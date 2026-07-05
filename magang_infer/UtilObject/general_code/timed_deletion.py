import copy
import json
import math
import shutil
import os
import datetime
import time
# from multiprocessing import Process
from threading import Thread

import numpy as np

from es_utils_old import ESoperation, IMAGE_DEFECT
from elasticsearch.helpers import bulk
from elasticsearch import Elasticsearch
from logger import logger
import traceback
import sys
from tqdm import tqdm
from pathlib import Path
from DBUtils.PooledDB import PooledDB
import pymysql

from collections import defaultdict
import cv2
#南南铝定时删除并补充小裁剪图像
es = ESoperation()
LOCALHOST = '192.168.1.102'
SERVER = 'server102'
CAMERA_LIST = [1, 2]
IMAGE_TABLE = "image"
DAY_GAP = 1
DAY_KEEP = 40
TARGET_HOUR = 12
minute = 0
crop_size = 1024
img_width_pix = 4096
dir_batch = r'D:\grab_img'
out_crop_dir = r'D:\crop_img'
labelme_template = {'version': '5.1.1', 'flags': {}, 'shapes': [{'label': 'yishi', 'points': [[496.0, 258.0], [518.0, 290.0]], 'group_id': None, 'shape_type': 'rectangle', 'flags': {}}], 'imagePath': 'pic_1.jpg', 'imageHeight': 1024, 'imageWidth': 1024, 'imageData': None}


MYSQL_CON = PooledDB(
    creator=pymysql,  # 驱动
    maxconnections=1,  # 最大连接数
    mincached=1,  # 初始化时，连接池中至少创建的空闲连接，0表示不创建
    maxcached=1,  # 连接池中最多允许的空闲连接数，超过部分会被关闭并回收
    blocking=True,  # 当连接池中没有可用连接时，是否阻塞等待，True表示等待，False表示不等待抛出异常
    maxshared=1,  # 连接池中最多允许的共享连接数，0表示不共享
    setsession=[],  # 设置会话参数
    ping=1,  # 检查MySQL服务器是否可用
    host='192.168.2.112',  # 数据库地址
    port=3306,
    user='root',  # 数据库用户名
    password='123456',  # 数据库密码
    database='steeldetection',  # 数据库名称
)

url_dict = {
    '/server101/': '/backup/server101/',
    '/server102/': '/backup/server102/',
}


def get_oldest_directory_with_keyword(keyword, path):
    # 获取目录下的所有文件和子目录
    entries = os.scandir(path)

    # 过滤出目录名包含关键字的目录
    relevant_directories = [entry for entry in entries if entry.is_dir() and keyword in entry.path]

    # print("relevant_directories:",relevant_directories)

    if not relevant_directories:
        return None

    # 按创建时间排序
    relevant_directories.sort(key=lambda entry: entry.stat().st_ctime)

    # 返回最早创建的目录名字
    return relevant_directories[0].name


def get_main_from_custom_id(custom_id):
    try:
        conn = MYSQL_CON.connection()
        with conn.cursor() as cursor:
            sql = 'SELECT main_id from batch where user_custom_id = "{}" ;'.format(custom_id)
            # logger.info(sql)
            cursor.execute(sql)
            conn.commit()
            cursor.close()
            conn.close()
            # logger.info("{} Mysql提交成功".format(main_id))
    except Exception as e:
        logger.error("数据库操作异常：\n", e)
        logger.error(traceback.format_exc())
    finally:
        conn.close()
    result = cursor.fetchone()[0]
    return result


def crop_img_backup(main_id):
    logs = es.search(main_id=main_id, table_name=IMAGE_DEFECT)

    if len(logs) == 0:
        logger.info('批次{}的缺陷数为0.'.format(main_id))
        return
    else:
        logger.info('批次{}的缺陷数为{}.'.format(main_id, len(logs)))
    logs = [log['_source'] for log in logs]
    img_defect_dict = defaultdict(list)
    try:
        for log in logs:
            image_url = log['image_url']
            surface_id = log['surface_id']
            if surface_id == 2:
                image_name = image_url.split('\\')[-1]
                img_defect_dict[image_name].append(log)
    except:
        log.error("image_url get error!")

    for image_name, defects in img_defect_dict.items():
        shape_list = []
        image_url = os.path.join(dir_batch, main_id,'compose', image_name)
        for i, log in enumerate(defects):
            # 如果用户删除了，就不备份了
            if log['is_user_delete']:
                continue

            x = int(log['x'])
            y = int(log['y'])
            w = int(log['w'])
            h = int(log['h'])
            label = str(log['type'])

            shape_list.append([label, x, y, w, h])
        try:
            # 写裁剪图与图片json
            get_CropSize_Pic_json1(image_url,main_id,shape_list)

        except Exception as e:
            logger.error(e)
            logger.error("image url crop error：{}".format(image_url))

def get_CropSize_Pic_json(pic_path, mainid, shape_list):
    mainid_path = os.path.join(out_crop_dir, mainid)
    os.makedirs(mainid_path, exist_ok=True)

    num = 0  # 起始文件名
    # 获取图片路径和大小
    pic = cv2.imdecode(np.fromfile(pic_path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    # 文件名
    name = pic_path.split('\\')[-1]
    basename = os.path.splitext(name)[0]
    height, width = pic.shape[:2]
    # crop_size = cropSize
    # 一列多少个
    colNum = math.ceil(height / crop_size)
    # 一行多少个
    rowNum = math.ceil(width / crop_size)
    print(height, width, rowNum, colNum, pic_path)
    for i in range(rowNum):
        for j in range(colNum):
            # 计算裁剪位置
            x = i * crop_size
            y = j * crop_size
            _width = crop_size
            _height = crop_size
            if y + crop_size > height:
                _height = height % crop_size
            if x + crop_size > width:
                _width = width % crop_size
            # 裁剪图片
            # crop_img = np.zeros((crop_size, crop_size,3), dtype=np.uint8)
            crop_img = pic[y:y + _height, x:x + _width]

            # 文件名设置

            temp_name = 'pic' + '_' + str(num) + ".jpg"
            temp_path = os.path.join(out_crop_dir, mainid, temp_name)
            while os.path.exists(temp_path):
                num += 1
                temp_name = 'pic' + '_' + str(num) + ".jpg"
                temp_path = os.path.join(out_crop_dir, mainid, temp_name)

            temp_json_name = 'pic' + '_' + str(num) + ".json"
            # 判断本块是否含有缺陷
            list_defects = []
            # 遍历每个标注框
            for k in range(len(shape_list)):
                # 获取标注框的类别和坐标
                label = shape_list[k][0]

                xmin, ymin = shape_list[k][1], shape_list[k][2]
                xmax, ymax = shape_list[k][3], shape_list[k][4]

                tempData = copy.deepcopy(labelme_template['shapes'][0])

                # 合格点
                if x <= xmin < x + _width and x <= xmax < x + _width and y <= ymin < y + _height and y <= ymax < y + _height:
                    tempData['points'][0] = [xmin % crop_size, ymin % crop_size]
                    tempData['points'][1] = [xmax % crop_size, ymax % crop_size]
                    list_defects.append(tempData)
                if x <= xmin < x + _width and (not x <= xmax < x + _width) and y <= ymin < y + _height and (
                        y <= ymax < y + _height):
                    # 增加这个范围内的点
                    tempData['points'][0] = [xmin % crop_size, ymin % crop_size]
                    tempData['points'][1] = [(x + _width - 1) % crop_size, ymax % crop_size]
                    list_defects.append(tempData)

                    # 增加data作为别的点
                    shape_list.append([label,x+_width,ymin,xmax,ymax])
                if x <= xmin < x + _width and (x <= xmax < x + _width) and y <= ymin < y + _height and not (
                        y <= ymax < y + _height):
                    # 增加这个范围内的点
                    tempData['points'][0] = [xmin % crop_size, ymin % crop_size]
                    tempData['points'][1] = [xmax % crop_size, (y + _height - 1) % crop_size]
                    list_defects.append(tempData)
                    # 增加data作为别的点
                    shape_list.append([label, xmin, y + _height, xmax, ymax])
                if x <= xmin < x + _width and not (x <= xmax < x + _width) and y <= ymin < y + _height and not (
                        y <= ymax < y + _height):
                    # 增加这个范围内的点
                    tempData['points'][0] = [xmin % crop_size, ymin % crop_size]
                    tempData['points'][1] = [(x + _width - 1) % crop_size, (y + _height - 1) % crop_size]
                    list_defects.append(tempData)

                    # 增加data作为别的点
                    shape_list.append([label, xmin, y + _height, x + _width, ymax])# 下
                    shape_list.append([label, x + _width, ymin,xmax, y + _height])# 右
                    shape_list.append([label, x + _width, y + _height, xmax, ymax])  # 右下

            if len(list_defects) != 0:

                # 创建json数据
                jsondata = labelme_template.copy()
                jsondata["shapes"] = []
                jsondata['imagePath'] = temp_name
                jsondata['imageHeight'] = crop_size
                jsondata['imageWidth'] = crop_size


                for info_data in list_defects:
                    jsondata["shapes"].append(info_data)
                json_str = json.dumps(jsondata, indent=4, ensure_ascii=False)
                temp_json_path = os.path.join(out_crop_dir, mainid, temp_json_name)

                with open(temp_json_path, 'w', encoding='utf-8') as json_file:
                    json_file.write(json_str)
                # 写图
                cv2.imencode(".jpg", crop_img)[1].tofile(temp_path)

def get_CropSize_Pic_json1(pic_path, mainid, shape_list):
    mainid_path = os.path.join(out_crop_dir, mainid)
    os.makedirs(mainid_path, exist_ok=True)

    num = 0  # 起始文件名
    # 获取图片路径和大小
    pic = cv2.imdecode(np.fromfile(pic_path, dtype=np.uint8), cv2.IMREAD_COLOR)

    name = pic_path.split('\\')[-1]
    basename = os.path.splitext(name)[0]

    # 遍历每个标注框
    for k in range(len(shape_list)):
        # 获取标注框的类别和坐标
        label = shape_list[k][0]

        x, y = shape_list[k][1], shape_list[k][2]
        w, h = shape_list[k][3], shape_list[k][4]

        pad_size = 10
        crop_x, crop_y = max(x - pad_size, 0), max(y - pad_size, 0)
        crop_w, crop_h = min(img_width_pix, x + w + pad_size) - crop_x, min(img_width_pix,
                                                                  y + h + pad_size) - crop_y
        crop_img = pic[crop_y:crop_y + crop_h, crop_x:crop_x + crop_w]
        # print('crop',x,y,w,h,crop_x,crop_y,crop_w,crop_h,crop_img.shape)
        temp_name = basename+'_'+label + '_' + str(num) + ".jpg"
        temp_path = os.path.join(out_crop_dir, mainid, temp_name)
        while os.path.exists(temp_path):
            num += 1
            temp_name = label + '_' + str(num) + ".jpg"
            temp_path = os.path.join(out_crop_dir, mainid, temp_name)
        cv2.imencode(".jpg", crop_img)[1].tofile(temp_path)


def task(from_time, to_time):
    try:
        logs = search_image(from_time, to_time)
    except Exception as e:
        traceback.print_exc()
        logger.error(e)
        return
    actions = []
    ids = []
    for i, log in enumerate(logs):
        try:
            _id = log.get("_id")
            doc = log.get("_source")
            old_path = doc['image_url']

            # move file
            src_path = old_path.replace('//' + LOCALHOST, '/diskb')
            dst_path = old_path.replace('//' + LOCALHOST, '/diskc')
            parent_dir = os.path.split(dst_path)[0]
            os.makedirs(parent_dir, exist_ok=True)
            if os.path.exists(src_path):
                shutil.move(src_path, dst_path)

            if doc['main_id'] not in ids:
                ids.append(doc['main_id'])
        except Exception as e:
            logger.error(e)

    logger.info('nums of images: {}'.format(len(logs)))

def task_crop_delete(to_time):
    # 先裁剪小图后删除
    dirs = search_dir(to_time)  # 早于to_time的批次
    mysql_pool = PooledDB(
        creator=pymysql,  # 驱动
        maxconnections=1,  # 最大连接数
        mincached=1,  # 初始化时，连接池中至少创建的空闲连接，0表示不创建
        maxcached=1,  # 连接池中最多允许的空闲连接数，超过部分会被关闭并回收
        blocking=True,  # 当连接池中没有可用连接时，是否阻塞等待，True表示等待，False表示不等待抛出异常
        maxshared=1,  # 连接池中最多允许的共享连接数，0表示不共享
        setsession=[],  # 设置会话参数
        ping=1,  # 检查MySQL服务器是否可用
        host='192.168.2.112',  # 数据库地址
        port=3306,
        user='root',  # 数据库用户名
        password='123456',  # 数据库密码
        database='steeldetection',  # 数据库名称
    )
    logger.info("=====================start_backup==============================")
    logger.info("len(dirs):{}".format(len(dirs)))
    logger.info("dirs:{}".format(dirs))
    tmp_i = 0
    for index, main_id in enumerate(dirs):
        try:
            tmp_i = tmp_i + 1
            logger.info("** Process:{}/{}, move: {} **".format(tmp_i, len(dirs), os.path.join(dir_batch, main_id)))
            logger.info("main-id: {}".format(main_id))
            status = 'archived'
        except Exception as e:
            logger.error("** Process:{}/{}, move: {} **".format(tmp_i, len(dirs), os.path.join(dir_batch, main_id)))
            logger.error("main-id lost, dir:{}", format(main_id))
        try:
            crop_img_backup(main_id)
            logger.info("***************crop备份完毕*********".format(main_id))
        except Exception as e:
            # todo
            logger.error("crop backup error!")
            logger.error(e)

        try:
            # 调用删除程序，删掉最老一天的原图数据
            current_mainid_path = os.path.join(dir_batch,main_id)
            shutil.rmtree(current_mainid_path)
            logger.error("Delete over:"+current_mainid_path)
            status = 'deleted'
        except Exception as e:
            logger.error("Delete error:"+current_mainid_path)
            logger.error(e)

        try:
            conn = mysql_pool.connection()
            with conn.cursor() as cursor:
                sql = 'update batch set img_status = "{}" where main_id = "{}" ;'.format(status, main_id)
                # logger.info(sql)
                cursor.execute(sql)
                conn.commit()
                cursor.close()
                conn.close()
                logger.info("{} Mysql提交成功".format(main_id))
        except Exception as e:
            logger.error("数据库操作异常：\n"+str(e))
            logger.error(traceback.format_exc())
        finally:
            conn.close()


def search_image(from_time, to_time):
    logs = []

    table_name = IMAGE_TABLE

    s_time = from_time
    e_time = to_time

    for camera_id in CAMERA_LIST:
        logs_ = es.search(table_name=table_name, camera_id=camera_id, s_time=s_time, e_time=e_time)
        logs += logs_
    # logs = es.search(table_name=table_name, camera_id=2, s_time=s_time, e_time=e_time, num_limit=10)
    return logs


def search_dir(to_time):
    dirs = []
    e_time = datetime.datetime.strptime(to_time, "%Y-%m-%dT%H:%M:%S")
    for item in Path(dir_batch).iterdir():
        if item.is_dir():
            item_name = item.name
            try:
                item_time = datetime.datetime.strptime(item_name, "%Y%m%d%H%M%S")
            except:
                continue

            time_difference = e_time - item_time

            # 检查差异的天数是否大于30
            if time_difference.days > DAY_KEEP:
                dirs.append(str(item_name))
    return dirs


def get_before_date(beforeOfDay):
    today = datetime.datetime.now()
    offset = datetime.timedelta(days=-beforeOfDay)
    re_date = (today + offset).strftime('%Y-%m-%d')
    return re_date + 'T00:00:00'


if __name__ == '__main__':
    hour_count = 0
    logger.info("Backup running.!!!!!!!!!!!!!!!!!!!!!!!!!!!! ")
    while (True):
        now_time = datetime.datetime.now()

        if (hour_count == 0 or hour_count == 3):  # 测试，不然是每隔多少小时测一次，先设置成2了,hour_count其实就是间隔几个小时。
            # if now_time.hour%3==1 and now_time.minute == 0: # 3的倍数备份一次
            yester_date = get_before_date(DAY_GAP - 1)
            logger.info('Backup the data before {}'.format(yester_date))  #
            t = Thread(target=task_crop_delete, args=(yester_date,))
            t.start()
            t.join()
            time.sleep(3 * 60 * 60)
            # time.sleep(15*60*60)
            hour_count = 1

        else:
            logger.info('Wating for one hour. ')
            time.sleep(60 * 60)
            hour_count += 1


    # logs = search_image('2023-03-20T00:00:00', '2023-03-20T01:00:00')
    # print(logs[0])
    # for log in logs:
    #     print(log)
    # task2('2023-09-29T00:00:00', '2023-09-30T00:00:00')
    # print(dirs)
