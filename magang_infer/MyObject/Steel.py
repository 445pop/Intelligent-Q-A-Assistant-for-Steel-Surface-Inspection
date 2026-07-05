from MyObject.Defect import SteelDefect, RepeatDefect
from UtilObject.AggregationUtil import Aggregation
from UtilObject.PeriodUtil import Period
from UtilObject.DepthUtil import get_depth
from MyObject.ProjectConfig import Grade
import traceback


class Steel:
    @staticmethod
    def transform_length(cfg_runner, pixel_length, need_y=True, gg='default'):
        if need_y:
            temp_value = cfg_runner['Image']['rate_pixel2real_y'][gg] * pixel_length
        else:
            temp_value = cfg_runner['Image']['rate_pixel2real_x'][gg] * pixel_length
        if temp_value < 0.01:
            temp_value = 0.01
        return round(temp_value, 3)

    def __init__(self, main_id, sys_setting, cu_defect_list, steel_info):
        self.score = 100
        self.grade = '优秀'  # 优秀、良好、较差
        # 判断应用状态 是否到截至时间
        self.cu_run_state = True
        self.steel_defect_total_ids = []
        self.steel_defect_total_ids_str = ''
        self.main_id = main_id
        self.sys_setting = sys_setting
        self.cfg_runner = sys_setting.cfg_runner
        self.logger = sys_setting.logger
        self.appraise_type_dict = sys_setting.appraise.appraise_type_dict
        self.appraise_num = {}
        self.steel_info = steel_info
        for name, member in Grade.__members__.items():
            self.appraise_num[name] = 0
        self.appraise_types_count = {}
        # 每个类的缺陷数目 初始全是0
        for type_id in self.cfg_runner['Detect']['type_trans_a2c']:
            if type_id not in self.appraise_types_count.keys():
                self.appraise_types_count[type_id] = {}
            for name, member in Grade.__members__.items():  # 每类的各种级别的数目
                self.appraise_types_count[type_id][name] = 0

        self.score_threshold = sys_setting.appraise.score_threshold
        self.aggregation = Aggregation()
        self.period = Period(self.logger)
        # 额外新增
        self.cu_defect_list = cu_defect_list

        self.image_defect_type_dict = {}
        self.steel_defect_type_dict = {}
        self.repeat_defect_list = {}  # 周期缺陷 对应多个钢材缺陷
        self.steel_defect_num = 0
        self.send_client_extra_info = []  # 有些报警信息(两次评级导致翘皮还有面积报警)只能在钢材处理中产生，所以在这里定义
        # 永刚新加 缺陷图片占比
        self.image_defect_camera_flow_dict = {}

    def process_defect(self):
        # 1：点火坑距离铸坯头部距离(mm)
        # 2：点火坑宽面点火坑深度
        # 3：点火坑窄面点火坑深度
        # 4：漏清宽面漏清率
        # 5：漏清窄面漏清率
        # 6：深度
        # 7：缺陷尺寸（面积）
        appraise_condition0 = self.cfg_runner['Conclusion']['appraise_condition'][0]  
        appraise_condition1 = self.cfg_runner['Conclusion']['appraise_condition'][1]  
        appraise_condition2 = self.cfg_runner['Conclusion']['appraise_condition'][2]  
        appraise_condition3 = self.cfg_runner['Conclusion']['appraise_condition'][3]  
        appraise_condition4 = self.cfg_runner['Conclusion']['appraise_condition'][4]  
        appraise_condition5 = self.cfg_runner['Conclusion']['appraise_condition'][5]  
        appraise_condition6 = self.cfg_runner['Conclusion']['appraise_condition'][6]  
        # cu_defect_list是从database的es数据库中根据mainid查询得到
        # 首先根据缺陷类型分类，放入image_defect_type_dict（根据类型分开的图像缺陷）以缺陷typeid为主键，内容是缺陷信息
        for es_defect in self.cu_defect_list:
            try:
                # 过滤不需要的type_id
                if es_defect['type'] not in self.cfg_runner['Conclusion']['typeid_need_summary']:
                    continue

                # 2m过滤点火坑 超过某个flow_id, steel_length
                if es_defect['type'] == 15:
                    if es_defect['flow_id']>4:
                        continue

                if 'flow_id' not in es_defect.keys():
                    self.logger.error('无flow_id:' + str(es_defect['flow_id']))

                if es_defect['type'] not in self.image_defect_type_dict.keys():
                    self.image_defect_type_dict[es_defect['type']] = []
                    self.steel_defect_type_dict[es_defect['type']] = []
                    self.repeat_defect_list[es_defect['type']] = []

                self.image_defect_type_dict[es_defect['type']].append(es_defect)
                if es_defect['camera_id'] not in self.image_defect_camera_flow_dict.keys():
                    # 缺陷图片占比 根据相机号走
                    self.image_defect_camera_flow_dict[es_defect['camera_id']] = []
                self.image_defect_camera_flow_dict[es_defect['camera_id']].append(es_defect['flow_id'])
            except Exception as e:
                self.logger.error('es image_defect error')
                self.logger.error('es image_defect :' + str(es_defect))
                self.logger.error(traceback.format_exc())
        # 用于统计缺陷图像占比的遍历循环
        for c, flow_list in self.image_defect_camera_flow_dict.items():
            self.image_defect_camera_flow_dict[c] = set(flow_list)
        # 用于根据类别进行缺陷聚合
        for type_id, type_defects in self.image_defect_type_dict.items():
            defect_surface_dict = {}
            surface_id_chinese_dict = {}
            surface_id_chinese_dict[1] = "西"
            surface_id_chinese_dict[2] = "上"
            surface_id_chinese_dict[3] = "下"
            surface_id_chinese_dict[4] = "东"
            # 根据表面号分组（点火坑、漏清表面聚合）
            for es_defect in type_defects:
                try:
                    surface_id = es_defect['surface_id']
                except:
                    print(es_defect)
                # 自适应读取相机号
                if surface_id not in defect_surface_dict.keys():
                    defect_surface_dict[surface_id] = []
                # 存同一类、同一个相机的全部缺陷
                defect_surface_dict[surface_id].append(es_defect)
            defect_camera_dict = {}                
            # 根据相机号分组（凹槽、起楞相机聚合）
            for es_defect in type_defects:
                try:
                    camera_id = es_defect['camera_id']
                except:
                    print(es_defect)
                # 自适应读取相机号
                if camera_id not in defect_camera_dict.keys():
                    defect_camera_dict[camera_id] = []
                # 存同一类、同一个相机的全部缺陷
                defect_camera_dict[camera_id].append(es_defect)
            # 根据图像缺陷计算钢材缺陷[表面分组]
            for surface_id, surface_defects in defect_surface_dict.items():
                appraise_type = self.appraise_type_dict[type_id]
                type_name = self.cfg_runner['Detect']['typeid_chinese'][type_id]
                if type_id == 15:
                    #点火坑评级
                    #初始化
                    real_size = 0
                    image_defect_id_list = []
                    deep_value_list = []
                    #创建一个钢材缺陷
                    steel_defect = SteelDefect()
                    #遍历每个面
                    #根据这个面第一个缺陷写一些钢材缺陷信息
                    steel_defect.set_parm_by_dhk_defect(self.cfg_runner, surface_defects[0], gg=str(surface_defects[0]['camera_id']))
                    for dhk_defect in surface_defects:
                        # 累加每个点火坑的面积
                        real_size += round(dhk_defect['w']*dhk_defect['h'],2)
                        # 把每个图像缺陷记录下来，写入image_defect_id_list
                        image_defect_id_list.append(dhk_defect['id'])
                        # 记录每个图像缺陷的深度，取平均作为钢材缺陷的深度
                        deep_value_list.append(dhk_defect['real_depth'])
                    # 点火坑面积写入钢材缺陷
                    steel_defect.real_depth = (sum(deep_value_list)/len(deep_value_list))
                    steel_defect.real_size = real_size
                    # 把所有的图像缺陷合并,写入钢材缺陷
                    image_defect_ids_text = ','.join(image_defect_id_list)
                    steel_defect.image_defect_ids_text = image_defect_ids_text

                    # 四个面都要判断头部距离
                    steel_defect.set_grade_loss_from_conclusion(self.cfg_runner,
                                                                self.appraise_type_dict[type_id],
                                                                appraise_condition0)
                    
                    if steel_defect.surface_id in [2,3]:
                        # 如果是上下表
                        # 判断评级条件类型：上下表深度
                        steel_defect.set_grade_loss_from_conclusion(self.cfg_runner,
                                                                self.appraise_type_dict[type_id],
                                                                appraise_condition1)
                    elif steel_defect.surface_id in [1,4]:
                        # 如果是侧表
                        # 判断评级条件类型：侧表深度
                        steel_defect.set_grade_loss_from_conclusion(self.cfg_runner,
                                                                self.appraise_type_dict[type_id],
                                                                appraise_condition2)
                    #结合两个条件得到最后结果
                    steel_defect.contact_grade_loss_dhk(self.appraise_type_dict[type_id])
                    for dhk_defect in surface_defects:
                        # 更新图像缺陷
                        dhk_defect['steel_defect_id'] = steel_defect.id
                        dhk_defect['grade'] = steel_defect.grade
                    # 写入报警信息
                    if steel_defect.grade_dhk1 == "报警":
                        message = '{}批次中, {}表面{:.2f}m处出现头部距离为{:.2f}mm的[点火坑]缺陷报警！\n'.format(
                                                            str(self.main_id),
                                                            surface_id_chinese_dict[steel_defect.surface_id],
                                                            round(dhk_defect['real_y'] / 1000, 2),
                                                            steel_defect.top_distance)
                        info = (message,steel_defect)
                        self.send_client_extra_info.append(info)
                    if steel_defect.grade_dhk2 == "报警":
                        message = '{}批次中, {}表面{:.2f}m处出现深度为{:.2f}mm的[点火坑]缺陷报警！\n'.format(
                                                            str(self.main_id),
                                                            surface_id_chinese_dict[steel_defect.surface_id],
                                                            round(dhk_defect['real_y'] / 1000, 2),
                                                            steel_defect.real_depth)
                        info = (message,steel_defect)
                        self.send_client_extra_info.append(info)
                    # 属性处理
                    # self.logger.error("steel_defect.loss{}，grade{}".format(steel_defect.loss,steel_defect.grade))
                    self.score -= steel_defect.loss
                    self.steel_defect_type_dict[type_id].append(steel_defect.get_dict())
                    self.steel_defect_total_ids.append(steel_defect.id)
                    self.appraise_num[steel_defect.grade] += 1
                    self.appraise_types_count[type_id][steel_defect.grade] += 1
                elif type_id == 0:
                    #漏清评级
                    #初始化
                    real_size = 0
                    image_defect_id_list = []
                    #创建一个钢材缺陷
                    steel_defect = SteelDefect()

                    #根据这个面第一个缺陷写一些钢材缺陷信息
                    steel_defect.set_parm_by_lq_defect(self.cfg_runner, surface_defects[0], gg=str(surface_defects[0]['camera_id']))
                    deep_value_list = []
                    real_size = 0
                    for lq_defect in surface_defects:
                        # 累加每个漏清的面积
                        real_size += round(lq_defect['real_w']*lq_defect['real_h'],2)
                        # 把每个图像缺陷记录下来，写入image_defect_id_list
                        image_defect_id_list.append(lq_defect['id'])
                        # 记录每个图像缺陷的深度，取平均作为钢材缺陷的深度
                        deep_value_list.append(lq_defect['real_depth'])
                    # 漏清面积写入钢材缺陷
                    steel_defect.real_depth = (sum(deep_value_list)/len(deep_value_list))
                    steel_defect.real_size = real_size
                    # 把所有的图像缺陷合并,写入钢材缺陷
                    image_defect_ids_text = ','.join(image_defect_id_list)
                    steel_defect.image_defect_ids_text = image_defect_ids_text

                    # 获取钢板长宽高
                    real_length = self.steel_info[5]
                    real_height = self.steel_info[6]
                    real_width = self.steel_info[7]

                    if steel_defect.surface_id in [2,3]:
                        # 如果是上下表
                        # 判断评级条件类型：上下表深度
                        # 计算钢板面积、漏清率
                        steel_size = round(real_length*real_width,2)
                        steel_defect.area_rate = round((real_size*100)/steel_size,2)

                        steel_defect.set_grade_loss_from_conclusion(self.cfg_runner,
                                                                self.appraise_type_dict[type_id],
                                                                appraise_condition3)
                    elif steel_defect.surface_id in [1,4]:
                        # 如果是侧表
                        # 判断评级条件类型：侧表深度
                        # 计算钢板面积、漏清率
                        steel_size = round(real_length*real_height,2)
                        steel_defect.area_rate = round((real_size*100)/steel_size,2)

                        steel_defect.set_grade_loss_from_conclusion(self.cfg_runner,
                                                                self.appraise_type_dict[type_id],
                                                                appraise_condition4)

                    # 写入报警信息
                    if steel_defect.grade == "报警":
                        message = '{}批次中, {}表面{:.2f}m处出现漏清率为{:.2f}%的[漏清]缺陷报警！\n'.format(
                                                            str(self.main_id),
                                                            surface_id_chinese_dict[steel_defect.surface_id],
                                                            round(lq_defect['real_y'] / 1000, 2),
                                                            steel_defect.area_rate)
                        info = (message,steel_defect)
                        self.send_client_extra_info.append(info)
                    for lq_defect in surface_defects:    
                        # 更新图像缺陷
                        lq_defect['steel_defect_id'] = steel_defect.id
                        lq_defect['grade'] = steel_defect.grade
                    # 属性处理
                    # self.logger.error("steel_defect.loss{}，grade{}".format(steel_defect.loss,steel_defect.grade))
                    self.score -= steel_defect.loss
                    self.steel_defect_type_dict[type_id].append(steel_defect.get_dict())
                    self.steel_defect_total_ids.append(steel_defect.id)
                    self.appraise_num[steel_defect.grade] += 1
                    self.appraise_types_count[type_id][steel_defect.grade] += 1
                elif appraise_type.need_other_depth:
                    for depth_defect in surface_defects:  
                        steel_defect = SteelDefect()
                        steel_defect.set_parm_by_depth_defect(self.cfg_runner, depth_defect,gg=str(depth_defect['camera_id']))
                        # 判断评级条件类型：深度
                        steel_defect.set_grade_loss_from_conclusion(self.cfg_runner,
                                                                    self.appraise_type_dict[type_id],
                                                                    appraise_condition5)
                        # 获取钢材缺陷深度与图像缺陷深度

                        # 更新图像缺陷
                        depth_defect['steel_defect_id'] = steel_defect.id
                        depth_defect['grade'] = steel_defect.grade
                        # 写入报警信息
                        if steel_defect.grade == "报警":
                            message = '{}批次中, {}表面{:.2f}m处出现深度为{:.2f}mm的[{}]报警缺陷！\n'.format(
                                                            str(self.main_id),
                                                            surface_id_chinese_dict[steel_defect.surface_id],
                                                            round(depth_defect['real_y'] / 1000, 2),
                                                            steel_defect.real_depth,
                                                            type_name)
                            info = (message,steel_defect)
                            self.send_client_extra_info.append(info)
                        # 属性处理
                        # self.logger.error("steel_defect.loss{}，grade{}".format(steel_defect.loss,steel_defect.grade))
                        self.score -= steel_defect.loss                        
                        self.steel_defect_type_dict[type_id].append(steel_defect.get_dict())
                        self.steel_defect_total_ids.append(steel_defect.id)
                        self.appraise_num[steel_defect.grade] += 1
                        self.appraise_types_count[type_id][steel_defect.grade] +=1
                elif appraise_type.need_area:
                    for area_defect in surface_defects:  
                        steel_defect = SteelDefect()
                        steel_defect.set_parm_by_area_defect(self.cfg_runner, area_defect,gg=str(area_defect['camera_id']))
                        # 判断评级条件类型：面积
                        steel_defect.set_grade_loss_from_conclusion(self.cfg_runner,
                                                                    self.appraise_type_dict[type_id],
                                                                    appraise_condition6)
                        # 更新图像缺陷
                        area_defect['steel_defect_id'] = steel_defect.id
                        area_defect['grade'] = steel_defect.grade
                        # 写入报警信息
                        if steel_defect.grade == "报警":
                            message = '{}批次中, {}表面{:.2f}m处出现大小为{:.2f}mm^2的大面积[{}]报警缺陷！\n'.format(
                                                            str(self.main_id),
                                                            surface_id_chinese_dict[steel_defect.surface_id],
                                                            round(area_defect['real_y'] / 1000, 2),
                                                            steel_defect.real_size,
                                                            type_name
                                                            )
                            info = (message,steel_defect)
                            self.send_client_extra_info.append(info)
                        # 属性处理
                        # self.logger.error("steel_defect.loss{}，grade{}".format(steel_defect.loss,steel_defect.grade))
                        self.score -= steel_defect.loss
                        self.steel_defect_type_dict[type_id].append(steel_defect.get_dict())
                        self.steel_defect_total_ids.append(steel_defect.id)
                        self.appraise_num[steel_defect.grade] += 1
                        self.appraise_types_count[type_id][steel_defect.grade] +=1
            # 根据图像缺陷计算钢材缺陷[相机分组]
            for camera_id, camera_defects in defect_camera_dict.items():
                appraise_type = self.appraise_type_dict[type_id]
                if appraise_type.need_merge:
                    y_grouping_space = self.cfg_runner['Conclusion']['merge_setting']['y_grouping_space']
                    x_grouping_space = self.cfg_runner['Conclusion']['merge_setting']['x_grouping_space']
                    s_threshold = self.cfg_runner['Conclusion']['merge_setting']['s_threshold']
                    y_error = (y_grouping_space * 1000) / self.cfg_runner['Image']['rate_pixel2real_y'][
                        str(camera_id)]  # 2m为纵向间隔
                    merge_defect_list = self.aggregation.target_types_defect_merge(camera_defects,
                                                                                   self.cfg_runner['Image'][
                                                                                       'image_h'],
                                                                                   s_threshold=s_threshold,
                                                                                   x_error=x_grouping_space,
                                                                                   y_error=y_error)

                    for merge_defect in merge_defect_list:
                        steel_defect = SteelDefect()
                        image_defect_id_list = []
                        deep_value_list = []
                        real_size = 0

                        steel_defect.set_parm_by_merge_defect(self.cfg_runner, merge_defect,camera_id ,gg=str(camera_id))
                        steel_defect.main_id = self.main_id
                        if camera_id in [1]:
                            steel_defect.surface_id = 1
                        elif camera_id in [2,3]:
                            steel_defect.surface_id = 2
                        elif camera_id in [5,6,7]:
                            steel_defect.surface_id = 3
                        elif camera_id in [4]:
                            steel_defect.surface_id = 4
                        
                        steel_defect.type = type_id
                        # 判断评级条件类型：深度
                        steel_defect.set_grade_loss_from_conclusion(self.cfg_runner,
                                                                    self.appraise_type_dict[type_id],
                                                                    appraise_condition5)
                        # 更新图像缺陷
                        for cu_image_defect in merge_defect['img_defect']:
                            real_size += round(cu_image_defect['real_w']*cu_image_defect['real_h'],2)
                            image_defect_id_list.append(cu_image_defect['id'])
                            deep_value_list.append(cu_image_defect['real_depth'])
                        image_defect_ids_text = ','.join(image_defect_id_list)
                        steel_defect.image_defect_ids_text = image_defect_ids_text
                        steel_defect.real_size = real_size
                        steel_defect.real_depth = (sum(deep_value_list)/len(deep_value_list))
                        # 写入报警信息
                        if steel_defect.grade == "报警":
                            message = '{}批次中, {}表面{:.2f}m处出现深度为{:.2f}mm的[{}]报警缺陷！\n'.format(
                                                            str(self.main_id),
                                                            steel_defect.surface_id,
                                                            round(merge_defect['img_defect'][0]['real_y'] / 1000, 2),
                                                            steel_defect.real_depth,
                                                            type_name
                                                            )
                            info = (message,steel_defect)
                            self.send_client_extra_info.append(info)
                        for cu_image_defect in merge_defect['img_defect']:
                            # 更新图像缺陷
                            cu_image_defect['steel_defect_id'] = steel_defect.id
                            cu_image_defect['grade'] = steel_defect.grade
                        # self.logger.error("steel_defect.loss{}，grade{}".format(steel_defect.loss,steel_defect.grade))
                        self.score -= steel_defect.loss
                        self.steel_defect_type_dict[type_id].append(steel_defect.get_dict())
                        self.steel_defect_total_ids.append(steel_defect.id)
                        self.appraise_num[steel_defect.grade] += 1
                        self.appraise_types_count[type_id][steel_defect.grade] += 1


        for type_id, type_defects in self.steel_defect_type_dict.items():
            self.steel_defect_num += len(type_defects)
        self.score = round(self.score, 2)
        # 钢材评级
        if self.score <= self.score_threshold['low']:
            self.grade = '较差'
        elif self.score <= self.score_threshold['high']:
            self.grade = '良好'
        else:
            self.grade = '优秀'
        # self.steel_defect_total_ids_str = ','.join(self.steel_defect_total_ids)
