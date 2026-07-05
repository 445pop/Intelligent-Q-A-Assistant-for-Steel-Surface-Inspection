import copy
import multiprocessing
import os
import queue
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from queue import Empty
import cv2
import numpy as np

from UtilObject.general_code import summary
from MyObject.Defect import SteelDefect, ImageDefect
from MyObject.Steel import Steel
from UtilObject.DatabaseUtil import MyDatabase
# 使用V8推理
from UtilObject.V8Detector import Detector_Batch, Detector
# 使用V5推理
# from UtilObject.V5Detector import Detector_Batch, Detector
from UtilObject.HttpServerUtil import MyHTTPServer
from MyObject.ProjectConfig import Appraise, Grade
# 加入小图聚合大图
from UtilObject.AggregationUtil import Aggregation
# 加入深度计算
from UtilObject.DepthUtil import get_depth


'''
此进程是拿推理结果，图像缺陷与冗余钢材缺陷。
情况：推理进程发送图像采集停止信号 与 缺陷数据信号。多个推理进程到数据库进程通信时，所以可能出现已经收到图像采集信号了，
但后续还有同批次缺陷数据信号，我就不要这些同批次缺陷数据了，故需要记录已发送批次
'''


class DatabaseProcess(multiprocessing.Process):
    def __init__(self, index, alive, res_queue, finished_queue, finished_mainid_list, sys_setting, daemon=True):
        multiprocessing.Process.__init__(self, daemon=daemon)
        self.database = MyDatabase(sys_setting)
        self.database.create_es()
        self.res_queue = res_queue
        self.finished_queue = finished_queue
        self.finished_mainid_list = finished_mainid_list  # 防止提交summary后还继续插入
        self.index = index
        self.alive = alive
        self.logger = sys_setting.logger

    # 接收结束信号并立马提交，不再接收同main_id后续的缺陷
    def run(self):
        self.logger.info('DatabaseProcess index {} is running'.format(self.index))
        actions = []
        direct_flag = False
        time_gap = 2
        last_time = time.time()
        while self.alive.value == True:
            try:
                action = self.res_queue.get()
                over_signal = action.pop('over_signal')
                main_id = action.pop('main_id')
                # 缺陷插入
                if over_signal == 0:
                    if main_id not in self.finished_mainid_list:
                        actions.append(action)
                    # else:
                    #     self.logger.info('DatabaseProcess filter :' + main_id)
                # 软件发送结束信号
                else:
                    direct_flag = True
                    self.finished_mainid_list.append(main_id)
                if len(actions) >= 150 or time.time() - last_time >= time_gap or direct_flag:
                    if len(actions) > 0:
                        res = self.database.bulk_actions(actions)
                        self.logger.info('已提交数据库' + str(len(actions)))
                    last_time = time.time()
                    actions.clear()
                    if direct_flag:
                        direct_flag = False
                        temp = (main_id, 'alg_send')
                        self.finished_queue.put(temp)
                        # 保留3个即可
                        if len(self.finished_mainid_list) > 3:
                            self.finished_mainid_list = self.finished_mainid_list[1:]

            except Exception as e:
                actions.clear()
                last_time = time.time()
                self.logger.error(traceback.format_exc())
                self.logger.error("ES Error occurred: %s".format(e))
        self.logger.info('DatabaseProcess over running')


'''
此进程使用生成者消费者模型，不会卡住。主要是多进程哈~
情况：考虑批次结束信号，增加全局钢材信息在多进程中通信，多线程通信当前进程的时间处理信息，并在时间处理中加锁作为 
'''

class InferProcess(multiprocessing.Process):
    def __init__(self, device_id, alive,alarmCancelled, json_queue, res_queue, steels_dic
                 , sys_setting, daemon=True):
        multiprocessing.Process.__init__(self, daemon=daemon)
        self.device_id = device_id
        self.cfg_runner = sys_setting.cfg_runner

        self.sys_setting = sys_setting
        self.database = MyDatabase(sys_setting)
        self.database.create_es()  # 建立数据库连接
        self.json_queue = json_queue
        self.res_queue = res_queue
        # 全局批次信息
        self.steels_dic = steels_dic

        self.alive = alive
        # 20240534 添加共享变量alarmCancelled免打扰模式/取消报警
        self.alarmCancelled = alarmCancelled
        self.logger = sys_setting.logger
        # 钢材时间
        self.steel_processTime = {}
        self.BATCH_NUM = 4
        self.lock = threading.Lock()

        # 安全线程队列
        self.shared_queue = queue.Queue(4000)
        self.shared_queue2 = queue.Queue(2000)
        # 事件
        self.cu_mainid_over_event = multiprocessing.Event()
        # 评级属性初始化
        self.get_new_appraise()
        # 初始化聚合类，用于小图聚合大图
        self.aggregation = Aggregation()

    # 每次批次更新前读取评级文件
    def get_new_appraise(self):
        # 0514添加,读取数据库评级套餐，如果可以读取，则更新，如果不能读取当前评级套餐id，则使用默认评级套餐
        # 如果无法读取默认评级套餐,则使用配置文件默认配置
        current_appraise_cfg_id = self.database.get_current_appraise_cfg_id()
        if current_appraise_cfg_id is not None:
            # 当前套餐id不为空
            current_appraise_cfg = self.database.get_current_appraise_cfg_from_id(current_appraise_cfg_id)
            if current_appraise_cfg is not None:
                # 当前套餐读取数据库评级文件成功
                self.logger.error('当前套餐读取成功' + str(current_appraise_cfg))
                appraise = Appraise(self.sys_setting, current_appraise_cfg)
                self.appraise_type_dict = appraise.appraise_type_dict
            else:
                self.logger.error('当前套餐id对应评级配置为空')
                default_appraise_cfg = self.database.get_default_appraise_cfg()
                if default_appraise_cfg is not None:
                    # 读取默认套餐成功
                    appraise = Appraise(self.sys_setting, current_appraise_cfg)
                    self.appraise_type_dict = appraise.appraise_type_dict
                else:
                    self.logger.error('没有套餐，数据库也没有默认套餐，使用配置文件默认配置')
                    self.appraise_type_dict = self.sys_setting.appraise.appraise_type_dict
        else:
            self.logger.error('没有套餐，数据库也没有默认套餐，使用配置文件默认配置')
            self.appraise_type_dict = self.sys_setting.appraise.appraise_type_dict

    def run(self):
        self.logger.info('InferProcess {} start running'.format(self.device_id))
        while self.alive.value:
            try:
                # 创建生产者线程 发现1个速度还可以（wait_batch） 后面自己测试
                producer_thread = threading.Thread(target=self.producer, args=(1,))
                # producer_thread2 = threading.Thread(target=self.producer, args=(2,))
                # 创建消费者线程
                consumer_thread1 = threading.Thread(target=self.consumer, args=(1,))
                # consumer_thread2 = threading.Thread(target=self.consumer, args=(2,))
                post_processing_thread = threading.Thread(target=self.post_processing)  # 这个处理很快
                check_steel_process_thread = threading.Thread(target=self.check_steel_process)
                # 启动线程
                producer_thread.start()
                # producer_thread2.start()
                consumer_thread1.start()
                # consumer_thread2.start()
                check_steel_process_thread.start()
                post_processing_thread.start()
                # 等待生产者线程完成
                # producer_thread.join()
                # producer_thread2.join()
                # consumer_thread1.join()
                # consumer_thread2.join()
                # post_processing_thread.join()
                check_steel_process_thread.join()
            except Exception as e:
                self.logger.error('threading prediction error')
                self.logger.error(traceback.format_exc())
        self.logger.info('InferProcess over running')

    # 生产者 若裁剪时固定距离则放在模型类里面比较好
    def get_small_images(self, image, json_dict, width_boundary=3072, crop_width=640, crop_height=640):  # 考虑加纵方向偏移
        left = json_dict['left_edge']
        right = json_dict['right_edge']

        # 存储非全黑图像块的列表
        non_black_block = []
        # 存储非全黑图像块左上角相对大图的位置（offset_x,offset_y）
        non_black_offset = []

        if 0 <= left <= width_boundary and 0 <= right <= width_boundary:
            current_left = left
            current_up = 0
            pic_num_x = (int(right) - int(left)) // crop_width
            yushu_x = (int(right) - int(left)) % crop_width
            pic_num_y = 6
            yushu_y = 256
            # 太短的不分析了
            if right - left < 100:
                return ([json_dict] * len(non_black_block), non_black_offset, non_black_block)
            # 处理640倍数的图像x
            for _ in range(pic_num_x):
                for _ in range(pic_num_y):
                    temp_img = image[current_up:current_up + crop_height, current_left:current_left + crop_width]
                    non_black_block.append(temp_img)
                    non_black_offset.append((current_left, current_up))
                    current_up += crop_height
                if yushu_y > 100 and pic_num_y > 0:
                    end_edge = current_up + yushu_y - 1
                    temp_img = image[end_edge - crop_height:end_edge, current_left:current_left + crop_width]
                    non_black_block.append(temp_img)
                    non_black_offset.append((current_left, end_edge - crop_height))
                current_left += crop_width
                current_up = 0
            # 处理不足640的x方向的内容:边部相机可能right_left不够640或者存在一个裁剪之后剩下一个余数

            if current_left + crop_width < width_boundary:  # 对于最右相机不足640
                current_left = left
            elif right - crop_width > 0:  # 对于最左相机不足640
                current_left = right - crop_width
            else:
                current_left = None
            if current_left is not None:
                for _ in range(pic_num_y):
                    temp_img = image[current_up:current_up + crop_height, current_left:current_left + crop_width]
                    non_black_block.append(temp_img)
                    non_black_offset.append((current_left, current_up))
                    current_up += crop_height
                if yushu_y > 100 and pic_num_y > 0:
                    end_edge = current_up + yushu_y - 1
                    temp_img = image[end_edge - crop_height:end_edge, current_left:current_left + crop_width]
                    non_black_block.append(temp_img)
                    non_black_offset.append((current_left, end_edge - crop_height))
        else:
            return ([json_dict] * len(non_black_block), non_black_offset, non_black_block)
        return ([json_dict] * len(non_black_block), non_black_offset, non_black_block)

    def update_steel_process_time(self, json_dict):
        with self.lock:
            self.logger.error('update_steel_process_time：{}'.format(json_dict))
            self.steel_processTime[json_dict['main_id']]['recv_end_time'] = datetime.now()
            time_format = "%Y-%m-%dT%H:%M:%S"
            self.steel_processTime[json_dict['main_id']]['hw_end_time'] = datetime.strptime(
                json_dict['end_time'], time_format)
            self.steel_processTime[json_dict['main_id']]['hw_start_time'] = datetime.strptime(
                json_dict['insert_time'], time_format)

    def init_steel_process_time(self):
        return {'gpu': int(self.device_id) % self.cfg_runner['Detect']['gpu_count'],
                'process': self.device_id,
                'infer_time': 0,
                'inferred_img_count': 0,
                'fps': 0,
                'picnum': 0,
                'io_time': 0,
                'wait_batch_time': 0,
                'start_time': datetime.now(),
                'end_time': datetime.now(),
                'alg_gap_time': 0,
                'hw_time': 0,
                'hw_start_time': datetime.now(),
                'hw_end_time': datetime.now(),
                'hw_gap_time': 0}

    # 目的是进行提前提交结束信号、更新批次时间信息与当前batch的内容
    def check_steel_process(self):
        # 提前提交看情况，最好的效果还是后处理的正常提交。这里并没有
        self.logger.info('InferProcess check_steel_processTime start running')
        while self.alive.value == True:
            try:
                time.sleep(0.5)
                with self.lock:
                    for key in self.steel_processTime.keys():
                        # 不想提前提交注释if 这一段
                        # 表示当前进程的收到批次结束信号、还未进行提交
                        if 'recv_end_time' in self.steel_processTime[key] and 'recv_end_time2' not in \
                                self.steel_processTime[key]:
                            if (datetime.now() - self.steel_processTime[key]['recv_end_time']).total_seconds() > 15:
                                finish_action = {

                                    'main_id': key,
                                    'over_signal': 1
                                }
                                self.res_queue.put(finish_action)

                                self.steel_processTime[key]['recv_end_time2'] = self.steel_processTime[key].pop(
                                    'recv_end_time')  # 已提交获得结论信号，清除终止信号
                                self.steel_processTime[key]['send_time'] = datetime.now()
                                self.logger.info(str(key) + '---' + str(self.device_id) + '进程接收到信号，并提前提交 ')

                        # 在全局变量中对此批次进行检查，目的是提交batch
                        # 表示当前进程的未收到批次结束信号，是未处理的
                        if key in self.steels_dic.keys():
                            if 'recv_end_time' in self.steels_dic[key] and 'recv_end_time' not in self.steel_processTime[
                                key] and 'recv_end_time2' not in self.steel_processTime[key]:
                                # 通知未接收到结束信号的可以正常提交了，但是正常提交会再次出现传送结束信号的情况，所以此处不是recv_end_time
                                # 而是recv_end_time2，仅代表本进程本批次已推理结束，记录时间罢了。
                                self.steel_processTime[key]['recv_end_time2'] = datetime.now()
                                self.cu_mainid_over_event.set()
                                # 那如果这个进程的批次也结束了呢或者没有这个批次，但可能未提交剩余内容 会影响什么嘛 好像不会吧 仅置位了时间，用来显示。
                                self.logger.info(str(key) +
                                                 '-----其他推理进程接收到信号,' + str(
                                    self.device_id) + ' 进程需设置终止信号 时间是' + str(
                                    (self.steel_processTime[key]['recv_end_time2'] - self.steels_dic[key][
                                        'recv_end_time']).total_seconds()))

            except Exception as e:

                self.logger.error(traceback.format_exc())
                self.logger.error('全局变量展示：' + str(self.steels_dic.keys()))
                self.logger.error('线程变量展示：' + str(self.steel_processTime.keys()))
        self.logger.info('InferProcess check_steel_processTime over running')
    # 新批次来时所操作的函数
    def init_new_batch(self):
        # 评级属性初始化
        self.get_new_appraise()

        if self.cu_mainid_over_event.is_set():
            self.cu_mainid_over_event.clear()


    # 图像预处理函数
    def hw_pre_func(self, img_origins, neth=640, netw=640):
        img_list = []
        info_list = []
        shape_list = []
        for img_origin in img_origins:
            # 遍历输入的图像列表
            imgh, imgw = img_origin.shape[:2]
            img_origin, ratio, pad = self.letterbox(img_origin, new_shape=(neth, netw))
            shape = (imgh, imgw), ((img_origin.shape[0] / imgh, img_origin.shape[1] / imgw), pad)
            img_info = np.stack([np.array([neth, netw, imgh, imgw], dtype=np.float16)], axis=0)
            img_origin = (np.stack([img_origin], axis=0))

            img = img_origin[..., ::-1].transpose(0, 3, 1, 2)  # BGR tp RGB HWC to CHW
            image_np = np.array(img, dtype=np.float32)  # img 转换为NumPy数组
            image_np_expanded = image_np / 255.0  # 像素值进行归一化，将值范围从0到255缩放到0到1之间
            img = np.ascontiguousarray(image_np_expanded).astype(
                np.float16)  # image_np_expanded 转换为一个以连续内存存储的NumPy数组
            # 创建列表存储图像、图像信息、图像尺寸
            img_list.append(img)
            info_list.append(img_info)
            shape_list.append(shape)

        return img_list, info_list, shape_list

    def letterbox(self, img, new_shape=(640, 640), color=(114, 114, 114), auto=False, scaleFill=False, scaleup=True):
        # Resize image to a 32-pixel-multiple rectangle https://github.com/ultralytics/yolov3/issues/232
        shape = img.shape[:2]  # current shape [height, width]

        if isinstance(new_shape, int):
            new_shape = (new_shape, new_shape)

        # Scale ratio (new / old)
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        if not scaleup:  # only scale down, do not scale up (for better test mAP)
            r = min(r, 1.0)

        # Compute padding
        ratio = r, r  # width, height ratios
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
        dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # wh padding
        if auto:  # minimum rectangle
            dw, dh = np.mod(dw, 64), np.mod(dh, 64)  # wh padding
        elif scaleFill:  # stretch
            dw, dh = 0.0, 0.0
            new_unpad = (new_shape[1], new_shape[0])
            ratio = new_shape[1] / shape[1], new_shape[0] / shape[0]  # width, height ratios

        dw /= 2  # divide padding into 2 sides
        dh /= 2

        if shape[::-1] != new_unpad:  # resize
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
            # img_ = Image.fromarray(img)
            # img_ = img_.resize(new_unpad, resample=Image.BILINEAR)
            # img = np.array(img_)
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)  # add border
        return img, ratio, (dw, dh)

    '''
     结束信号代表所有图像都发送完毕了
     在这里使用线程锁主要是为了触发信号准确，在部分情况下可以取消有关线程锁的内容
     '''

    # 一张大图上的小图缺陷聚合为大图缺陷
    def one_pic_defect_aggregation(self, one_pic_defect_list):
        # 以前的聚合代码用的数据格式是从es数据库里读出来的，最初源头是database.get_defects_by_main_id，得到的结构是一种json格式
        # 现在的小图聚合大图，用的是one_pic_defect_list，且是在大图中的位置，如下 x1, y1, x2, y2, conf, class_id
        # 进行聚合前，现根据类型分组
        # 聚合 要x方向y方向都聚合
        merge_defect_list = []

        one_pic_defect_type_dict = {}

        for batch_defect in one_pic_defect_list:
            try:
                #根据缺陷类型分类，放入batch_defect_type_dict
                class_id = int(batch_defect[5])
                if class_id not in one_pic_defect_type_dict.keys():
                    one_pic_defect_type_dict[class_id] = []
                one_pic_defect_type_dict[class_id].append(batch_defect)
            except Exception as e:
                self.logger.error('batch_defect_type_dict error')
                self.logger.error('batch_defect_type_dict' + str(batch_defect))
                self.logger.error(traceback.format_exc())

        for class_id, type_defects in one_pic_defect_type_dict.items():
            # 遍历这一张大图中 所有的缺陷（按照缺陷类型进行遍历）
            # y_grouping_space = self.cfg_runner['Conclusion']['merge_setting']['y_grouping_space']
            # x_grouping_space = self.cfg_runner['Conclusion']['merge_setting']['x_grouping_space']
            x_error = 4096
            y_error = 4096
            s_threshold = 0.5
            # 聚合每个类
            type_merge_defect_list = self.aggregation.one_pic_target_types_defect_merge(type_defects,
                                                                                        class_id,
                                                                           s_threshold=s_threshold,
                                                                           x_error=x_error,
                                                                           y_error=y_error)
            # 把每个类的都加进来
            merge_defect_list.extend(type_merge_defect_list)
        return merge_defect_list

    def producer(self, index_p):
        # 小图数据
        batch_json_small = []
        batch_offset_small = []
        batch_img_small = []
        batch_info_small = []
        batch_shape_small = []  

        # 大图数据
        batch_json_big = []
        batch_offset_big = []
        batch_img_big = []
        batch_info_big = []
        batch_shape_big = [] 

        t_new = time.time()
        self.logger.info('InferProcess {} producer {} start running'.format(self.device_id, index_p))
        while self.alive.value:
            try:
                json_dict = self.json_queue.get()

                # 更新时间情况日志
                with self.lock:
                    if json_dict['main_id'] not in self.steel_processTime.keys():
                        self.steel_processTime[json_dict['main_id']] = self.init_steel_process_time()
                        self.init_new_batch()
                        t_new = time.time()

                        if json_dict['main_id'] not in self.steels_dic.keys():
                            self.steels_dic[json_dict['main_id']] = {'start_time': datetime.now()}
                            self.logger.error('检查全局变量变化' + str(self.steels_dic.keys()))
                            self.logger.error('检查线程全局变量变化' + str(self.steel_processTime.keys()))
                            # 保留最新5个的信息
                            if len(self.steels_dic) > 10:
                                for key in list(self.steels_dic.keys())[:5]:
                                    try:
                                        del self.steels_dic[key]

                                    except KeyError:
                                        self.logger.error('出现多进程删除同一全局变量' + str(key))
                                        # 保持steel_processTime与最新钢材缺陷保持一致
                        self.steel_processTime = {key: self.steel_processTime[key] for key in
                                                  list(self.steels_dic.keys()) if key in self.steel_processTime}

                # 终止信号含信号、批次、插入时间与终止时间
                if json_dict['signal'] == 1:
                    self.logger.info(
                        'json_str is finish ' + str(json_dict['main_id']) + '  ' + str(datetime.now()))
                    self.update_steel_process_time(json_dict)
                    # 更新全局信息 保证其余多进程也能收到结束信号 进行当前批次的终止。
                    self.steels_dic[json_dict['main_id']]['recv_end_time'] = \
                        self.steel_processTime[json_dict['main_id']]['recv_end_time']

                    # 针对多生产者
                    self.cu_mainid_over_event.set()

                if json_dict['signal'] == 0:
                    # 尝试少推理图像
                    if json_dict['flow_id'] % 10 > 10:

                        continue
                    elif json_dict['flow_id'] % 1000 == 0:
                        self.logger.info(
                            'InferProcess {} producer {} mainid{} json_len{} pic_len {}'.format(self.device_id, index_p,
                                                                                                json_dict['main_id'],
                                                                                                self.json_queue.qsize(),
                                                                                                self.shared_queue.qsize()))
                    # 打印采集端信息
                    # self.logger.error(str(json_dict))
                    # 读取文件路径
                    # 修改马钢地址
                    st = json_dict['image_url'].find("img")
                    # 解析相机号，根据相机号来决定文件路径头部
                    if json_dict["root_id"] == "1234":
                        temp_img_path = os.path.join(self.cfg_runner['Image']['data_root']['1234'],
                                                     json_dict['image_url'][st+4:].replace('\\', '/'))
                    elif json_dict["root_id"] == "567":
                        temp_img_path = os.path.join(self.cfg_runner['Image']['data_root']['567'],
                                                     json_dict['image_url'][st+4:].replace('\\', '/'))
                    else:
                        continue

                    log_img_path = json_dict['image_url']
                    self.logger.error("log_img_path:{}".format(log_img_path))

                    if os.path.exists(temp_img_path):
                        t1 = time.time()
                        # 读取大图
                        temp_img = cv2.imread(temp_img_path)
                        #batch_json_big += json_dict

                        # 构造大图数据
                        batch_json_big.append(json_dict)
                        pic = []
                        pic.append(temp_img)
                        img_list_big, info_list_big, shape_list_big = self.hw_pre_func(pic)
                        batch_img_big += img_list_big
                        batch_info_big += info_list_big
                        batch_shape_big += shape_list_big
                        batch_offset_big.append((0,0))

                        # 切分为小图
                        json_dicts_small, offset_small, pic_blocks_small = self.get_small_images(temp_img, json_dict)
                        batch_json_small += json_dicts_small
                        batch_offset_small += offset_small
                        # 构造小图数据
                        img_list_small, info_list_small, shape_list_small = self.hw_pre_func(pic_blocks_small)
                        batch_img_small += img_list_small
                        batch_info_small += info_list_small
                        batch_shape_small += shape_list_small

                        with self.lock:
                            self.steel_processTime[json_dict['main_id']]['io_time'] += (time.time() - t1)
                    else:
                        self.logger.error('img_path is not found: ' + temp_img_path)

                if len(batch_json_small) >= self.BATCH_NUM or self.cu_mainid_over_event.is_set():
                    if len(batch_json_small) != 0:
                        # 与consumer里的shared_queue共享
                        self.shared_queue.put(
                            (
                            copy.copy(batch_json_small),
                            copy.copy(batch_offset_small), 
                            copy.copy(batch_img_small), 
                            copy.copy(batch_info_small),
                            copy.copy(batch_shape_small),
                            copy.copy(batch_json_big),
                            copy.copy(batch_offset_big), 
                            copy.copy(batch_img_big), 
                            copy.copy(batch_info_big),
                            copy.copy(batch_shape_big)
                            ))
                    with self.lock:
                        self.steel_processTime[json_dict['main_id']]['wait_batch_time'] += (time.time() - t_new)
                    t_new = time.time()
                    # 每个批次结束后重置为空
                    batch_json_small = []
                    batch_offset_small = []
                    batch_img_small = []
                    batch_info_small = []
                    batch_shape_small = []  

                    batch_json_big = []
                    batch_offset_big = []
                    batch_img_big = []
                    batch_info_big = []
                    batch_shape_big = []

            except Exception as e:
                self.logger.error('threading producer error')
                self.logger.error(traceback.format_exc())
        self.logger.info('InferProcess {} producer {} over running'.format(self.device_id, index_p))

    def consumer(self, index_c):
        gpu_count = self.cfg_runner['Detect']['gpu_count']
        if self.cfg_runner['is_nvidia']:
            self.model = Detector_Batch(self.sys_setting,gpu_id=int(self.device_id) % gpu_count)  # self.device_id  'cpu'
        else:
            # 目前一般是走这里，用华为卡推理
            self.model = Detector(self.sys_setting,device_id=int(self.device_id))  # self.device_id  'cpu'
        self.logger.info('batch model on device {} in thread {} start running'.format(self.device_id, index_c))
        # 如果结束信号来了，但是没有推理完
        while self.alive.value == True:
            try:
                # 获取当前批次的大图小图数据
                (
                    batch_json_small,
                    batch_offset_small,
                    batch_img_small,
                    batch_info_small,
                    batch_shape_small,
                    batch_json_big,
                    batch_offset_big,
                    batch_img_big,
                    batch_info_big,
                    batch_shape_big
                ) = self.shared_queue.get()
                # 从producer里获取的信息，包括裁剪后的小图

                t2 = time.time()
                cu_main_id = batch_json_small[0]['main_id']
                cu_flow_id = batch_json_small[0]['flow_id']

                if 'recv_end_time2' in self.steel_processTime[cu_main_id]:  # 假如已提交summary就不必要检测了
                    self.logger.info(
                        '提前提交 {} flowid {} device {} in thread {} stop infer'.format(cu_main_id, cu_flow_id,
                                                                                         self.device_id, index_c))
                    continue
                # [[{6个},{6个}], [], [], []]
                # batch_results = self.model.detect(batch_img)
                # 创建两个模型，分别用于大图推理和小图推理
                batch_results_big = self.model.detect_after_preProcess(batch_img_big, batch_info_big, batch_shape_big,1)
                batch_results_small = self.model.detect_after_preProcess(batch_img_small, batch_info_small, batch_shape_small,2)

                # batch_results_small = self.model.detect_after_preProcess(batch_img_small, batch_info_small, batch_shape_small)

                # 这里的结果输入格式：x1, y1, x2, y2, conf, class_id
                # todo 如果要加小图缺陷聚合，加在这里
                # batch_image_defects = self.model.result2defect(batch_results)
                t3 = time.time()

                self.shared_queue2.put(
                    (
                        batch_results_small,
                        batch_json_small, 
                        batch_offset_small,
                        batch_results_big,
                        batch_json_big, 
                        batch_offset_big
                        )
                    )
                
                # with self.lock:
                #     self.steel_processTime[cu_main_id]['infer_time'] += (t3 - t2)
                #     self.steel_processTime[cu_main_id]['picnum'] += len(batch_img_big)
                #     self.steel_processTime[cu_main_id]['fps'] += self.steel_processTime[cu_main_id]['picnum'] // \
                #                                                  self.steel_processTime[cu_main_id]['infer_time']


            except Exception as e:
                self.logger.error('threading consumer error')
                self.logger.error(traceback.format_exc())
        self.logger.info('batch model on device {} in thread {} over running'.format(self.device_id, index_c))
    # 根据评级文件中滤除设置进行删除缺陷
    def need_filter_defect(self, image_defect):
        appraise_type = self.appraise_type_dict[image_defect.type]
        # 图像缺陷过滤条件
        filter_conditions = copy.copy(self.cfg_runner['Conclusion']['filter_condition'])

        for filter_condition in filter_conditions:

            if appraise_type.filter_unit[filter_condition][0]:  # 包含该过滤条件
                filter_lower = appraise_type.filter_unit[filter_condition][1]
                filter_upper = appraise_type.filter_unit[filter_condition][2]
                if filter_condition == 7:#缺陷高度
                    if not (filter_lower < image_defect.real_h < filter_upper):
                        return True
                elif filter_condition == 8:#缺陷宽度
                    if not (filter_lower < image_defect.real_w < filter_upper):
                        return True
                elif filter_condition == 4:#距离头部
                    if (filter_lower < image_defect.real_y < filter_upper):
                        return True
                elif filter_condition == 5:#距离左边
                    if (filter_lower < image_defect.real_x < filter_upper):
                        return True
                elif filter_condition == 17:#保留缺陷尺寸范围
                    if not (filter_lower < round(image_defect.real_w * image_defect.real_h, 2)< filter_upper):
                        return True
                elif filter_condition == 18:#过滤条形缺陷长宽比
                    if (filter_lower < round(image_defect.real_h / image_defect.real_w, 2)< filter_upper):
                        # self.logger.error('过滤长宽比{}'.format(round(image_defect.real_h / image_defect.real_w, 2)))
                        return True
                elif filter_condition == 9:#置信度
                    # 对30米后的擦伤进行置信度过滤提升
                    # if image_defect.type in [16] and 200000 > image_defect.real_y > 30000:
                    #     filter_lower += 0.1
                    #     filter_upper += 0.1
                    if not (filter_lower < image_defect.confidence < filter_upper):
                        return True

        if image_defect.type not in self.cfg_runner['Conclusion']['typeid_need_summary']:
            return True
            # 过滤越界
        if image_defect.x < 0 or image_defect.y < 0 or (image_defect.x + image_defect.w) > self.cfg_runner['Image'][
            'image_w'] or (image_defect.y + image_defect.h) > \
                self.cfg_runner['Image']['image_h']:
            return True

        return False
    
    def post_processing(self):
        last_mainid = None
        hw_llast_endtime = None
        alg_llast_endtime = None
        cu_surface_left = None  # 对于左边界还是等遇到时再进行更新吧，毕竟怎么弄都是不准的
        wait_left_defect_list = []  # 存储未及时拿到最新left的信息
        self.logger.info('InferProcess post_processing start running')
        while self.alive.value == True:
            try:
                temp_pic_dict = {}
                # 这是从inferprocess的consumer进程里拿到的
                # 其中batch_results是模型推出来的结果
                
                (
                    batch_results_small,
                    batch_json_small, 
                    batch_offset_small,
                    batch_results_big,
                    batch_json_big, 
                    batch_offset_big
                )= self.shared_queue2.get()

                t1 = time.time()
                # zip() 函数用于将可迭代的对象作为参数，将对象中对应的元素打包成一个个元组，然后返回由这些元组组成的列表。
                # 这里把batch_offset, batch_json_dict,batch_results这三个东西按照顺序打包成了一个元组，便于后续迭代
                # 对于两个模型输出的结果分别遍历
                for cu_offset, json_dict, pred_boxs in zip(batch_offset_small,
                                                           batch_json_small,
                                                           batch_results_small):
                    if json_dict['flow_id'] not in temp_pic_dict.keys():
                        temp_pic_dict[json_dict['flow_id']] = {}  # camera_id:[json_dict,[]]
                    if json_dict['camera_id'] not in temp_pic_dict[json_dict['flow_id']].keys():
                        temp_pic_dict[json_dict['flow_id']][json_dict['camera_id']] = [json_dict, []]
                    # 遍历每一个预测box
                    for row_info in pred_boxs:
                        x1, y1, x2, y2, conf, class_id = row_info[0], row_info[1], row_info[2], row_info[3], row_info[
                            4], row_info[5]
                        # 相对大图位置
                        x1 += cu_offset[0]
                        x2 += cu_offset[0]
                        y1 += cu_offset[1]
                        y2 += cu_offset[1]

                        # if int(class_id) in [4, 5, 6]:
                        #     # 需要统一的类
                        #     class_id = 4
                        # elif int(class_id) in [7, 8, 9, 24, 15, 16]:
                        #     class_id = 7
                        # elif int(class_id) in [21]:
                        #     class_id = 23

                        if int(class_id) in [2,4,10]:
                            # 小图模型只检出水和熔渣
                            temp_pic_dict[json_dict['flow_id']][json_dict['camera_id']][1].append([x1, y1, x2, y2, conf, class_id])
                            # self.logger.info('小图模型推理结果{}'.format([x1, y1, x2, y2, conf, class_id]))
                        else:
                            continue
                        
                for cu_offset, json_dict, pred_boxs in zip(batch_offset_big,
                                                           batch_json_big,
                                                           batch_results_big):
                    if json_dict['flow_id'] not in temp_pic_dict.keys():
                        temp_pic_dict[json_dict['flow_id']] = {}  # camera_id:[json_dict,[]]
                    if json_dict['camera_id'] not in temp_pic_dict[json_dict['flow_id']].keys():
                        temp_pic_dict[json_dict['flow_id']][json_dict['camera_id']] = [json_dict, []]
                    # 遍历每一个预测box



                    # 假设 pred_boxs 是当前图像的预测框列表
                    has_class_id_3 = False  # 用于标记是否存在 class_id=3

                    # 首先遍历一次预测框，检查是否存在 class_id=3
                    for row_info in pred_boxs:
                        class_id = row_info[5]  # 假设 class_id 在 row_info 的第 5 个位置
                        if class_id == 3:
                            has_class_id_3 = True
                            break  # 找到后退出循环

                    # 重新遍历预测框，根据是否存在 class_id=3 来设置 class_id=13
                    for row_info in pred_boxs:
                        x1, y1, x2, y2, conf, class_id = row_info[0], row_info[1], row_info[2], row_info[3], row_info[
                            4], row_info[5]

                        # 根据 has_class_id_3 的值设置 class_id
                        if class_id == 14:
                            if has_class_id_3:
                                class_id = 3  # 如果存在 class_id=3，则将 class_id=13 设置为 3
                            else:
                                class_id = 12  # 如果不存在 class_id=3，则将 class_id=13 设置为 12

                        # 这里可以继续处理其他逻辑，例如存储预测框等
                        # ...




                    for row_info in pred_boxs:
                        x1, y1, x2, y2, conf, class_id = row_info[0], row_info[1], row_info[2], row_info[3], row_info[
                            4], row_info[5]
                        # 相对大图位置
                        x1 += cu_offset[0]
                        x2 += cu_offset[0]
                        y1 += cu_offset[1]
                        y2 += cu_offset[1]

                        # if int(class_id) in [4, 5, 6]:
                        #     # 需要统一的类
                        #     class_id = 4
                        # elif int(class_id) in [7, 8, 9, 24, 15, 16]:
                        #     class_id = 7
                        # elif int(class_id) in [21]:
                        #     class_id = 23
                        if int(class_id) in [12,9,2,4]:
                            # 不需要检出的水、误检、气孔、熔渣
                            continue
                        temp_pic_dict[json_dict['flow_id']][json_dict['camera_id']][1].append([x1, y1, x2, y2, conf, class_id])


                self.logger.info('temp_pic_dict：{}'.format(temp_pic_dict))
                # 大图的nms
                for cu_flow_id in temp_pic_dict.keys():
                    for cu_camera_id in temp_pic_dict[cu_flow_id]:
                        json_dict = temp_pic_dict[cu_flow_id][cu_camera_id][0]
                        if last_mainid is None:
                            last_mainid = json_dict['main_id']
                        cu_surface_left = json_dict['left']

                        one_pic_defect_list = temp_pic_dict[cu_flow_id][cu_camera_id][1]
                        # self.logger.info('nms前结果：{}'.format(one_pic_defect_list))
                        # one_pic_defect_list = self.model.nms(np.array(one_pic_defect_list), 0.2)
                        # self.logger.info('nms后结果：{}'.format(one_pic_defect_list))
                        # 聚合步骤：
                        # 分类
                        # 聚合
                        # 新类型
                        # 现在的输入就是缺陷在大图上的位置信息和置信度
                        # 有些项目不需要小图聚合大图，因此在配置文件种加入这一属性
                        # need_one_pic_merge =  self.cfg_runner['Detect']['need_one_pic_merge']
                        # self.logger.info('小图聚合前缺陷数量{}'.format(len(one_pic_defect_list)))
                        # if need_one_pic_merge:
                        #     one_pic_defect_list = self.one_pic_defect_aggregation(one_pic_defect_list)
                        # self.logger.info('小图聚合后缺陷数量{}'.format(len(one_pic_defect_list)))

                        for item in one_pic_defect_list:
                            x1, y1, x2, y2, conf, class_id = int(item[0]), int(item[1]), int(item[2]), int(
                                item[3]), float(item[4]), int(item[5])
                            # 相对表面
                            pa_x1 = x1 + self.cfg_runner['CameraOffset'][cu_camera_id]['other_offset'][0]
                            pa_y1 = y1 + self.cfg_runner['CameraOffset'][cu_camera_id]['other_offset'][1]
                            pa_x2 = x2 + self.cfg_runner['CameraOffset'][cu_camera_id]['other_offset'][0]
                            pa_y2 = y2 + self.cfg_runner['CameraOffset'][cu_camera_id]['other_offset'][1]
                            # 创建钢材缺陷与图像缺陷
                            image_defect = ImageDefect.pred_result2defect(self.cfg_runner,[x1, y1, x2, y2, conf, class_id])
                            self.logger.info('相机号：{}，流水号：{}，推理结果：{}'.format(cu_camera_id,cu_flow_id,[x1, y1, x2, y2, conf, class_id]) )
                            image_defect.set_parm_by_json_dict(json_dict)

                            if cu_surface_left is not None:
                                cu_left = cu_surface_left
                                self.process_defect(image_defect, json_dict, pa_x1, pa_y1, pa_x2, pa_y2, cu_left)
                                if len(wait_left_defect_list) > 0:
                                    for item in wait_left_defect_list:
                                        self.process_defect(item[0], item[1], item[2], item[3], item[4], item[5],cu_left)
                                    wait_left_defect_list.clear()
                                    self.logger.error('该批次已处理left:' + str([self.device_id, json_dict['main_id']]))
                            else:
                                # 存起来内容【json_dict,pa,imagedefect】continue
                                wait_left_defect_list.append([image_defect, json_dict, pa_x1, pa_y1, pa_x2, pa_y2])
                                self.logger.error('该批次在等待left:' + str([self.device_id, json_dict['main_id']]))

                        with self.lock:
                            # 正常批次推理结束提交
                            if json_dict['main_id'] in self.steel_processTime:
                                if 'recv_end_time' in self.steel_processTime[json_dict['main_id']].keys():
                                    # 算法已处理了一段时间了 有效推理
                                    if (datetime.now() - self.steel_processTime[json_dict['main_id']][
                                        'start_time']).total_seconds() > 5:
                                        finish_action = {
                                            'main_id': json_dict['main_id'],
                                            'over_signal': 1
                                        }

                                        self.res_queue.put(finish_action)
                                        self.steel_processTime[json_dict['main_id']]['recv_end_time2'] = \
                                            self.steel_processTime[json_dict['main_id']].pop('recv_end_time')
                                        self.steel_processTime[json_dict['main_id']]['send_time'] = datetime.now()
                                        self.logger.info(str(self.device_id) + '进程正常提交 ' + str(
                                            self.steel_processTime[json_dict['main_id']]))

                                self.steel_processTime[json_dict['main_id']]['end_time'] = datetime.now()
                                # 获得新批次时间
                                if last_mainid != json_dict['main_id']:
                                    cu_mainid = json_dict['main_id']
                                    if last_mainid in self.steel_processTime.keys():
                                        # 计算硬件处理时间
                                        self.steel_processTime[last_mainid]['hw_time'] = int(
                                            (self.steel_processTime[last_mainid][
                                                'hw_end_time'] -
                                            self.steel_processTime[last_mainid][
                                                'hw_start_time']).total_seconds())
                                        self.steel_processTime[last_mainid]['alg_time'] = int(
                                            (self.steel_processTime[last_mainid]['end_time'] -
                                            self.steel_processTime[last_mainid][
                                                'start_time']).total_seconds())
                                        # 已知上上批次的结束时间 计算间隔等
                                        if hw_llast_endtime is not None:
                                            self.steel_processTime[last_mainid]['hw_gap_time'] = int(
                                                (self.steel_processTime[last_mainid][
                                                    'hw_start_time'] - hw_llast_endtime).total_seconds())
                                            self.steel_processTime[last_mainid]['alg_gap_time'] = int(
                                                (self.steel_processTime[last_mainid][
                                                    'start_time'] - alg_llast_endtime).total_seconds())
                                            self.steel_processTime[last_mainid]['alg_s_hw_e'] = int(
                                                (self.steel_processTime[last_mainid][
                                                    'start_time'] -
                                                self.steel_processTime[last_mainid][
                                                    'hw_end_time']).total_seconds())
                                            self.steel_processTime[last_mainid]['alg_s_hw_s'] = int(
                                                (self.steel_processTime[last_mainid][
                                                    'start_time'] -
                                                self.steel_processTime[last_mainid][
                                                    'hw_start_time']).total_seconds())
                                            self.steel_processTime[last_mainid]['last_alg_e_cu_hw_s'] = int(
                                                (alg_llast_endtime -
                                                self.steel_processTime[
                                                    last_mainid][
                                                    'hw_start_time']).total_seconds())
                                            self.steel_processTime[last_mainid]['alg_e_hw_e'] = int(
                                                (self.steel_processTime[last_mainid][
                                                    'end_time'] -
                                                self.steel_processTime[last_mainid][
                                                    'hw_end_time']).total_seconds())
                                        hw_llast_endtime = self.steel_processTime[last_mainid]['hw_end_time']
                                        alg_llast_endtime = self.steel_processTime[last_mainid]['end_time']

                                    self.logger.info('last_mainid:{},cu_main_id:{} '.format(last_mainid, cu_mainid))
                                    # 更新因批次变化而需要更新的参数
                                    last_mainid = cu_mainid
                                    cu_surface_left = None



            except Exception as e:
                self.logger.error('threading_predict_batch error')
                self.logger.error(traceback.format_exc())
        self.logger.info('InferProcess post_processing over running')

    # 处理图像缺陷，钢材缺陷转换，插入数据库
    def process_defect(self, image_defect, json_dict, pa_x1, pa_y1, pa_x2, pa_y2, cu_left):
        # 不同项目相对真实长度计算可能有差异
        image_defect.real_x = Steel.transform_length(self.cfg_runner,
                                                     pa_x1 - cu_left, need_y=False,
                                                     gg=str(json_dict['camera_id']))
        image_defect.real_y = Steel.transform_length(self.cfg_runner, pa_y1, need_y=True,
                                                     gg=str(json_dict['camera_id'])) + round(json_dict['steel_length'] * 1000, 3)
        image_defect.real_w = Steel.transform_length(self.cfg_runner, pa_x2 - pa_x1, need_y=False,
                                                     gg=str(json_dict['camera_id']))
        image_defect.real_h = Steel.transform_length(self.cfg_runner, pa_y2 - pa_y1, need_y=True,
                                                     gg=str(json_dict['camera_id']))
        # 过滤条件添加
        if self.need_filter_defect(image_defect):
            return
        
        image_path = json_dict['image_url']
        st = json_dict['image_url'].find("img")
        # 解析相机号，根据相机号来决定文件路径头部
        if json_dict["root_id"] == "1234":
            temp_img_path = os.path.join(self.cfg_runner['Image']['data_root']['1234'],
                                         json_dict['image_url'][st+4:].replace('\\', '/'))
        elif json_dict["root_id"] == "567":
            temp_img_path = os.path.join(self.cfg_runner['Image']['data_root']['567'],
                                         json_dict['image_url'][st+4:].replace('\\', '/'))
        else:
            pass
        # 获取基准深度
        chinese_typeid_dict = self.cfg_runner['Detect']['typeid_chinese']
        depth_base = float(json_dict["other1"])
        # 获取缺陷坐标,xywhs是大图上的坐标信息
        x = int(image_defect.x)
        y = int(image_defect.y)
        w = int(image_defect.w)
        h = int(image_defect.h)
        cls = image_defect.type
        defect_pos = [x,y,w,h]
        # 通过bin路径读取深度信息
        bin_path = temp_img_path.replace('gray_img', 'origin_img').replace('.jpg', '.bin')
        #/home/hongtai/yolo/1002d/img/20240703041707/gray_img/6_2410564244_3_down_3.jpg
        # self.logger.error("binpath{}".format(bin_path))


        #20240929测试取消读bin文件 

        # status_code , error_value , depth= get_depth(defect_pos,depth_base,cls,bin_path)
        # depth = float(depth)
        # # 保留两位小数并取绝对值round(abs(original_value), 2)
        # if status_code == 100:
        #     self.logger.info("获取{}深度值成功,返回值{}".format(chinese_typeid_dict[cls],depth))
        #     image_defect.real_depth = round(abs(depth), 2)
        # elif status_code == 201:
        #     self.logger.info("获取{}深度值失败,数值异常,返回默认值{},错误值为{}".format(chinese_typeid_dict[cls],depth,error_value))
        #     self.logger.error("获取{}深度值失败,数值异常,返回默认值{},错误值为{}".format(chinese_typeid_dict[cls],depth,error_value))
        #     image_defect.real_depth = round(abs(depth), 2)
        # elif status_code == 202:
        #     self.logger.info("获取{}深度值失败,bin文件路径错误,返回值{}".format(chinese_typeid_dict[cls],depth))
        #     self.logger.error("获取{}深度值失败,bin文件路径错误,返回值{}".format(chinese_typeid_dict[cls],depth))
        #     image_defect.real_depth = round(abs(depth), 2)
        # elif status_code == 203:
        #     self.logger.info("获取{}深度值失败,bin文件读取错误,返回值{}".format(chinese_typeid_dict[cls],depth))
        #     self.logger.error("获取{}深度值失败,bin文件读取错误,返回值{}".format(chinese_typeid_dict[cls],depth))
        #     image_defect.real_depth = round(abs(depth), 2)
        # elif status_code == 204:
        #     self.logger.info("获取{}深度值失败,缺陷区域不正确,返回值{}".format(chinese_typeid_dict[cls],error_value))
        #     self.logger.error("获取{}深度值失败,缺陷区域不正确,返回值{}".format(chinese_typeid_dict[cls],error_value))
        #     image_defect.real_depth = round(abs(depth), 2)
        # elif status_code == 205:
        #     self.logger.info("获取{}深度值失败,类型错误,type值{}".format(chinese_typeid_dict[cls],error_value))
        #     self.logger.error("获取{}深度值失败,类型错误,type值{}".format(chinese_typeid_dict[cls],error_value))
        #     image_defect.real_depth = round(abs(depth), 2)
        # elif status_code == 206:
        #     self.logger.info("获取{}深度值失败,类型错误,type值{}".format(chinese_typeid_dict[cls],error_value))
        #     self.logger.error("获取{}深度值失败,类型错误,type值{}".format(chinese_typeid_dict[cls],error_value))
        #     image_defect.real_depth = round(abs(depth), 2)
        # else:
        #     self.logger.info("深度类型{},返回值{}".format(chinese_typeid_dict[cls],depth))

        # 处理图像缺陷报警信息（马钢删除这部分）
        # self.need_post_client(image_defect)

        # 做钢材冗余缺陷
        steel_defect = SteelDefect.create_new_defect(json_dict)
        steel_defect.set_rongyu_parm_by_image_defect(image_defect)
        steel_defect.grade = '冗余存储'
        # 考虑是否向数据库发送
        # 向es进程发送信息
        index_action1 = {
            '_op_type': 'index',
            '_index': self.cfg_runner['Database']['ES']['es_table'][1],
            '_source': image_defect.get_dict(),
            'main_id': json_dict['main_id'],
            'over_signal': 0
        }
        # self.logger.error(vars(image_defect))
        self.res_queue.put(index_action1)

        index_action2 = {
            '_op_type': 'index',
            '_index': self.cfg_runner['Database']['ES']['es_table'][2],
            '_source': steel_defect.get_dict(),
            'main_id': json_dict['main_id'],
            'over_signal': 0
        }

        self.res_queue.put(index_action2)



# 定期检查流程
class PeriodicCheckProcess(multiprocessing.Process):
    def __init__(self, index, alive,alarmCancelled, finished_queue
                 , sys_setting, daemon=True):
        multiprocessing.Process.__init__(self, daemon=daemon)

        self.finished_queue = finished_queue
        self.database = MyDatabase(sys_setting)
        self.database.create_es()
        self.database_cpj = MyDatabase(sys_setting)
        self.database_cpj.create_es()
        self.finished_dict = {}
        self.sys_setting = sys_setting
        self.index = index
        self.cfg_runner = sys_setting.cfg_runner
        self.alive = alive
        self.alarmCancelled = alarmCancelled
        self.logger = sys_setting.logger
        # 安全线程队列
        self.shared_queue = queue.Queue()

    def run(self):

        while self.alive.value == True:
            try:
                self.logger.info('PeriodicCheckProcess {} start running'.format(self.index))
                # 创建生产者线程
                # producer_thread = threading.Thread(target=self.producer)
                # 创建消费者线程
                consumer_thread1 = threading.Thread(target=self.consumer)

                # 启动线程
                # producer_thread.start()
                consumer_thread1.start()

                # 等待生产者线程完成
                # producer_thread.join()
                consumer_thread1.join()


            except Exception as e:
                self.logger.error(traceback.format_exc())
                self.logger.error(e)
    def producer(self):
        while self.alive.value == True:
            try:
                time.sleep(30)

            except Exception as e:
                self.logger.error('PeriodicCheckProcess producer error')
                self.logger.error(traceback.format_exc())

    def consumer(self):
        pool = ThreadPoolExecutor(max_workers=4)  # 适合cpu密集型,使用进程池，但线程池可以利用多核 CPU 并行执行任务
        last_finished_mainid = None  # 保证冗余缺陷（实时缺陷）还是显示状态
        while self.alive.value == True:
            try:
                temp = self.finished_queue.get()
                (finished_mainid, flag) = temp
                if flag == 'alg_send':
                    if last_finished_mainid is not None:
                        self.database.delete_redu_delete(last_finished_mainid)
                        self.logger.info(
                            '已删除上一批 {} 冗余缺陷,此批次 {} 冗余缺陷等待中'.format(last_finished_mainid,
                                                                                       finished_mainid))
                        last_finished_mainid = finished_mainid
                    else:
                        last_finished_mainid = finished_mainid
                    summary.summary(finished_mainid, self.sys_setting,self.alarmCancelled)

                    # pool.submit(summary.summary, finished_mainid, self.sys_setting)
                elif flag == 'client_send':
                    # 删除所有钢材缺陷记录 评级记录
                    self.database_cpj.delete_steel_defect_delete(finished_mainid)
                    self.database_cpj.delete_steel_defect_amount(finished_mainid)
                    # 重新进行结论提交
                    # pool.submit(summary.summary, finished_mainid, self.sys_setting)
                    summary.summary(finished_mainid, self.sys_setting,self.alarmCancelled,is_cpj=True)# 会写finished==1
                    self.logger.error('重新评估信号完成{}'.format(str(finished_mainid)))




            except Exception as e:
                self.logger.error('threading consumer error')
                self.logger.error(traceback.format_exc())

# 接收来自采集端、算法端得到的字段信息
class HttpProcess(multiprocessing.Process):
    def __init__(self, index, alive, alarmCancelled, json_queue, finished_queue, sys_setting, daemon=True):
        multiprocessing.Process.__init__(self, daemon=daemon)
        self.cfg_runner = sys_setting.cfg_runner
        self.host = self.cfg_runner['HttpProcess']['http_host']
        self.port = self.cfg_runner['HttpProcess']['http_port']
        self.index = index
        self.json_queue = json_queue
        self.finished_queue = finished_queue
        self.alive = alive
        self.alarmCancelled = alarmCancelled
        self.logger = sys_setting.logger

    def run(self):
        self.logger.info('HttpProcess {} start running'.format(self.index))
        MyHTTPServer(self.host, int(self.port), self.json_queue, self.finished_queue, self.logger, self.alive,self.alarmCancelled)


if __name__ == '__main__':
    pass
