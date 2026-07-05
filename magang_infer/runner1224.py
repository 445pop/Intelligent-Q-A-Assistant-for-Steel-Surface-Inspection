# -- coding: utf-8 --**
# Copyright 2022 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# 处理每个相机前几张是空图来修正real值

import math
import os
from util.util_stitch.create3dpic import to3Dimg
import cv2
import glob
import json
import argparse
from tqdm import tqdm
import numpy as np
from collections import OrderedDict
# from pycocotools.coco import COCO
# from pycocotools.cocoeval import COCOeval
# from Yolov5_for_Pytorch.common.util.util_stitch.Stitcher import *pip
# from common.util.util_stitch.Stitcher import abc
from util.util_stitch.Stitcher import Stitcher

from util.acl_net_multiple import Net
from util.http_server import HTTPServer
from elasticsearch import Elasticsearch
import threading
import multiprocessing
from multiprocessing import Queue, Value, Manager
from threading import Thread
import datetime
import acl
import functools
import time
import sys
import socket
from elasticsearch import Elasticsearch
import uuid
from PIL import Image
import signal
import atexit
import copy
import pymysql
import logging
import random
from logging.handlers import RotatingFileHandler

np.set_printoptions(suppress=True)
cv2.setNumThreads(1)
os.environ['OPENBLAS_NUM_THREADS'] = '1'
# 训练时的图片大小
neth, netw = 640, 640
localhost = '192.168.100.3'
error_log = './error.log'
info_log = './info.log'
img_height_pix = 800

eshost = '192.168.100.3'
# 没用到
label_dict = {
    '0': 'gc',
    '1': 'ak',
    '2': 'ql',
    '3': 'cs',
    '4': 'qk',
    '5': 'lw',
}


class LogFilter(logging.Filter):
    """Filters (lets through) all messages with level < LEVEL"""

    # http://stackoverflow.com/a/24956305/408556
    def __init__(self, level):
        self.level = level

    def filter(self, record):
        # "<" instead of "<=": since logger.setLevel is inclusive, this should
        # be exclusive
        return record.levelno < self.level


MIN_LEVEL = logging.DEBUG
stdout_hdlr = logging.StreamHandler(sys.stdout)
stderr_hdlr = logging.StreamHandler(sys.stderr)
# 可自增日志
log_filename = f'logs/mg_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
filehandler = RotatingFileHandler(log_filename, maxBytes=5000000, backupCount=5, encoding='utf-8')
filehandler.setLevel(MIN_LEVEL)

log_filter = LogFilter(logging.WARNING)
stdout_hdlr.addFilter(log_filter)
stdout_hdlr.setLevel(MIN_LEVEL)
stderr_hdlr.setLevel(max(MIN_LEVEL, logging.WARNING))
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y/%m/%d %I:%M:%S')
stdout_hdlr.setFormatter(formatter)
stderr_hdlr.setFormatter(formatter)
filehandler.setFormatter(formatter)

rootLogger = logging.getLogger()
rootLogger.addHandler(filehandler)
rootLogger.addHandler(stdout_hdlr)
rootLogger.addHandler(stderr_hdlr)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# 将输入图像的上下或者左右添加填充，使其成为一个指定大小的矩形图像（640*640）
# img:输入图像 new_shape:目标图像大小
def letterbox(img, new_shape=(640, 640), color=(114, 114, 114), auto=False, scaleFill=False, scaleup=True):
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


# 将每个框的表示形式从 左上角和右下角坐标 转换为 中心坐标和宽度高度
def xyxy2xywh(x):
    # convert nx4 boxes from [x1, y1, x2, y2] to [x, y, w, h] where xy1=top-left, xy2=botttom-right
    y = np.copy(x)
    y[:, 0] = (x[:, 0] + x[:, 2]) / 2  # x center
    y[:, 1] = (x[:, 1] + x[:, 3]) / 2  # y center
    y[:, 2] = x[:, 2] - x[:, 0]  # width
    y[:, 3] = x[:, 3] - x[:, 1]  # height
    return y


# 获得固定尺寸大小(640*640)的图像 图像预处理
def preProcess(img_origin, neth, netw):
    try:
        imgh, imgw = img_origin.shape[:2]
        # img_origin = cv2.resize(img_origin, (1024, 1024), interpolation=cv2.INTER_LINEAR)
        img_origin = letterbox(img_origin, new_shape=(neth, netw))[0]

        img_info = np.stack([np.array([neth, netw, imgh, imgw], dtype=np.float16)], axis=0)
        img_origin = (np.stack([img_origin], axis=0))

        img = img_origin[..., ::-1].transpose(0, 3, 1, 2)  # BGR tp RGB
        image_np = np.array(img, dtype=np.float32)  # img 转换为NumPy数组
        image_np_expanded = image_np / 255.0  # 像素值进行归一化，将值范围从0到255缩放到0到1之间
        img = np.ascontiguousarray(image_np_expanded).astype(np.float16)  # image_np_expanded 转换为一个以连续内存存储的NumPy数组
        return img, img_info
    except Exception as e:
        with open(error_log, 'a', encoding='utf-8') as errlog:
            print(img_origin)
            logger.warning(str(datetime.datetime.now()) + ':' + img_origin + ' can not be read\n')
            return


def afterProcess(result, json_dict, instance_ulr_class, instance_d_class, input_img, net2source_Xsize, net2source_Ysize,
                 queue3d):
    defect_body_list = []
    batch_boxout, boxnum = result

    # name, postfix = basename.split('.')
    num_det = int(boxnum[0][0])
    boxout = batch_boxout[0][:num_det * 6].reshape(6, -1).transpose().astype(np.float32)  # 6xN -> Nx6

    box = xyxy2xywh(boxout[:, :4])
    box[:, :2] -= box[:, 2:] / 2  # xy center to top-left corner

    for p, b in zip(boxout.tolist(), box.tolist()):
        defect_id = str(uuid.uuid4())
        img3d_defect_id = str(uuid.uuid4())
        time_now = datetime.datetime.now()
        # 传递给前端的数据类型
        # 3d 原图路径
        if json_dict['surface_id'] != 3:
            defect_type = instance_ulr_class[int(p[5])]
            origin_inputpath = input_img.replace('gray', 'origin')
        else:
            defect_type = instance_d_class[int(p[5])]
            origin_inputpath = input_img
        x = b[0] * net2source_Xsize
        y = b[1] * net2source_Ysize
        w = b[2] * net2source_Xsize
        h = b[3] * net2source_Ysize
        if defect_type == 6:
            continue 
        output_path = input_img.replace('gray', '3d_img')

        # if p[5] == 4:
        #     continue

        queue3d.put((img3d_defect_id, origin_inputpath, output_path, json_dict, x, y, w, h))

        databody = {
            "id": defect_id,
            "main_id": json_dict['main_id'],
            "type": defect_type,
            "steel_defect_id": '',
            "surface_id": json_dict['surface_id'],
            "camera_id": json_dict['camera_id'],
            "insert_time": time_now,
            "x": int(x),
            "y": int(y),
            "w": int(w),
            "h": int(h),
            "real_x": int(0),
            "real_y": int(0),
            "real_w": int(w * 0.425),
            "real_h": int(h * 0.185),
            "confidence": round(p[4], 5),
            "grade": '',
            "is_visualize": True,
            "is_user_delete": False,
            # "image_id": json_dict['id'],
            "image_id": json_dict['deepimg_id'],
            "image2_id": json_dict['grayimg_id'],
            "image3_id": img3d_defect_id,
            "image4_id": '',
            "crop_image__url": '',
            "crop_image2__url": '',
            "crop_image3__url": '',
            "crop_image4__url": '',
            "image_url": json_dict['image_url'],
            "other0": '',
            "other1": '',
            "deepth": random.randint(1, 8)  # 缺陷深度
        }
        # print("databody = {}".format(databody))
        defect_body_list.append(databody)
    return defect_body_list


def afterProcessforQK(result, json_dict, instance_ulr_class, instance_d_class, input_img, net2source_Xsize,
                      net2source_Ysize,
                      queue3d, i, j, block_height=640):
    defect_qk_list = []
    batch_boxout, boxnum = result
    num_det = int(boxnum[0][0])
    boxout = batch_boxout[0][:num_det * 6].reshape(6, -1).transpose().astype(np.float32)  # 6xN -> Nx6

    box = xyxy2xywh(boxout[:, :4])
    box[:, :2] -= box[:, 2:] / 2  # xy center to top-left corner

    for p, b in zip(boxout.tolist(), box.tolist()):

        defect_id = str(uuid.uuid4())
        img3d_defect_id = str(uuid.uuid4())
        time_now = datetime.datetime.now()
        # 传递给前端的数据类型
        # 3d 原图路径
        if json_dict['surface_id'] != 3:
            defect_type = instance_ulr_class[int(p[5])]
            origin_inputpath = input_img.replace('gray', 'origin')
        else:
            defect_type = instance_d_class[int(p[5])]
            origin_inputpath = input_img

        # 还原推理结果识别框到原图
        x = b[0] * net2source_Xsize
        y = b[1] * net2source_Ysize
        w = b[2] * net2source_Xsize
        h = b[3] * net2source_Ysize
        #纯黑判定，生成
        left = int(x+i)
        right = int(x+i + w)
        top = int(y+i)
        bottom = int(h+i) + top
        if left > 3072 or left < 0  or right > 3072 or right < 0:
            continue
        if top > 4096 or top < 0 or bottom > 4096 or bottom < 0:
            continue
        #print("left",left,right,top,bottom)
        img = Image.open(input_img).convert('L') #灰度图        # 获取灰度图像的第一个像素值
        arr = np.array(img, dtype=float)
        first_pixel_value = arr[left, top]
        arr = arr[top:bottom, left:right]
        # 检查所有像素是否与第一个像素值相等
        is_monochrome = (arr == first_pixel_value).all()
        if is_monochrome:
            continue
        # 输出结果
        # if is_monochrome:
        #     return True
        # else:
        #     return False

        # img = Image.open(input_img).convert('L') #灰度图
        # arr = np.array(img, dtype=float)
        # arr = arr[top:bottom, left:right]
        # if np.all(arr == 0):
        #     print(arr)
        #     continue
        # if w < 1:
        #     w = 20
        # if h < 1:
        #     h = 20
        if w < 3:
            continue
        if h < 3:
            continue
        x_restored = x + i
        y_restored = y + j
        output_path = input_img.replace('gray', '3d_img')
        # print("x_restored:",x_restored,"y_restored:",y_restored,"x:",x,"y:",y,i,j)
        # print("defect type = {}".format(int(p[5])))

        if p[5] != 4:
            continue

        queue3d.put((img3d_defect_id, origin_inputpath, output_path, json_dict, x_restored, y_restored, w, h))
        print("queue3d",queue3d)
        databody = {
            "id": defect_id,
            "main_id": json_dict['main_id'],
            "type": defect_type,
            "steel_defect_id": '',
            "surface_id": json_dict['surface_id'],
            "camera_id": json_dict['camera_id'],
            "insert_time": time_now,
            "x": int(x_restored),
            "y": int(y_restored),
            "w": int(w),
            "h": int(h),
            "real_x": int(0),
            "real_y": int(0),
            #"real_w": int(w * 0.425),
            #"real_h": int(h * 0.185),
            "real_w": int(w),
            "real_h": int(h),
            "confidence": round(p[4], 5),
            "grade": '',
            "is_visualize": True,
            "is_user_delete": False,
            # "image_id": json_dict['id'],
            "image_id": json_dict['deepimg_id'],
            "image2_id": json_dict['grayimg_id'],
            "image3_id": img3d_defect_id,
            "image4_id": '',
            "crop_image__url": '',
            "crop_image2__url": '',
            "crop_image3__url": '',
            "crop_image4__url": '',
            "image_url": json_dict['image_url'],
            "other0": '',
            "other1": '',
            "deepth": random.randint(1, 8)  # 缺陷深度
        }
        defect_qk_list.append(databody)
        # print("databody = {}".format(databody))

    return defect_qk_list


# 裁剪图像
def crop_image(image, i, j, new_width, new_height):
    # 获取原始图片的尺寸
    height, width, _ = image.shape

    # 计算裁剪的起始位置和结束位置
    # left = (width - new_width) // 2
    # top = (height - new_height) // 2
    left = j
    top = i
    right = left + new_width
    bottom = top + new_height

    # 裁剪图片
    cropped_image = image[top:bottom, left:right]

    # 返回裁剪后的图片
    return cropped_image


# 检查图像是否为纯色图像
def is_black_image(image):
    # 将图像转换为灰度图像
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 获取灰度图像的第一个像素值
    first_pixel_value = gray_image[0, 0]

    # 检查所有像素是否与第一个像素值相等
    is_monochrome = (gray_image == first_pixel_value).all()

    # 输出结果
    if is_monochrome:
        return True
    return False


# 根据模型自动推理
def threading_predict_origin(model_ulr, model_ulr_qk, model_d, input_img, instance_ulr_class, instance_d_class,
                             json_dict, predict_queue, res_queue,
                             queue3d, upsample, signal_str):
    # 过钢结束信号
    if signal_str == 1:
        predict_queue.put(
            (-1, str(json_dict['main_id']), -1, signal_str, None, None))
        logger.info("{}: get_http_info :{}".format(datetime.datetime.now(), signal_str))
        return
    # 只对灰度图片进行推理
    # 图像预处理
    img_origin = cv2.imread(input_img)
    img, img_info = preProcess(img_origin, 640, 640)
    result = None
    # 当前图片的全部缺陷list
    defect_body_list = []
    defect_body_list_normal = []

    # 还原坐标
    net2source_Xsize = 1
    net2source_Ysize = 1
    # 假如非下表
    if json_dict['surface_id'] != 3:
        if model_ulr is not None:
            # 先检测其他缺陷
            result, dt = model_ulr([img, img_info])  # net out, infer time

        elif model_ulr_qk is not None:
            ########## 单独检测气孔 上左右：3072*4096 ############
            #xia 2048*2730
            # 原始图片尺寸
            original_width = 3072
            original_height = 4096

            # 目标裁剪尺寸
            new_width = 640
            new_height = 640
            # 进行循环裁剪和还原
            for i in range(0, original_width, new_width):
                for j in range(0, original_height, new_height):
                    defect_qk_list = []
                    # 裁剪图片
                    cropped_image = crop_image(img_origin, i, j, 640, 640)
                    # print("cropped_image shape h : {}, w : {}".format(cropped_image.shape[0], cropped_image.shape[1]))

                    if cropped_image.shape[0] > 0 and cropped_image.shape[1] > 0:

                        # 检查裁剪后的图像是否为全黑图像
                        if is_black_image(cropped_image):
                            continue  # 如果是全黑图像，则跳过当前裁剪位置，不进行推理操作
                        # 图像预处理
                        img, img_info = preProcess(cropped_image, 640, 640)
                        # 进行推理操作
                        result, dt = model_ulr_qk([img, img_info])

                        # 还原推理结果到原始图像的正确位置
                        defect_qk_list = afterProcessforQK(result, json_dict, instance_ulr_class, instance_d_class,
                                                           input_img,
                                                           net2source_Xsize, net2source_Ysize, queue3d, i, j, 640)
                        defect_body_list.extend(defect_qk_list)

    else:
        if model_d is not None:
            # 2048*2730
            result, dt = model_d([img, img_info])  # net out, infer time
            # 还原坐标
            net2source_Xsize = 1
            net2source_Ysize = 1
    if result is None:
        return
    # 推理结果后处理 构造数据库存储格式
    defect_body_list_normal = afterProcess(result, json_dict, instance_ulr_class, instance_d_class, input_img,
                                           net2source_Xsize, net2source_Ysize,
                                           queue3d)
    defect_body_list.extend(defect_body_list_normal)
    predict_queue.put(
        (json_dict['flow_id'], json_dict['main_id'], json_dict['camera_id'], signal_str, defect_body_list,
         input_img))


# 推理深度相机模态 上左右
class InferProcess(multiprocessing.Process):
    def __init__(self, device_id, model_ulr_path, model_ulr_qk, json_queue, res_queue, predict_queue,
                 down_json_queue, queue3d, upsample,
                 alive, daemon=True):
        multiprocessing.Process.__init__(self, daemon=daemon)
        self.device_id = device_id
        self.model_ulr_path = model_ulr_path
        self.model_ulr_qk_path = model_ulr_qk
        self.down_json_queue = down_json_queue
        self.json_queue = json_queue
        # 依次是 15点火坑 16划痕 11熔渣 0漏清 6气孔 17凹槽 4擦伤 3起棱 18误检
        self.instance_ulr_class = [15, 16, 11, 0, 6, 17, 4, 3, 18]

        self.res_queue = res_queue
        self.queue3d = queue3d
        self.predict_queue = predict_queue
        self.upsample = upsample
        self.alive = alive

    def run(self):
        self.model_ulr_path = Net(device_id=(self.device_id), model_path=self.model_ulr_path)

        logger.info('model_ulr_path on device {} start running'.format(self.device_id))
        while self.alive.value == True:
            json_str = self.json_queue.get()
            #print('jsonstr',json_str)
            try:
                #接收数据存在转移问题 增加一下语句
                json_str = json_str.replace('\\', '\\\\')
                json_dict = json.loads(json_str)

            except Exception as e:
                logger.error("接收" + str(e))
                # write_log(e)
                continue

            #print("jsondict",json_dict)
            signal = json_dict['signal']
            if signal == 1:
                threading_predict_origin(None, None, None, None, None, None, json_dict, self.predict_queue,
                                         self.res_queue, self.queue3d, self.upsample, json_dict['signal'])

            else:
                # 往下表推理中发
                if json_dict["surface_id"] == 3:
                    self.down_json_queue.put(json_dict)
                    continue
                logger.info("{}: model_d get_http_info :{},flowid{},cameraid{},surfaceid{}".format(datetime.datetime.now(), json_dict['image_url'],
                                                              json_dict['flow_id'],json_dict['camera_id'],json_dict['surface_id']))
                img_path = json_dict['image_url']
                img_path = img_path.replace('\\', '/').replace('D:/img', '/home/hongtai/yolo/depth_img')
                img_path_temp = json_dict['image_url']
                print("img_path_temp",img_path_temp)
                img_path_temp = json_dict['image_url'].replace('\\', '/').replace('D:','//Grab1/192.168.100.1')
                json_dict['image_url'] = img_path_temp
                # print("img_path_temp_change",img_path_temp)
                # json_dict['image_url'] = json_dict['image_url'].replace('\\\\', '/').replace('D:',
                #                                                                            '//Grab1/192.168.100.1')

                threading_predict_origin(self.model_ulr_path, None, None, img_path, self.instance_ulr_class, None,
                                         json_dict, self.predict_queue, self.res_queue, self.queue3d, self.upsample,
                                         json_dict['signal'])

# 推理深度相机模态 上左右 for qk 1026 hcf
class InferProcess_ulr_qk(multiprocessing.Process):
    def __init__(self, device_id, model_ulr_path, model_ulr_qk, json_queue, res_queue, predict_queue,
                 down_json_queue, queue3d, upsample,
                 alive, daemon=True):
        multiprocessing.Process.__init__(self, daemon=daemon)
        self.device_id = device_id
        self.model_ulr_path = model_ulr_path
        self.model_ulr_qk_path = model_ulr_qk
        self.down_json_queue = down_json_queue
        self.json_queue = json_queue
        # 依次是 15点火坑 16划痕 11熔渣 0漏清 6气孔 17凹槽 4擦伤 3起棱 18误检
        self.instance_ulr_class = [15, 16, 11, 0, 6, 17, 4, 3, 18]

        self.res_queue = res_queue
        self.queue3d = queue3d
        self.predict_queue = predict_queue
        self.upsample = upsample
        self.alive = alive

    def run(self):
        # 新增气孔模型 hcf
        self.model_ulr_qk = Net(device_id=(self.device_id), model_path=self.model_ulr_qk_path)

        logger.info('model_ulr_qk on device {} start running'.format(self.device_id))
        while self.alive.value == True:

            json_str = self.json_queue.get()
            #print('jsonstr',json_str)

            try:
                # 接收数据存在转移问题 增加一下语句
                json_str = json_str.replace('\\', '\\\\')
                json_dict = json.loads(json_str)

            except Exception as e:
                logger.error("接收" + str(e))
                # write_log(e)
                continue
            #print("jsondict",json_dict)
            signal = json_dict['signal']
            if signal == 1:
                threading_predict_origin(None, None, None, None, None, None, json_dict, self.predict_queue,
                                         self.res_queue, self.queue3d, self.upsample, json_dict['signal'])

            else:
                # 往下表推理中发
                if json_dict["surface_id"] == 3:
                    self.down_json_queue.put(json_dict)
                    continue
                # logger.info(
                #     "{}: ulr_qk_model get_http_info :{},{}".format(datetime.datetime.now(), json_dict['image_url'],
                #                                                    json_dict['flow_id']))
                logger.info("{}: ulr_qk_model get_http_info :{},flowid{},cameraid{},surfaceid{}".format(datetime.datetime.now(), json_dict['image_url'],
                                                              json_dict['flow_id'],json_dict['camera_id'],json_dict['surface_id']))
  
                img_path = json_dict['image_url']
                img_path = img_path.replace('\\', '/').replace('D:/img', '/home/hongtai/yolo/depth_img')
                img_path_temp = json_dict['image_url']
                print("img_path_temp",img_path_temp)
                img_path_temp = json_dict['image_url'].replace('\\', '/').replace('D:','//Grab1/192.168.100.1')
                json_dict['image_url'] = img_path_temp
                
                threading_predict_origin(None, self.model_ulr_qk, None, img_path, self.instance_ulr_class, None,
                                         json_dict, self.predict_queue, self.res_queue, self.queue3d, self.upsample,
                                         json_dict['signal'])


# 推理深度相机模态 下
class InferProcess2(multiprocessing.Process):
    def __init__(self, device_id, model_d_path, down_json_queue, res_queue, predict_queue, queue3d, upsample,
                 alive, daemon=True):
        multiprocessing.Process.__init__(self, daemon=daemon)
        self.device_id = device_id
        self.model_d_path = model_d_path
        self.down_json_queue = down_json_queue
        self.instance_d_class = [15, 16, 11, 0, 6, 17, 4, 3]
        #self.instance_d_class = [15, 0, 11]
        self.res_queue = res_queue
        self.queue3d = queue3d
        self.predict_queue = predict_queue
        self.upsample = upsample
        self.alive = alive

    def run(self):
        self.model_d_path = Net(device_id=(self.device_id), model_path=self.model_d_path)
        logger.info('model_d_path on device {} start running'.format(self.device_id))
        while self.alive.value == True:
            json_dict = self.down_json_queue.get()
            #print('json_dict',json_dict)
            logger.info("{}: model_d get_http_info :{},flowid{},cameraid{},surfaceid{}".format(datetime.datetime.now(), json_dict['image_url'],
                                                            json_dict['flow_id'],json_dict['camera_id'],json_dict['surface_id']))
 
            img_path = json_dict['image_url']
            img_path = img_path.replace('\\', '/').replace('D:', '/home/hongtai/yolo/1002d')
            img_path_temp = json_dict['image_url']
            print("img_path_temp",img_path_temp)
            img_path_temp = json_dict['image_url'].replace('\\', '/').replace('D:','//Grab2/192.168.100.2')
            json_dict['image_url'] = img_path_temp
            # json_dict['image_url'] = json_dict['image_url'].replace('\\\\', '/').replace('D:','//Grab2/192.168.100.2')

            threading_predict_origin(None, None, self.model_d_path, img_path, None, self.instance_d_class, json_dict,
                                     self.predict_queue, self.res_queue, self.queue3d, self.upsample,
                                     json_dict['signal'])


class HttpProcess(multiprocessing.Process):
    def __init__(self, host, port, json_queue, alive, daemon=True):
        multiprocessing.Process.__init__(self, daemon=daemon)
        self.host = host
        self.port = port
        self.json_queue = json_queue
        self.alive = alive

    def run(self):
        HTTPServer(self.host, self.port, self.json_queue, self.alive)



class EsProcess(multiprocessing.Process):

    def __init__(self, res_queue, index, alive, daemon=True):
        multiprocessing.Process.__init__(self, daemon=daemon)
        self.es = Elasticsearch('http://' + eshost + ':9201')
        self.res_queue = res_queue
        self.index = index
        self.alive = alive

    def run(self):
        logger.info('es index {} is running'.format(self.index))
        while self.alive.value == True:
            databody = self.res_queue.get()
            if databody:
                res = self.es.index(index="image_defect", body=databody)
                steel_defect_body = self.parse_steel_data(databody)
                res = self.es.index(index="steel_defect", body=steel_defect_body)
                # logger.info("插入缺陷数据库:"+str(res))
                # filename = os.path.basename( databody['image_url'])
                # logger.info("插入缺陷数据库:"+str(filename))

    def parse_steel_data(self, json_dict):
        databody = {
            "id": str(uuid.uuid4()),
            "main_id": json_dict['main_id'],
            "surface_id": json_dict['surface_id'],
            "type": json_dict['type'],
            "insert_time": datetime.datetime.now(),
            "confidence": json_dict['confidence'],
            "grade": '疑似',
            "is_visualize": True,
            "is_user_delete": False,
            "image_defect_ids_text": json_dict['id'],
            "panorama_id": '',
            "panorama_x": 0,
            "panorama_y": 0,
            "panorama_w": 0,
            "panorama_h": 0,
            "real_x": json_dict['real_x'],
            "real_y": json_dict['real_y'],
            "real_w": json_dict['real_w'],
            "real_h": json_dict['real_h'],
            "real_size": json_dict['real_w']*json_dict['real_h'],
            "real_depth": json_dict['deepth'],
            "is_repeat": False,
            "repeat_num": 0,
            "repeat_len": 0,
            "volume_url": '',
            "other0": '',
            "other1": ''
        }
        return databody


class Create3dProcess(multiprocessing.Process):
    def __init__(self, queue3d, index, alive, daemon=True):
        multiprocessing.Process.__init__(self, daemon=daemon)
        self.es = Elasticsearch('http://' + eshost + ':9201')
        self.queue3d = queue3d
        self.alive = alive
        self.index = index

    def run(self):
        logger.info('create3d index {} is running'.format(self.index))
        while self.alive.value == True:
            databody = self.queue3d.get()
            if databody:
                (img3d_defect_id, input_img, output_path, json_dict, x, y, w, h) = databody
                print('input_img',input_img)
                self.insert_3d_defects(img3d_defect_id, input_img, output_path, json_dict, x, y, w, h)

    def insert_3d_defects(self, img3d_defect_id, input_img, output_path, json_dict, x, y, w, h):
        left = int(x)
        right = int(x + w)
        top = int(y)
        bottom = int(h) + top
        print('3dimg_path',output_path)
        (filename, extension) = os.path.splitext(os.path.basename(output_path))
        dirpath = os.path.dirname(output_path)
        num = 0
        output_path = os.path.join(dirpath, filename + "_" + str(num) + extension)
        while os.path.exists(output_path):
            num += 1
            output_path = os.path.join(dirpath, filename + "_" + str(num) + extension)
        
        print("input_img",input_img)
        try:
            if w < 16 :
                left = int(x) - 8
                right = int(x) + 8
            if h < 16 :
                top = int(y) + 8
                bottom = int(h) -16 + top
            to3Dimg(left, right, top, bottom, input_img, output_path)
        except Exception as e:
            logger.info('3d缺陷生成失败：'+ str(e), output_path)
        h = 3116
        w = 3116
        if json_dict['surface_id'] != 3:
            img_url = output_path.replace('/home/hongtai/yolo/depth_img', '//Grab1/192.168.100.1/img')
        else:
            img_url = output_path.replace('/home/hongtai/yolo/1002d', '//Grab2/192.168.100.2')
        time_now = datetime.datetime.now()
        # try:
        #     img3d = cv2.imread(output_path)
        #     h, w = img3d.shape[:2]
        # except Exception as e:
        #     logger.info('3d缺陷插入失败：'+str(img_url))
        #     logger.info('3d缺陷位置信息是：'+str(left)+str(right)+str(top)+str(bottom))

        databody = {
            "id": img3d_defect_id,
            "main_id": json_dict["main_id"],
            "flow_id": int(json_dict["flow_id"]),
            "image_url": img_url,
            "type": 3,
            "surface_id": json_dict["surface_id"],
            "camera_id": json_dict['camera_id'],
            "insert_time": time_now,
            "width": w,
            "height": h,
            "status": 1,
            "other0": '',
            "other1": '',
            "steel_length": 0
        }
        res = self.es.index(index="image", body=databody)
        logger.info("插入3d数据库成功:" + str(img3d_defect_id))


# 深度相机坐标转换
class PosTransformProcess(multiprocessing.Process):
    def __init__(self, res_queue, predict_queue, alive, daemon=True):
        multiprocessing.Process.__init__(self, daemon=daemon)
        self.es = Elasticsearch('http://' + eshost + ':9201')
        self.res_queue = res_queue
        self.predict_queue = predict_queue
        self.alive = alive
        self.last_mainid = "0"
        self.defect_num = 0
        self.conn = pymysql.connect(
            host='192.168.100.100',  # 数据库地址
            user='root',  # 数据库用户名
            password='123456',  # 数据库密码r
            db='steeldetection',  # 数据库名称
            # charset = 'utf8 -- UTF-8 Unicode'
        )

        # 测试顺序
        self.flowids_up_left_camera = []
        self.flowids_up_right_camera = []
        self.flowids_left_camera = []
        self.flowids_right_camera = []
        self.flowids_down_left_camera = []
        self.flowids_down_center_camera = []
        self.flowids_down_right_camera = []
        # 图片路径
        self.imagepath_up_left_camera = []
        self.imagepath_up_right_camera = []
        self.imagepath_left_camera = []
        self.imagepath_right_camera = []
        self.imagepath_down_left_camera = []
        self.imagepath_down_center_camera = []
        self.imagepath_down_right_camera = []
        # 打火坑缺陷信息
        self.dhkdefect_up_left_camera = []
        self.dhkdefect_up_right_camera = []
        self.dhkdefect_down_left_camera = []
        self.dhkdefect_down_center_camera = []
        self.dhkdefect_down_right_camera = []
        self.dhkdefect_left_camera = []
        self.dhkdefect_right_camera = []
        # 漏清缺陷信息
        self.lqdefect_up_left_camera = []
        self.lqdefect_up_right_camera = []
        self.lqdefect_down_left_camera = []
        self.lqdefect_down_center_camera = []
        self.lqdefect_down_right_camera = []
        self.lqdefect_left_camera = []
        self.lqdefect_right_camera = []

        #1212新增起楞缺陷信息
        self.qldefect_up_left_camera = []
        self.qldefect_up_right_camera = []
        self.qldefect_down_left_camera = []
        self.qldefect_down_center_camera = []
        self.qldefect_down_right_camera = []
        self.qldefect_left_camera = []
        self.qldefect_right_camera = []
        #凹槽
        self.acdefect_up_left_camera = []
        self.acdefect_up_right_camera = []
        self.acdefect_down_left_camera = []
        self.acdefect_down_center_camera = []
        self.acdefect_down_right_camera = []
        self.acdefect_left_camera = []
        self.acdefect_right_camera = []
        #气孔
        self.qkdefect_up_left_camera = []
        self.qkdefect_up_right_camera = []
        self.qkdefect_down_left_camera = []
        self.qkdefect_down_center_camera = []
        self.qkdefect_down_right_camera = []
        self.qkdefect_left_camera = []
        self.qkdefect_right_camera = []


        # 右侧缺陷信息列表
        self.left_defect_list = []

        # 待坐标转换信息
        self.picdata_up_wait = []
        self.picdata_down_wait = []

        # 上表偏移量
        self.up_offset = [-1, -1]
        # 下表偏移量 左中 中右
        self.down_offset = [-1, -1, -1, -1]
        # 头部距离
        self.ul_up_dis = -1
        self.ur_up_dis = -1
        self.l_up_dis = -1
        self.r_up_dis = -1
        self.dl_up_dis = -1
        self.dc_up_dis = -1
        self.dr_up_dis = -1
        #数量统计
        self.numdict={
            'dhk':0,
            'hh':0,
            'rz':0,
            'lq':0,
            'qk':0,
            'ac':0,
            'cs':0,
            'ql':0,
        }        
        self.label_name_dict = {
            'dhk':'点火坑',
            'hh':'划痕',
            'rz':'熔渣',
            'lq':'漏清',
            'qk':'气孔',
            'ac':'凹槽',
            'cs':'擦伤',
            'ql':'起棱',
        }
        self.label_dict_reverse = {
            'dhk':'15',
            'hh':'16',
            'rz':'11',
            'lq':'0',
            'qk':'6',
            'ac':'17',
            'cs':'4',
            'ql':'3',
        }
    def run(self):
        while self.alive.value == True:
            pic_data = self.predict_queue.get()
            (flow_id, main_id, camera_id, signal_str, defect_body_list, imagepath) = pic_data
            # 防止接收不到finish 即接收一半就舍弃掉缺陷
            # if defect_body_list is not None:
            #     #缺陷数量统计
            #     self.defect_num = self.defect_num + len(defect_body_list)
            if main_id != self.last_mainid:
                self.init()
                logger.info("新旧批次号分别为：" + str(main_id) + "--" + str(self.last_mainid))
                # if self.last_mainid != "0":  # 右侧缺陷是上一批左侧的缺陷，刚开始运行不会有右侧缺陷
                #     self.adjustMainid(main_id)
                # self.last_mainid = main_id

            if signal_str == 1:  # 可能存在要结束信号来的太快还没推理完 还要等一个接收http
                logger.info(self.last_mainid + str("--批次结束推理"))
                # 检测批次顺序是否正常
                # self.get_batch_flowids()
                last_mainid, temp_length1, temp_width1, temp_thickness1 = self.get_batch_size()
                # 将不同表面缺陷分别插入至钢材缺陷数据库
                # self.insert_es_steel_defect_data(main_id)
                # 先获得长度信息 再进行打火坑的插入
                self.defect_num = 0
                total = 0
                conclusion = ""
                sendes_data, dhk_result = self.dhk_process()
                print(sendes_data)
                lq_result = self.lq_process()
                ql_result = self.ql_process()
                ac_result = self.ac_process()
                qk_result = self.qk_process()
                for type_,num in self.numdict.items():
                    total = total + num
                    conclusion += "-{}-:{}\n".format(self.label_dict_reverse[type_], num)
                conclusion += "-{}-:{}\n".format(1,0)
                conclusion += "-{}-:{}\n".format(5,0)
                conclusion += "-{}-:{}\n".format(7,0)
                conclusion += "-{}-:{}\n".format(13,0)
                print("numdict",self.numdict)
                print("conclusion",conclusion)
                print("total",total)
                self.numdict={
                        'dhk':0,
                        'hh':0,
                        'rz':0,
                        'lq':0,
                        'qk':0,
                        'ac':0,
                        'cs':0,
                        'ql':0,
                    }  
                #conclusion += "{}:{}\n".format("总共", total)
                self.writeMySql(last_mainid, temp_thickness1,dhk_result + lq_result +ql_result + ac_result + qk_result , total ,conclusion)
                self.send_es(sendes_data)
                self.init()
            if signal_str == 0:
                # 直接进行数据库写入 测试批次数据正常
                self.last_mainid = main_id
                # 把当前flowid写入列表
                continue_flag = self.add2list(pic_data)
                if not continue_flag:
                    continue
                # 上表右侧
                if camera_id == 3 and self.up_offset[0] == -1 and self.up_offset[1] == -1:
                    self.picdata_up_wait.append(pic_data)
                # 下表中测
                # elif camera_id==7 and self.down_offset[0]==-1 and self.down_offset[1]==-1:
                #     self.picdata_down_wait.append(pic_data)
                # 下表右侧
                elif (camera_id == 6 or camera_id == 5) and self.down_offset[2] == -1 and self.down_offset[3] == -1:
                    self.picdata_down_wait.append(pic_data)
                    continue
                else:
                    defect_body_list = self.adjustXY(pic_data)
                    # 获得没有dhk的缺陷信息
                    n_dhk_defect_body_list = self.extract_process(defect_body_list, camera_id)
                    self.send_es(n_dhk_defect_body_list)

                if self.ul_up_dis != -1 and self.ur_up_dis != -1 and self.up_offset[0] == -1 and self.up_offset[
                    1] == -1:
                    self.get_up_offset()
                    for item in self.picdata_up_wait:
                        defect_body_list = self.adjustXY(item)
                        n_dhk_defect_body_list = self.extract_process(defect_body_list, camera_id)
                        self.send_es(n_dhk_defect_body_list)
                    self.picdata_up_wait.clear()
                # 暂时用一个相机
                if  self.dl_up_dis!=-1 and self.dc_up_dis!=-1 and self.dr_up_dis!=-1 and self.down_offset[0]==-1 and self.down_offset[3]==-1:
                    self.get_down_offset()
                    for item in self.picdata_down_wait:
                        defect_body_list = self.adjustXY(item)
                        n_dhk_defect_body_list = self.extract_process(defect_body_list,camera_id)
                        self.send_es(n_dhk_defect_body_list)
                    self.picdata_down_wait.clear()

    def add2list(self, pic_data):  # 返回一个是否继续分析 比如遇到空图 后续不要分析
        (flow_id, main_id, camera_id, signal_str, defect_body_list, image_path) = pic_data
        # sorted_list = sorted(list(q.queue), key=lambda x: list(x.keys())[0])
        flow_id = int(flow_id)
        continue_flag = True
        # 上左
        if camera_id == 2:
            if self.ul_up_dis == -1:
                self.ul_up_dis = self.get_pic_dis(image_path)
                if self.ul_up_dis != -1:

                    left = self.ul_up_dis[2]
                    right = self.ul_up_dis[3]
                    self.ul_up_dis = self.ul_up_dis[0]
                    if 3096 - left - right < 300:  # 噪声图像依旧非头
                        print('认为为空路径：', image_path, flow_id)
                        self.ul_up_dis = -1
                        continue_flag = False
                    else:
                        self.flowids_up_left_camera.append(flow_id)
                        self.imagepath_up_left_camera.append(image_path)
                else:

                    continue_flag = False
            else:
                self.flowids_up_left_camera.append(flow_id)
                self.imagepath_up_left_camera.append(image_path)
        # 上右
        elif camera_id == 3:
            if self.ur_up_dis == -1:
                self.ur_up_dis = self.get_pic_dis(image_path)
                if self.ur_up_dis != -1:

                    left = self.ur_up_dis[2]
                    right = self.ur_up_dis[3]
                    self.ur_up_dis = self.ur_up_dis[0]
                    if 3096 - left - right < 300:  # 噪声图像依旧非头
                        self.ur_up_dis = -1
                        continue_flag = False
                    else:
                        self.flowids_up_right_camera.append(flow_id)
                        self.imagepath_up_right_camera.append(image_path)
                else:
                    continue_flag = False
            else:
                self.flowids_up_right_camera.append(flow_id)
                self.imagepath_up_right_camera.append(image_path)
        # 左
        elif camera_id == 1:
            if self.l_up_dis == -1:
                self.l_up_dis = self.get_pic_dis(image_path)
                if self.l_up_dis != -1:

                    left = self.l_up_dis[2]
                    right = self.l_up_dis[3]
                    self.l_up_dis = self.l_up_dis[0]
                    if 3096 - left - right < 300:  # 噪声图像依旧非头
                        self.l_up_dis = -1
                        continue_flag = False
                    else:
                        self.flowids_left_camera.append(flow_id)
                        self.imagepath_left_camera.append(image_path)
                else:
                    continue_flag = False

            else:
                self.flowids_left_camera.append(flow_id)
                self.imagepath_left_camera.append(image_path)
        # 右
        elif camera_id == 4:
            if self.r_up_dis == -1:
                self.r_up_dis = self.get_pic_dis(image_path)
                if self.r_up_dis != -1:

                    left = self.r_up_dis[2]
                    right = self.r_up_dis[3]
                    self.r_up_dis = self.r_up_dis[0]
                    if 3096 - left - right < 300:  # 噪声图像依旧非头
                        self.r_up_dis = -1
                        continue_flag = False
                    else:
                        self.flowids_right_camera.append(flow_id)
                        self.imagepath_right_camera.append(image_path)
                else:
                    continue_flag = False
            else:
                self.flowids_right_camera.append(flow_id)
                self.imagepath_right_camera.append(image_path)
        # 下左
        elif camera_id == 5:
            if self.dl_up_dis == -1:
                self.dl_up_dis = self.get_pic_dis(image_path)
                if self.dl_up_dis != -1:

                    left = self.dl_up_dis[2]
                    right = self.dl_up_dis[3]
                    self.dl_up_dis = self.dl_up_dis[0]
                    if 2048 - left - right < 200:  # 噪声图像依旧非头
                        self.dl_up_dis = -1
                        continue_flag = False
                    else:
                        self.flowids_down_left_camera.append(flow_id)
                        self.imagepath_down_left_camera.append(image_path)
                else:
                    continue_flag = False

            else:
                self.flowids_down_left_camera.append(flow_id)
                self.imagepath_down_left_camera.append(image_path)
        # 下中
        elif camera_id == 7:
            if self.dc_up_dis == -1:
                self.dc_up_dis = self.get_pic_dis(image_path)
                if self.dc_up_dis != -1:

                    left = self.dc_up_dis[2]
                    right = self.dc_up_dis[3]
                    self.dc_up_dis = self.dc_up_dis[0]
                    if 2048 - left - right < 200:  # 噪声图像依旧非头
                        self.dc_up_dis = -1
                        continue_flag = False
                    else:
                        self.flowids_down_center_camera.append(flow_id)
                        self.imagepath_down_center_camera.append(image_path)
                else:
                    continue_flag = False

            else:
                self.flowids_down_center_camera.append(flow_id)
                self.imagepath_down_center_camera.append(image_path)
        # 下右
        elif camera_id == 6:
            if self.dr_up_dis == -1:
                self.dr_up_dis = self.get_pic_dis(image_path)
                if self.dr_up_dis != -1:

                    left = self.dr_up_dis[2]
                    right = self.dr_up_dis[3]
                    self.dr_up_dis = self.dr_up_dis[0]
                    if 2048 - left - right < 200:  # 噪声图像依旧非头
                        self.dr_up_dis = -1
                        continue_flag = False
                    else:
                        self.flowids_down_right_camera.append(flow_id)
                        self.imagepath_down_right_camera.append(image_path)
                else:
                    continue_flag = False

            else:
                self.flowids_down_right_camera.append(flow_id)
                self.imagepath_down_right_camera.append(image_path)
        return continue_flag

    def send_es(self, defect_body_list):
        for i in range(len(defect_body_list)):
            # if defect_body_list[i]['camera_id'] == 4:
            #     temp = copy.deepcopy(defect_body_list[i])
            #     temp['camera_id'] = 1
            #     temp['defect_id'] = str(uuid.uuid4())
            #     # print('templeft:',temp['surface_id'])
            #     temp['surface_id'] = 3
            #     self.left_defect_list.append(temp)
            self.res_queue.put(defect_body_list[i])

    def search_defects(self, select_id, new_id, main_id):
        body = {
            'query': {
                'term': {
                    'id': select_id
                }
            },

            'size': 1000  # 指定当前页数据量
        }
        res = self.es.search(index="image", body=body)  # 翻页取消使用filter
        hits = res['hits']['hits']
        # 创建一个列表，用于存储文档的源数据
        results = []

        # 遍历每个命中的文档
        for hit in hits:
            source = hit['_source']
            results.append(source)
        if len(results) > 0:
            # return results[0]
            databody = results[0]

            databody['id'] = new_id
            databody['main_id'] = main_id
            databody['camera_id'] = 1
            databody['surface_id'] = 1
            res = self.es.index(index="image", body=databody)
            return True
        else:
            return False

    # 东西侧数据调整
    def adjustMainid(self, mainid):
        for i in range(len(self.left_defect_list)):
            if self.left_defect_list[i]['camera_id'] == 1:
                self.left_defect_list[i]['main_id'] = mainid
                # print('调整：',self.ri)
                # 待修改
                new_image_id = str(uuid.uuid4())
                new_image3d_id = str(uuid.uuid4())
                new_grayimg_id = str(uuid.uuid4())

                if not self.search_defects(self.left_defect_list[i]['image_id'], new_image_id, mainid):
                    logger.info("修改image_id失败" + str(mainid) + '  ' + str(self.left_defect_list[i]['image_id']))
                if not self.search_defects(self.left_defect_list[i]['image3_id'], new_image3d_id, mainid):
                    logger.info("修改image3d_id失败" + str(mainid) + '  ' + str(self.left_defect_list[i]['image3_id']))
                if not self.search_defects(self.left_defect_list[i]['image2_id'], new_grayimg_id, mainid):
                    logger.info("修改grayimg_id失败" + str(mainid) + '  ' + str(self.left_defect_list[i]['image2_id']))
                self.left_defect_list[i]['image_id'] = new_image_id
                self.left_defect_list[i]['image2_id'] = new_grayimg_id
                self.left_defect_list[i]['image3_id'] = new_image3d_id

        n_dhk_defect_body_list = self.extract_process(self.left_defect_list, 1)
        self.send_es(n_dhk_defect_body_list)
        self.left_defect_list = []
        # self.res_queue.put(defect_body_list[i])

    # 得到钢材的实际长宽厚
    def get_batch_size(self):
        # 经验值
        length = 8497
        width = 1591
        thickness = 224
        tempLength_ul = -1
        tempwidth_u = -1
        tempthickness_lr = -1
        try:
            # logger.info("上左："+str(len(self.imagepath_up_left_camera))+"上右"+str(len(self.imagepath_up_right_camera)))
            # logger.info("左："+str(len(self.imagepath_left_camera))+"右"+str(len(self.imagepath_right_camera)))
            # 计算长度 使用上表左侧计算
            if len(self.imagepath_up_left_camera) > 0:
                # 至少含头含尾
                for i in range(len(self.imagepath_up_left_camera) - 1, -1, -1):
                    path = self.imagepath_up_left_camera[i]
                    flag = self.get_pic_dis(path)
                    if (flag == -1):
                        continue
                    else:
                        down_dis = flag[1]
                        tempLength_ul = ((i + 1) * 4096 - self.ul_up_dis - down_dis) * 0.185
                        # print("down_dis",down_dis,"i",i,"up_dis:",self.ul_up_dis)
                        break
                # 在上左的基础上计算宽度
                if len(self.imagepath_up_right_camera) > 0:
                    left_dis = flag[2]
                    _, _, _, right_dis = self.get_img_dixtance(
                        self.imagepath_up_right_camera[0])
                    tempwidth_u = (self.up_offset[0] + 3072 - left_dis - right_dis) * 0.425
            # 计算厚度
            if (len(self.imagepath_left_camera) > 0):
                _, _, leftdis, rightdis = self.get_img_dixtance(
                    self.imagepath_left_camera[0])
                tempthickness_lr = (3072 - leftdis - rightdis) * 0.425
            elif (len(self.imagepath_right_camera) > 0):
                _, _, leftdis, rightdis = self.get_img_dixtance(
                    self.imagepath_right_camera[0])
                tempthickness_lr = (3072 - leftdis - rightdis) * 0.425
            if tempLength_ul != -1:
                length = tempLength_ul
            if tempwidth_u != -1:
                width = tempwidth_u
            if tempthickness_lr != -1:
                thickness = tempthickness_lr

            return self.last_mainid, round(length, 2), round(width, 2), round(thickness, 2)
        except Exception as e:
            logger.error("总长error:" + str(e))
            logger.info("获取钢材实际长度、宽度、厚度失败" + str(self.last_mainid))

        return self.last_mainid, round(length, 2), round(width, 2), round(thickness, 2)

        # self.writeBatchGrageAndSize(self.last_mainid,(temp_length1),(temp_width1),(temp_thickness1))

    def writeMySql(self, main_id, thickness, dhk_result , defect_num , conlusion):
        score = random.randint(-50, 100)
        grade = "优秀"
        if (score <= 0):
            grade = "较差"
        elif score < 60:
            grade = "良好"
        else:
            grade = "优秀"
        try:
            with self.conn.cursor() as cursor:
                # 准备SQL语句
                sql = 'update batch set defect_num = "{}" ,real_height = "{}", score = "{}",grade = "{}",details = "{}",conclusion = "{}" where main_id ' \
                      '= "{}" ;'.format(
                    defect_num, thickness, score, grade, dhk_result,conlusion, main_id)
                # 执行SQL语句
                self.conn.ping(reconnect=True)
                cursor.execute(sql)
                # 执行完要提交
                self.conn.commit()
                logger.info("写入mysql数据库成功:" + str(main_id))

        except Exception as e:
            # 如果执行失败要回滚
            self.conn.rollback()
            logger.info("写入mysql数据库失败:" + str(main_id))
            print(e)
            print( thickness, score, grade, dhk_result, main_id)

        self.conn.close()

    def get_up_offset(self):

        if self.ul_up_dis != -1 and self.ur_up_dis != -1:
            left_second_up, left_second_down, left_second_left, left_second_right = self.get_img_dixtance(
                self.imagepath_up_left_camera[0])

            right_second_up, right_second_down, right_second_left, right_second_right = self.get_img_dixtance(
                self.imagepath_up_right_camera[0])

            delta_y = self.ul_up_dis - self.ur_up_dis
            # 101 重叠像素
            delta_x = max(0, (3072 - 101 - left_second_right - right_second_left))
            self.up_offset = [delta_x, delta_y]

    def get_down_offset(self):

        if self.dl_up_dis != -1 and self.dr_up_dis != -1 and self.dc_up_dis != -1:
            _, _, _, l_r_dis = self.get_img_dixtance(self.imagepath_down_left_camera[0])

            _, _, c_l_dis, c_r_dis = self.get_img_dixtance(self.imagepath_down_center_camera[0])
            _, _, r_l_dis, _ = self.get_img_dixtance(self.imagepath_down_right_camera[0])
            delta_y_lc = self.dl_up_dis - self.dc_up_dis
            delta_y_cr = self.dc_up_dis - self.dr_up_dis + delta_y_lc
            # 51 左中重叠像素 50 中右重叠像素
            delta_x_lc = max(0, (2048 - 51 - l_r_dis - c_l_dis))
            delta_x_cr = max(0, (2048 - 50 - c_r_dis - r_l_dis + delta_x_lc))
            self.down_offset = [delta_x_lc, delta_y_lc, delta_x_cr, delta_y_cr]

    def get_batch_flowids(self):
        print('上表左侧：', self.flowids_up_left_camera)
        print('上表右侧：', self.flowids_up_right_camera)
        print('下表左侧：', self.flowids_down_left_camera)
        print('下表中侧：', self.flowids_down_center_camera)
        print('下表右侧：', self.flowids_down_right_camera)
        print('左表：', self.flowids_left_camera)
        print('右表：', self.flowids_right_camera)

    # 对单张图片进行现实中坐标转换
    def adjustXY(self, pic_data):
        # 假如固定偏移量 第2张相对于第一张左图向右1900 向下0
        # up_offset = [1900, 0]

        # 修正当前图片的缺陷表
        (flow_id, main_id, camera_id, signal_str, defect_body_list, imagepath) = pic_data
        flow_id = int(flow_id)
        for i in range(len(defect_body_list)):
            x = defect_body_list[i]['x']
            y = defect_body_list[i]['y']
            current_flowid = 0
            first_flowid = 0

            # 对于第一张图，仅修正real_x,real_y为x,y
            # 上左
            if camera_id == 2:
                if len(self.flowids_up_left_camera) != 0:
                    current_flowid = flow_id
                    first_flowid = self.flowids_up_left_camera[0]
                    y -= self.ul_up_dis

            # 上右
            elif camera_id == 3:
                if len(self.flowids_up_right_camera) != 0:
                    current_flowid = flow_id
                    first_flowid = self.flowids_up_right_camera[0]
                    x += self.up_offset[0]
                    y += self.up_offset[1]
                    y -= self.ur_up_dis
            # 左
            elif camera_id == 1:
                if len(self.flowids_left_camera) != 0:
                    current_flowid = flow_id
                    first_flowid = self.flowids_left_camera[0]
                    y -= self.l_up_dis
            # 右
            elif camera_id == 4:
                if len(self.flowids_right_camera) != 0:
                    current_flowid = flow_id
                    first_flowid = self.flowids_right_camera[0]
                    y -= self.r_up_dis
            # 下左
            elif camera_id == 5:
                if len(self.flowids_down_left_camera) != 0:
                    current_flowid = flow_id
                    first_flowid = self.flowids_down_left_camera[0]
                    y -= self.dl_up_dis
            # 下中
            elif camera_id == 7:
                if len(self.flowids_down_center_camera) != 0:
                    current_flowid = flow_id
                    first_flowid = self.flowids_down_center_camera[0]
                    #暂时先用一个相机
                    x += self.down_offset[0]
                    y += self.down_offset[1]
                    y -= self.dc_up_dis
            # 下右
            elif camera_id == 6:
                if len(self.flowids_down_right_camera) != 0:
                    current_flowid = flow_id
                    first_flowid = self.flowids_down_right_camera[0]
                    x += self.down_offset[2]
                    y += self.down_offset[3]
                    y -= self.dr_up_dis
            offsetX = -0
            if camera_id == 5 or camera_id == 6 or camera_id == 7:
                offsetY = (current_flowid - first_flowid) * 2730 - 0
            else:
                offsetY = (current_flowid - first_flowid) * 4096 - 0 
            defect_body_list[i]['real_x'] = int((x + offsetX) * 0.425)
            defect_body_list[i]['real_y'] = int((y + offsetY) * 0.185)
            if (x + offsetX) * 0.185 < 0 :
                defect_body_list[i]['real_x'] = int(50)
            if (y + offsetY) * 0.185 < 0 :
                defect_body_list[i]['real_y'] = int(50)

        return defect_body_list
        
    # 依次是 15点火坑 16划痕 11熔渣 0漏清 6气孔 17凹槽 4擦伤 3起棱
    # 单张图的打火坑缺陷提取
    def extract_process(self, defect_body_list, camera_id):
        temp_defect_body_list = []
        for i in range(len(defect_body_list)):
            # dhk缺陷
            if defect_body_list[i]['type'] == 15:
                x = defect_body_list[i]['x']
                y = defect_body_list[i]['y']
                w = defect_body_list[i]['w']
                h = defect_body_list[i]['h']
                # 过滤缺陷
                if h > w or y > 7000 or w < 700:
                    continue
                # 上左
                if camera_id == 2:
                    if w * h < 100 * 453:
                        continue
                    self.dhkdefect_up_left_camera.append(defect_body_list[i])
                # 上右
                elif camera_id == 3:
                    if w * h < 100 * 453:
                        continue
                    self.dhkdefect_up_right_camera.append(defect_body_list[i])
                # 左
                elif camera_id == 1:
                    self.dhkdefect_left_camera.append(defect_body_list[i])
                # 右
                elif camera_id == 4:
                    self.dhkdefect_right_camera.append(defect_body_list[i])
                # 下左
                elif camera_id == 5:
                    self.dhkdefect_down_left_camera.append(defect_body_list[i])
                # 下中
                elif camera_id == 7:
                    self.dhkdefect_down_center_camera.append(defect_body_list[i])
                # 下右
                elif camera_id == 6:
                    self.dhkdefect_down_right_camera.append(defect_body_list[i])
            elif defect_body_list[i]['type'] == 0:
                temp_defect_body_list.append(defect_body_list[i])
                x = defect_body_list[i]['x']
                y = defect_body_list[i]['y']
                w = defect_body_list[i]['w']
                h = defect_body_list[i]['h']
                self.numdict['lq']+=1
                # 上左
                if camera_id == 2:

                    self.lqdefect_up_left_camera.append(defect_body_list[i])
                # 上右
                elif camera_id == 3:

                    self.lqdefect_up_right_camera.append(defect_body_list[i])
                # 左
                elif camera_id == 1:
                    self.lqdefect_left_camera.append(defect_body_list[i])
                # 右
                elif camera_id == 4:
                    self.lqdefect_right_camera.append(defect_body_list[i])
                # 下左
                elif camera_id == 5:
                    self.lqdefect_down_left_camera.append(defect_body_list[i])
                # 下中
                elif camera_id == 7:
                    self.lqdefect_down_center_camera.append(defect_body_list[i])
                # 下右
                elif camera_id == 6:
                    self.lqdefect_down_right_camera.append(defect_body_list[i])

                temp_defect_body_list.append(defect_body_list[i])
            elif defect_body_list[i]['type'] == 3:
                temp_defect_body_list.append(defect_body_list[i])
                x = defect_body_list[i]['x']
                y = defect_body_list[i]['y']
                w = defect_body_list[i]['w']
                h = defect_body_list[i]['h']
                self.numdict['ql']+=1

                # 上左
                if camera_id == 2:

                    self.qldefect_up_left_camera.append(defect_body_list[i])
                # 上右
                elif camera_id == 3:

                    self.qldefect_up_right_camera.append(defect_body_list[i])
                # 左
                elif camera_id == 1:
                    self.qldefect_left_camera.append(defect_body_list[i])
                # 右
                elif camera_id == 4:
                    self.qldefect_right_camera.append(defect_body_list[i])
                # 下左
                elif camera_id == 5:
                    self.qldefect_down_left_camera.append(defect_body_list[i])
                # 下中
                elif camera_id == 7:
                    self.qldefect_down_center_camera.append(defect_body_list[i])
                # 下右
                elif camera_id == 6:
                    self.qldefect_down_right_camera.append(defect_body_list[i])
            elif defect_body_list[i]['type'] == 17:
                temp_defect_body_list.append(defect_body_list[i])
                x = defect_body_list[i]['x']
                y = defect_body_list[i]['y']
                w = defect_body_list[i]['w']
                h = defect_body_list[i]['h']
                self.numdict['ac']+=1

                # 上左
                if camera_id == 2:

                    self.acdefect_up_left_camera.append(defect_body_list[i])
                # 上右
                elif camera_id == 3:

                    self.acdefect_up_right_camera.append(defect_body_list[i])
                # 左
                elif camera_id == 1:
                    self.acdefect_left_camera.append(defect_body_list[i])
                # 右
                elif camera_id == 4:
                    self.acdefect_right_camera.append(defect_body_list[i])
                # 下左
                elif camera_id == 5:
                    self.acdefect_down_left_camera.append(defect_body_list[i])
                # 下中
                elif camera_id == 7:
                    self.acdefect_down_center_camera.append(defect_body_list[i])
                # 下右
                elif camera_id == 6:
                    self.acdefect_down_right_camera.append(defect_body_list[i])
            elif defect_body_list[i]['type'] == 6:
                temp_defect_body_list.append(defect_body_list[i])
                x = defect_body_list[i]['x']
                y = defect_body_list[i]['y']
                w = defect_body_list[i]['w']
                h = defect_body_list[i]['h']
                self.numdict['qk']+=1

                # 上左
                if camera_id == 2:

                    self.qkdefect_up_left_camera.append(defect_body_list[i])
                # 上右
                elif camera_id == 3:

                    self.qkdefect_up_right_camera.append(defect_body_list[i])
                # 左
                elif camera_id == 1:
                    self.qkdefect_left_camera.append(defect_body_list[i])
                # 右
                elif camera_id == 4:
                    self.qkdefect_right_camera.append(defect_body_list[i])
                # 下左
                elif camera_id == 5:
                    self.qkdefect_down_left_camera.append(defect_body_list[i])
                # 下中
                elif camera_id == 7:
                    self.qkdefect_down_center_camera.append(defect_body_list[i])
                # 下右
                elif camera_id == 6:
                    self.qkdefect_down_right_camera.append(defect_body_list[i])
            elif defect_body_list[i]['type'] == 16:
                temp_defect_body_list.append(defect_body_list[i])
                self.numdict['hh']+=1
            elif defect_body_list[i]['type'] == 11:
                temp_defect_body_list.append(defect_body_list[i])
                self.numdict['rz']+=1
            elif defect_body_list[i]['type'] == 4:
                temp_defect_body_list.append(defect_body_list[i])
                self.numdict['cs']+=1
            else:
                temp_defect_body_list.append(defect_body_list[i])

        return temp_defect_body_list

    def depth_judge(self, ori_img_path, depth_base, depth_threshold, x, y, w, h):
        img = cv2.imread(ori_img_path, cv2.IMREAD_GRAYSCALE)
        arr = np.array(img, dtype=float)
        roi = arr[y:y + h, x:x + w]
        roi[roi < 10] = np.nan  # 去除无效的干扰像素点
        zmean = np.nanmean(roi)
        depth = abs(depth_base - zmean) / 2.5
        if depth > depth_threshold:
            return depth, False
        else:
            return depth, True

    def depth_judge_ql(self, ori_img_path, depth_base, depth_threshold1,depth_threshold2, x, y, w, h):
        img = cv2.imread(ori_img_path, cv2.IMREAD_GRAYSCALE)
        arr = np.array(img, dtype=float)
        roi = arr[y:y + h, x:x + w]
        roi[roi < 10] = np.nan  # 去除无效的干扰像素点
        zmean = np.nanmean(roi)
        depth = abs(depth_base - zmean) / 2.5
        if depth < depth_threshold1:
            return depth, 1
        elif ((depth>depth_threshold1)  and (depth< depth_threshold2)):
            return depth, 2
        else:
            return depth, 3
    def depth_judge_ac(self, ori_img_path, depth_base, depth_threshold1,depth_threshold2, x, y, w, h):
        img = cv2.imread(ori_img_path, cv2.IMREAD_GRAYSCALE)
        arr = np.array(img, dtype=float)
        roi = arr[y:y + h, x:x + w]
        roi[roi < 10] = np.nan  # 去除无效的干扰像素点
        zmean = np.nanmean(roi)
        depth = abs(depth_base - zmean) / 2.5
        if depth < depth_threshold1:
            return depth, 1
        elif ((depth>depth_threshold1)  and (depth< depth_threshold2)):
            return depth, 2
        else:
            return depth, 3


    def dhk_process(self):
        # 一个面只有1个
        #         (1)点火坑分析:
        # 东侧检出，距离头部》60mm((不)达标)，深度<20mm((不)达标)；
        # 上侧未检出；
        # 下侧未检出；
        # 西侧未检出；
        dhk_result = "点火坑分析:\n"
        depth_threshold = 25
        dis_threshold = 60
        sendes_data = []
        if len(self.dhkdefect_up_left_camera) > 0:
            defect_info = self.get_min_data_json(self.dhkdefect_up_left_camera)
            real_y = defect_info['real_y']
            self.numdict['dhk']+=1
            imgpath = defect_info['image_url'].replace("//Grab1/192.168.100.1/img", '/home/hongtai/yolo/depth_img')
            deepth, is_dabiao = self.depth_judge(imgpath, 120, depth_threshold, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
            defect_info['deepth'] = deepth
            sendes_data.append(defect_info)
            if real_y <= dis_threshold:
                tempdis = "上侧东检出,距离头部<" + str(dis_threshold) + "mm (达标)"
            else:
                tempdis = "上侧东检出,距离头部>" + str(dis_threshold) + "mm (不达标)"
            if is_dabiao:
                tempdepth = ",深度<" + str(depth_threshold) + "mm (达标)"
            else:
                tempdepth = ",深度>" + str(depth_threshold) + "mm (不达标)"
            result = tempdis + tempdepth + '\n'
            dhk_result += result
        else:
            dhk_result += "上侧东未检出;\n"
        if len(self.dhkdefect_up_right_camera) > 0:
            defect_info = self.get_min_data_json(self.dhkdefect_up_right_camera)
            real_y = defect_info['real_y']
            self.numdict['dhk']+=1            
            imgpath = defect_info['image_url'].replace("//Grab1/192.168.100.1/img", '/home/hongtai/yolo/depth_img')
            deepth, is_dabiao = self.depth_judge(imgpath, 120, depth_threshold, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
            defect_info['deepth'] = deepth
            sendes_data.append(defect_info)
            if real_y <= dis_threshold:
                tempdis = "上侧西检出,距离头部<" + str(dis_threshold) + "mm (达标)"
            else:
                tempdis = "上侧西检出,距离头部>" + str(dis_threshold) + "mm (不达标)"
            if is_dabiao:
                tempdepth = ",深度<" + str(depth_threshold) + "mm (达标)"
            else:
                tempdepth = ",深度>" + str(depth_threshold) + "mm (不达标)"
            result = tempdis + tempdepth + '\n'
            dhk_result += result
        else:
            dhk_result += "上侧西未检出;\n"
        if len(self.dhkdefect_down_left_camera) > 0:
            defect_info = self.get_min_data_json(self.dhkdefect_down_left_camera)
            real_y = defect_info['real_y']
            self.numdict['dhk']+=1
            imgpath = defect_info['image_url'].replace("//Grab2/192.168.100.2", '/home/hongtai/yolo/1002d')
            deepth, is_dabiao = self.depth_judge(imgpath, 120, depth_threshold, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
            defect_info['deepth'] = deepth
            sendes_data.append(defect_info)

            if real_y <= dis_threshold:
                tempdis = "下侧东检出,距离头部<" + str(dis_threshold) + "mm (达标)"
            else:
                tempdis = "下侧东检出,距离头部>" + str(dis_threshold) + "mm (不达标)"
            if is_dabiao:
                tempdepth = ",深度<" + str(depth_threshold) + "mm (达标)"
            else:
                tempdepth = ",深度>" + str(depth_threshold) + "mm (不达标)"
            result = tempdis + tempdepth + '\n'
            dhk_result += result
        else:
            dhk_result += "下侧东未检出;\n"

        if len(self.dhkdefect_down_center_camera) > 0:
            defect_info = self.get_min_data_json(self.dhkdefect_down_center_camera)
            self.numdict['dhk']+=1
            real_y = defect_info['real_y']
            imgpath = defect_info['image_url'].replace("//Grab2/192.168.100.2", '/home/hongtai/yolo/1002d')
            deepth, is_dabiao = self.depth_judge(imgpath, 120, depth_threshold, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
            defect_info['deepth'] = deepth
            sendes_data.append(defect_info)

            if real_y <= dis_threshold:
                tempdis = "下侧中检出,距离头部<" + str(dis_threshold) + "mm (达标)"
            else:
                tempdis = "下侧中检出,距离头部>" + str(dis_threshold) + "mm (不达标)"
            if is_dabiao:
                tempdepth = ",深度<" + str(depth_threshold) + "mm (达标)"
            else:
                tempdepth = ",深度>" + str(depth_threshold) + "mm (不达标)"
            result = tempdis + tempdepth + '\n'
            dhk_result += result
        else:
            dhk_result += "下侧中未检出;\n"
        if len(self.dhkdefect_down_right_camera) > 0:
            defect_info = self.get_min_data_json(self.dhkdefect_down_right_camera)
            self.numdict['dhk']+=1
            real_y = defect_info['real_y']
            imgpath = defect_info['image_url'].replace("//Grab2/192.168.100.2", '/home/hongtai/yolo/1002d')
            deepth, is_dabiao = self.depth_judge(imgpath, 120, depth_threshold, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
            defect_info['deepth'] = deepth
            sendes_data.append(defect_info)

            if real_y <= dis_threshold:
                tempdis = "下侧西检出,距离头部<" + str(dis_threshold) + "mm (达标)"
            else:
                tempdis = "下侧西检出,距离头部>" + str(dis_threshold) + "mm (不达标)"
            if is_dabiao:
                tempdepth = ",深度<" + str(depth_threshold) + "mm (达标)"
            else:
                tempdepth = ",深度>" + str(depth_threshold) + "mm (不达标)"
            result = tempdis + tempdepth + '\n'
            dhk_result += result
        else:
            dhk_result += "下侧西未检出;\n"
        if len(self.dhkdefect_left_camera) > 0:
            defect_info = self.get_min_data_json(self.dhkdefect_left_camera)
            self.numdict['dhk']+=1
            real_y = defect_info['real_y']
            imgpath = defect_info['image_url'].replace("//Grab1/192.168.100.1/img", '/home/hongtai/yolo/depth_img')
            deepth, is_dabiao = self.depth_judge(imgpath, 120, 20, defect_info['x'], defect_info['y'], defect_info['w'],
                                                 defect_info['h'])
            defect_info['deepth'] = deepth
            sendes_data.append(defect_info)
            if real_y <= dis_threshold:
                tempdis = "西侧检出,距离头部<" + str(dis_threshold) + "mm (达标)"
            else:
                tempdis = "西侧检出,距离头部>" + str(dis_threshold) + "mm (不达标)"
            if is_dabiao:
                tempdepth = ",深度<" + str(20) + "mm (达标)"
            else:
                tempdepth = ",深度>" + str(20) + "mm (不达标)"
            result = tempdis + tempdepth + '\n'
            dhk_result += result
        else:
            dhk_result += "西侧未检出;\n"
        if len(self.dhkdefect_right_camera) > 0:
            defect_info = self.get_min_data_json(self.dhkdefect_right_camera)
            self.numdict['dhk']+=1
            real_y = defect_info['real_y']
            imgpath = defect_info['image_url'].replace("//Grab1/192.168.100.1/img", '/home/hongtai/yolo/depth_img')
            deepth, is_dabiao = self.depth_judge(imgpath, 120, 20, defect_info['x'], defect_info['y'], defect_info['w'],
                                                 defect_info['h'])
            defect_info['deepth'] = deepth
            sendes_data.append(defect_info)
            if real_y <= dis_threshold:
                tempdis = "东侧检出,距离头部<" + str(dis_threshold) + "mm (达标)"
            else:
                tempdis = "东侧检出,距离头部>" + str(dis_threshold) + "mm (不达标)"
            if is_dabiao:
                tempdepth = ",深度<" + str(20) + "mm (达标)"
            else:
                tempdepth = ",深度>" + str(20) + "mm (不达标)"
            result = tempdis + tempdepth + '\n'
            dhk_result += result
        else:
            dhk_result += "东侧未检出;\n"
        # print(dhk_result)
        return sendes_data, dhk_result

    def get_min_data_json(self, json_list):
        min_data = float('inf')  # 初始化最小值为正无穷大
        min_data_json = None

        for json_obj in json_list:
            try:
                # json_obj = json.loads(json_str)
                # if 'y' in json_obj and isinstance(json_obj['y'], int):
                if json_obj['y'] < min_data:
                    min_data = json_obj['y']
                    min_data_json = json_obj
            except Exception as e:
                logger.error("zuixiao:" + str(e))
                logger.info("jsonlist" + str(json_list))

        return min_data_json

    def get_max_data_json(self, json_list):
        max_data = float('0')  # 初始化最大值为0
        max_data_json = None

        for json_obj in json_list:
            try:
                # json_obj = json.loads(json_str)
                # if 'y' in json_obj and isinstance(json_obj['y'], int):
                if json_obj['y'] > max_data:
                    max_data = json_obj['y']
                    max_data_json = json_obj
            except Exception as e:
                logger.error("zuida:" + str(e))
                logger.info("jsonlist" + str(json_list))

        return max_data_json


    def lq_process(self):
        # 一个面只有1个
        #         (1)漏清分析:
        # 东侧检出，漏清率40% 小于50%；
        # 上侧未检出，漏清率2% 小于5%；
        # 下侧未检出；
        # 西侧未检出；
        lq_result = "漏清分析:\n"
        up_S = 25092972  # 29493x1004上表左单张图的钢材像素
        kuan_threthild = 5
        zhai_threthild = 50
        left_S = 15937560
        down_S = 22273680  # 1416*15730
        sendes_data = []
        if len(self.lqdefect_up_left_camera) > 0:
            lq_S = 0
            for defect_info in self.lqdefect_up_left_camera:
                w = defect_info['w']
                h = defect_info['h']
                lq_S += w * h
            lq_ratio = round(lq_S / up_S * 100, 2)
            if lq_ratio > 5:
                temp = "上侧东漏清率" + str(lq_ratio) + "%,大于5%"
            else:
                temp = "上侧东漏清率" + str(lq_ratio) + "%,小于5%"
            result = temp + '\n'
            lq_result += result
        else:
            lq_result += "上侧东未检出漏清;\n"
        if len(self.lqdefect_up_right_camera) > 0:
            lq_S = 0
            for defect_info in self.lqdefect_up_right_camera:
                w = defect_info['w']
                h = defect_info['h']
                lq_S += w * h
            lq_ratio = round(lq_S / up_S * 100, 2)
            if lq_ratio > 5:
                temp = "上侧西漏清率" + str(lq_ratio) + "%,大于5%"
            else:
                temp = "上侧西漏清率" + str(lq_ratio) + "%,小于5%"
            result = temp + '\n'
            lq_result += result
        else:
            lq_result += "上侧西未检出漏清;\n"
        if len(self.lqdefect_down_left_camera) > 0:
            lq_S = 0
            for defect_info in self.lqdefect_down_left_camera:
                w = defect_info['w']
                h = defect_info['h']
                lq_S += w * h
            lq_ratio = round(lq_S / down_S * 100, 2)
            if lq_ratio > 5:
                temp = "下侧东漏清率" + str(lq_ratio) + "%,大于5%"
            else:
                temp = "下侧东漏清率" + str(lq_ratio) + "%,小于5%"
            result = temp + '\n'
            lq_result += result
        else:
            lq_result += "下侧东未检出漏清;\n"

        if len(self.lqdefect_down_center_camera) > 0:
            lq_S = 0
            for defect_info in self.lqdefect_down_center_camera:
                w = defect_info['w']
                h = defect_info['h']
                lq_S += w * h
            lq_ratio = round(lq_S / down_S * 100, 2)
            if lq_ratio > 5:
                temp = "下侧中漏清率" + str(lq_ratio) + "%,大于5%"
            else:
                temp = "下侧中漏清率" + str(lq_ratio) + "%,小于5%"
            result = temp + '\n'
            lq_result += result
        else:
            lq_result += "下侧中未检出漏清;\n"
        if len(self.lqdefect_down_right_camera) > 0:
            lq_S = 0
            for defect_info in self.lqdefect_down_right_camera:
                w = defect_info['w']
                h = defect_info['h']
                lq_S += w * h
            lq_ratio = round(lq_S / down_S * 100, 2)
            if lq_ratio > 5:
                temp = "下侧西漏清率" + str(lq_ratio) + "%,大于5%"
            else:
                temp = "下侧西漏清率" + str(lq_ratio) + "%,小于5%"
            result = temp + '\n'
            lq_result += result
        else:
            lq_result += "下侧西未检出漏清;\n"
        if len(self.lqdefect_left_camera) > 0:
            lq_S = 0
            for defect_info in self.lqdefect_left_camera:
                w = defect_info['w']
                h = defect_info['h']
                lq_S += w * h
            lq_ratio = round(lq_S / left_S * 100, 2)
            if lq_ratio > 50:
                temp = "东侧漏清率" + str(lq_ratio) + "%,大于50%"
            else:
                temp = "东侧漏清率" + str(lq_ratio) + "%,小于50%"
            result = temp + '\n'
            lq_result += result
        else:
            lq_result += "东侧未检出漏清;\n"
        if len(self.lqdefect_right_camera) > 0:
            lq_S = 0
            for defect_info in self.lqdefect_right_camera:
                w = defect_info['w']
                h = defect_info['h']
                lq_S += w * h
            lq_ratio = round(lq_S / left_S * 100, 2)
            if lq_ratio > 50:
                temp = "西侧漏清率" + str(lq_ratio) + "%,大于50%"
            else:
                temp = "西侧漏清率" + str(lq_ratio) + "%,小于50%"
            result = temp + '\n'
            lq_result += result
        else:
            lq_result += "西侧未检出漏清;\n"
        # print(lq_result)
        return lq_result


    def ql_process(self):
        # (1)起楞分析:
        # 高度<2mm合格
        # 高度>2mm且<3mm可用于非汽车外板
        # 高度>3mm 不合格
        # 平滑过渡
        # 上侧未检出；
        # 下侧未检出；
        # 西侧未检出；
        ql_result = "起楞分析:\n"
        depth_threshold1 = 2
        depth_threshold2 = 3
        if len(self.qldefect_up_left_camera) > 0:
            for defect_info in self.qldefect_up_left_camera:
                imgpath = defect_info['image_url'].replace("//Grab1/192.168.100.1/img", '/home/hongtai/yolo/depth_img')
                deepth, judge_res = self.depth_judge_ql(imgpath, 120, depth_threshold1,depth_threshold2, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
                defect_info['deepth'] = deepth
                if judge_res == 1:
                    tempdepth = "上侧东检出起楞,高度<" + str(depth_threshold1) + "mm (达标)"
                elif judge_res == 2:
                    tempdepth = "上侧东检出起楞,高度>" + str(depth_threshold1) + ",且高度<" + str(depth_threshold2) + "mm (可用于非汽车外板)"
                else:
                    tempdepth = "上侧东检出起楞,高度>" + str(depth_threshold2) + "mm (不达标)"
            result =  tempdepth + '\n'
            ql_result += result
        else:
            ql_result += "上侧东未检出;\n"
        if len(self.qldefect_up_right_camera) > 0:
            for defect_info in self.qldefect_up_right_camera:
                imgpath = defect_info['image_url'].replace("//Grab1/192.168.100.1/img", '/home/hongtai/yolo/depth_img')
                deepth, judge_res = self.depth_judge_ql(imgpath, 120, depth_threshold1,depth_threshold2, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
                defect_info['deepth'] = deepth
                if judge_res == 1:
                    tempdepth = "上侧西检出起楞,高度<" + str(depth_threshold1) + "mm (达标)"
                elif judge_res == 2:
                    tempdepth = "上侧西检出起楞,高度>" + str(depth_threshold1) + ",且高度<" + str(depth_threshold2) + "mm (可用于非汽车外板)"
                else:
                    tempdepth = "上侧西检出起楞,高度>" + str(depth_threshold2) + "mm (不达标)"
            result =  tempdepth + '\n'
            ql_result += result
        else:
            ql_result += "上侧西未检出;\n"
        if len(self.qldefect_down_left_camera) > 0:
            for defect_info in self.qldefect_down_left_camera:
                imgpath = defect_info['image_url'].replace("//Grab2/192.168.100.2", '/home/hongtai/yolo/1002d')
                #imgpath = defect_info['image_url'].replace("//Grab1/192.168.100.1/img", '/home/hongtai/yolo/depth_img')
                deepth, judge_res = self.depth_judge_ql(imgpath, 120, depth_threshold1,depth_threshold2, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
                defect_info['deepth'] = deepth
                if judge_res == 1:
                    tempdepth = "下侧东检出起楞,高度<" + str(depth_threshold1) + "mm (达标)"
                elif judge_res == 2:
                    tempdepth = "下侧东检出起楞,高度>" + str(depth_threshold1) + ",且高度<" + str(depth_threshold2) + "mm (可用于非汽车外板)"
                else:
                    tempdepth = "下侧东检出起楞,高度>" + str(depth_threshold2) + "mm (不达标)"
            result =  tempdepth + '\n'
            ql_result += result
        else:
            ql_result += "下侧东未检出;\n"

        if len(self.qldefect_down_center_camera) > 0:
            for defect_info in self.qldefect_down_center_camera:
                #imgpath = defect_info['image_url'].replace("//Grab1/192.168.100.1/img", '/home/hongtai/yolo/depth_img')
                imgpath = defect_info['image_url'].replace("//Grab2/192.168.100.2", '/home/hongtai/yolo/1002d')
                deepth, judge_res = self.depth_judge_ql(imgpath, 120, depth_threshold1,depth_threshold2, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
                defect_info['deepth'] = deepth
                if judge_res == 1:
                    tempdepth = "下侧中检出起楞,高度<" + str(depth_threshold1) + "mm (达标)"
                elif judge_res == 2:
                    tempdepth = "下侧中检出起楞,高度>" + str(depth_threshold1) + ",且高度<" + str(depth_threshold2) + "mm (可用于非汽车外板)"
                else:
                    tempdepth = "下侧中检出起楞,高度>" + str(depth_threshold2) + "mm (不达标)"
            result =  tempdepth + '\n'
            ql_result += result
        else:
            ql_result += "下侧中未检出;\n"
        if len(self.qldefect_down_right_camera) > 0:
            for defect_info in self.qldefect_down_right_camera:
                #imgpath = defect_info['image_url'].replace("//Grab1/192.168.100.1/img", '/home/hongtai/yolo/depth_img')
                imgpath = defect_info['image_url'].replace("//Grab2/192.168.100.2", '/home/hongtai/yolo/1002d')
                deepth, judge_res = self.depth_judge_ql(imgpath, 120, depth_threshold1,depth_threshold2, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
                defect_info['deepth'] = deepth
                if judge_res == 1:
                    tempdepth = "下侧西检出起楞,高度<" + str(depth_threshold1) + "mm (达标)"
                elif judge_res == 2:
                    tempdepth = "下侧西检出起楞,高度>" + str(depth_threshold1) + ",且高度<" + str(depth_threshold2) + "mm (可用于非汽车外板)"
                else:
                    tempdepth = "下侧西检出起楞,高度>" + str(depth_threshold2) + "mm (不达标)"
            result =  tempdepth + '\n'
            ql_result += result
        else:
            ql_result += "下侧西未检出;\n"
        if len(self.qldefect_left_camera) > 0:
            for defect_info in self.qldefect_left_camera:
                imgpath = defect_info['image_url'].replace("//Grab1/192.168.100.1/img", '/home/hongtai/yolo/depth_img')
                deepth, judge_res = self.depth_judge_ql(imgpath, 120, depth_threshold1,depth_threshold2, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
                defect_info['deepth'] = deepth
                if judge_res == 1:
                    tempdepth = "西侧检出起楞,高度<" + str(depth_threshold1) + "mm (达标)"
                elif judge_res == 2:
                    tempdepth = "西侧检出起楞,高度>" + str(depth_threshold1) + ",且高度<" + str(depth_threshold2) + "mm (可用于非汽车外板)"
                else:
                    tempdepth = "西侧检出起楞,高度>" + str(depth_threshold2) + "mm (不达标)"
            result =  tempdepth + '\n'
            ql_result += result
        else:
            ql_result += "西侧未检出;\n"
        if len(self.qldefect_right_camera) > 0:
            for defect_info in self.qldefect_right_camera:
                imgpath = defect_info['image_url'].replace("//Grab1/192.168.100.1/img", '/home/hongtai/yolo/depth_img')
                deepth, judge_res = self.depth_judge_ql(imgpath, 120, depth_threshold1,depth_threshold2, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
                defect_info['deepth'] = deepth
                if judge_res == 1:
                    tempdepth = "东侧检出起楞,高度<" + str(depth_threshold1) + "mm (达标)"
                elif judge_res == 2:
                    tempdepth = "东侧检出起楞,高度>" + str(depth_threshold1) + ",且高度<" + str(depth_threshold2) + "mm (可用于非汽车外板)"
                else:
                    tempdepth = "东侧检出起楞,高度>" + str(depth_threshold2) + "mm (不达标)"
            result =  tempdepth + '\n'
            ql_result += result
        else:
            ql_result += "东侧未检出;\n"
        # print(ql_result)
        return ql_result

    def ac_process(self):
        # (1)凹槽分析:
        # 凹槽深度<2mm合格
        # 凹槽深度>2mm且<3mm可用于非汽车外板
        # 凹槽深度>3mm 不合格
        # 平滑过渡
        # 上侧未检出；
        # 下侧未检出；
        # 西侧未检出；
        ac_result = "凹槽分析:\n"
        depth_threshold1 = 2
        depth_threshold2 = 3
        if len(self.acdefect_up_left_camera) > 0:
            for defect_info in self.acdefect_up_left_camera:
                imgpath = defect_info['image_url'].replace("//Grab1/192.168.100.1/img", '/home/hongtai/yolo/depth_img')
                deepth, judge_res = self.depth_judge_ac(imgpath, 120, depth_threshold1,depth_threshold2, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
                defect_info['deepth'] = deepth
                if judge_res == 1:
                    tempdepth = "上侧东检出凹槽,深度<" + str(depth_threshold1) + "mm (达标)"
                elif judge_res == 2:
                    tempdepth = "上侧东检出凹槽,深度>" + str(depth_threshold1) + ",且高度<" + str(depth_threshold2) + "mm (可用于非汽车外板)"
                else:
                    tempdepth = "上侧东检出凹槽,深度>" + str(depth_threshold2) + "mm (不达标)"
            result =  tempdepth + '\n'
            ac_result += result
        else:
            ac_result += "上侧东未检出;\n"
        if len(self.acdefect_up_right_camera) > 0:
            for defect_info in self.acdefect_up_right_camera:
                imgpath = defect_info['image_url'].replace("//Grab1/192.168.100.1/img", '/home/hongtai/yolo/depth_img')
                deepth, judge_res = self.depth_judge_ac(imgpath, 120, depth_threshold1,depth_threshold2, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
                defect_info['deepth'] = deepth
                if judge_res == 1:
                    tempdepth = "上侧西检出凹槽,深度<" + str(depth_threshold1) + "mm (达标)"
                elif judge_res == 2:
                    tempdepth = "上侧西检出凹槽,深度>" + str(depth_threshold1) + ",且高度<" + str(depth_threshold2) + "mm (可用于非汽车外板)"
                else:
                    tempdepth = "上侧西检出凹槽,深度>" + str(depth_threshold2) + "mm (不达标)"
            result =  tempdepth + '\n'
            ac_result += result
        else:
            ac_result += "上侧西未检出;\n"
        if len(self.acdefect_down_left_camera) > 0:
            for defect_info in self.acdefect_down_left_camera:
                #imgpath = defect_info['image_url'].replace("//Grab1/192.168.100.1/img", '/home/hongtai/yolo/depth_img')
                imgpath = defect_info['image_url'].replace("//Grab2/192.168.100.2", '/home/hongtai/yolo/1002d')
                deepth, judge_res = self.depth_judge_ac(imgpath, 120, depth_threshold1,depth_threshold2, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
                defect_info['deepth'] = deepth
                if judge_res == 1:
                    tempdepth = "下侧东检出凹槽,深度<" + str(depth_threshold1) + "mm (达标)"
                elif judge_res == 2:
                    tempdepth = "下侧东检出凹槽,深度>" + str(depth_threshold1) + ",且高度<" + str(depth_threshold2) + "mm (可用于非汽车外板)"
                else:
                    tempdepth = "下侧东检出凹槽,深度>" + str(depth_threshold2) + "mm (不达标)"
            result =  tempdepth + '\n'
            ac_result += result
        else:
            ac_result += "下侧东未检出;\n"
        if len(self.acdefect_down_center_camera) > 0:
            for defect_info in self.acdefect_down_center_camera:
                #imgpath = defect_info['image_url'].replace("//Grab1/192.168.100.1/img", '/home/hongtai/yolo/depth_img')
                imgpath = defect_info['image_url'].replace("//Grab2/192.168.100.2", '/home/hongtai/yolo/1002d')
                deepth, judge_res = self.depth_judge_ac(imgpath, 120, depth_threshold1,depth_threshold2, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
                defect_info['deepth'] = deepth
                if judge_res == 1:
                    tempdepth = "下侧中检出凹槽,深度<" + str(depth_threshold1) + "mm (达标)"
                elif judge_res == 2:
                    tempdepth = "下侧中检出凹槽,深度>" + str(depth_threshold1) + ",且高度<" + str(depth_threshold2) + "mm (可用于非汽车外板)"
                else:
                    tempdepth = "下侧中检出凹槽,深度>" + str(depth_threshold2) + "mm (不达标)"
            result =  tempdepth + '\n'
            ac_result += result
        else:
            ac_result += "下侧中未检出;\n"
        if len(self.acdefect_down_right_camera) > 0:
            for defect_info in self.acdefect_down_right_camera:
                imgpath = defect_info['image_url'].replace("//Grab2/192.168.100.2", '/home/hongtai/yolo/1002d')
                deepth, judge_res = self.depth_judge_ac(imgpath, 120, depth_threshold1,depth_threshold2, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
                defect_info['deepth'] = deepth
                if judge_res == 1:
                    tempdepth = "下侧西检出凹槽,深度<" + str(depth_threshold1) + "mm (达标)"
                elif judge_res == 2:
                    tempdepth = "下侧西检出凹槽,深度>" + str(depth_threshold1) + ",且高度<" + str(depth_threshold2) + "mm (可用于非汽车外板)"
                else:
                    tempdepth = "下侧西检出凹槽,深度>" + str(depth_threshold2) + "mm (不达标)"
            result =  tempdepth + '\n'
            ac_result += result
        else:
            ac_result += "下侧西未检出;\n"
        if len(self.acdefect_left_camera) > 0:
            for defect_info in self.acdefect_left_camera:
                imgpath = defect_info['image_url'].replace("//Grab1/192.168.100.1/img", '/home/hongtai/yolo/depth_img')
                deepth, judge_res = self.depth_judge_ac(imgpath, 120, depth_threshold1,depth_threshold2, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
                defect_info['deepth'] = deepth
                if judge_res == 1:
                    tempdepth = "西侧检出凹槽,深度<" + str(depth_threshold1) + "mm (达标)"
                elif judge_res == 2:
                    tempdepth = "西侧检出凹槽,深度>" + str(depth_threshold1) + ",且高度<" + str(depth_threshold2) + "mm (可用于非汽车外板)"
                else:
                    tempdepth = "西侧检出凹槽,深度>" + str(depth_threshold2) + "mm (不达标)"
            result =  tempdepth + '\n'
            ac_result += result
        else:
            ac_result += "西侧未检出;\n"
        if len(self.acdefect_right_camera) > 0:
            for defect_info in self.acdefect_right_camera:
                imgpath = defect_info['image_url'].replace("//Grab1/192.168.100.1/img", '/home/hongtai/yolo/depth_img')
                deepth, judge_res = self.depth_judge_ac(imgpath, 120, depth_threshold1,depth_threshold2, defect_info['x'], defect_info['y'],
                                                 defect_info['w'], defect_info['h'])
                defect_info['deepth'] = deepth
                if judge_res == 1:
                    tempdepth = "东侧检出凹槽,深度<" + str(depth_threshold1) + "mm (达标)"
                elif judge_res == 2:
                    tempdepth = "东侧检出凹槽,深度>" + str(depth_threshold1) + ",且高度<" + str(depth_threshold2) + "mm (可用于非汽车外板)"
                else:
                    tempdepth = "东侧检出凹槽,深度>" + str(depth_threshold2) + "mm (不达标)"
            result =  tempdepth + '\n'
            ac_result += result
        else:
            ac_result += "东侧未检出;\n"
        # print(ac_result)
        return ac_result

    def qk_process(self):
        # (1)气孔分析:
        # 不允许存在直径>2mm的气孔
        # 单位面积不允许存在2个直径>1mm的气孔
        # 上侧未检出；
        # 下侧未检出；
        # 西侧未检出；
        qk_result = "气孔分析:\n"
        qk_threshold1 = 4
        sendes_data = []
        if len(self.qkdefect_up_left_camera) > 0:
            defect_info = self.get_max_data_json(self.qkdefect_up_left_camera)
            real_w = defect_info['real_w']
            real_h = defect_info['real_h']
            qk_d = (real_w+real_h)/2
            if qk_d > 4:
                tempdepth = "上侧东存在直径>" + str(qk_threshold1) + "mm的气孔,不达标"
            else:
                tempdepth = "上侧东不存在直径>" + str(qk_threshold1) + "mm的气孔,达标"
            result =  tempdepth + '\n'
            qk_result += result
        else:
            qk_result += "上侧东未检出;\n"
        if len(self.qkdefect_up_right_camera) > 0:
            defect_info = self.get_max_data_json(self.qkdefect_up_right_camera)
            real_w = defect_info['real_w']
            real_h = defect_info['real_h']
            qk_d = (real_w+real_h)/2
            if qk_d > 4:
                tempdepth = "上侧西存在直径>" + str(qk_threshold1) + "mm的气孔,不达标"
            else:
                tempdepth = "上侧西不存在直径>" + str(qk_threshold1) + "mm的气孔,达标"
            result =  tempdepth + '\n'
            qk_result += result
        else:
            qk_result += "上侧西未检出;\n"
        if len(self.qkdefect_down_left_camera) > 0:
            defect_info = self.get_max_data_json(self.qkdefect_down_left_camera)
            real_w = defect_info['real_w']
            real_h = defect_info['real_h']
            qk_d = (real_w+real_h)/2
            if qk_d > 4:
                tempdepth = "下侧东存在直径>" + str(qk_threshold1) + "mm的气孔,不达标"
            else:
                tempdepth = "下侧东不存在直径>" + str(qk_threshold1) + "mm的气孔,达标"
            result =  tempdepth + '\n'
            qk_result += result
        else:
            qk_result += "下侧东未检出;\n"

        if len(self.qkdefect_down_center_camera) > 0:
            defect_info = self.get_max_data_json(self.qkdefect_down_center_camera)
            real_w = defect_info['real_w']
            real_h = defect_info['real_h']
            qk_d = (real_w+real_h)/2
            if qk_d > 4:
                tempdepth = "下侧中存在直径>" + str(qk_threshold1) + "mm的气孔,不达标"
            else:
                tempdepth = "下侧中不存在直径>" + str(qk_threshold1) + "mm的气孔,达标"
            result =  tempdepth + '\n'
            qk_result += result
        else:
            qk_result += "下侧中未检出;\n"
        if len(self.qkdefect_down_right_camera) > 0:
            defect_info = self.get_max_data_json(self.qkdefect_down_right_camera)
            real_w = defect_info['real_w']
            real_h = defect_info['real_h']
            qk_d = (real_w+real_h)/2
            if qk_d > 4:
                tempdepth = "下侧西存在直径>" + str(qk_threshold1) + "mm的气孔,不达标"
            else:
                tempdepth = "下侧西不存在直径>" + str(qk_threshold1) + "mm的气孔,达标"
            result =  tempdepth + '\n'
            qk_result += result
        else:
            qk_result += "下侧西未检出;\n"
        if len(self.qkdefect_left_camera) > 0:
            defect_info = self.get_max_data_json(self.qkdefect_left_camera)
            real_w = defect_info['real_w']
            real_h = defect_info['real_h']
            qk_d = (real_w+real_h)/2
            if qk_d > 4:
                tempdepth = "西侧存在直径>" + str(qk_threshold1) + "mm的气孔,不达标"
            else:
                tempdepth = "西侧不存在直径>" + str(qk_threshold1) + "mm的气孔,达标"
            result =  tempdepth + '\n'
            qk_result += result
        else:
            qk_result += "西侧未检出;\n"
        if len(self.qkdefect_right_camera) > 0:
            defect_info = self.get_max_data_json(self.qkdefect_right_camera)
            real_w = defect_info['real_w']
            real_h = defect_info['real_h']
            qk_d = (real_w+real_h)/2
            if qk_d > 4:
                tempdepth = "东侧存在直径>" + str(qk_threshold1) + "mm的气孔,不达标"
            else:
                tempdepth = "东侧不存在直径>" + str(qk_threshold1) + "mm的气孔,达标"
            result =  tempdepth + '\n'
            qk_result += result
        else:
            qk_result += "东侧未检出;\n"
        # print(qk_result)
        return qk_result


    def init(self):
        # 相机列表置空等
        self.flowids_up_left_camera = []
        self.flowids_up_right_camera = []
        self.flowids_left_camera = []
        self.flowids_right_camera = []
        self.flowids_down_left_camera = []
        self.flowids_down_center_camera = []
        self.flowids_down_right_camera = []

        self.imagepath_up_left_camera = []
        self.imagepath_up_right_camera = []
        self.imagepath_left_camera = []
        self.imagepath_right_camera = []
        self.imagepath_down_left_camera = []
        self.imagepath_down_center_camera = []
        self.imagepath_down_right_camera = []

        self.dhkdefect_up_left_camera = []
        self.dhkdefect_up_right_camera = []
        self.dhkdefect_down_left_camera = []
        self.dhkdefect_down_center_camera = []
        self.dhkdefect_down_right_camera = []
        self.dhkdefect_left_camera = []
        self.dhkdefect_right_camera = []

        # 漏清缺陷信息
        self.lqdefect_up_left_camera = []
        self.lqdefect_up_right_camera = []
        self.lqdefect_down_left_camera = []
        self.lqdefect_down_center_camera = []
        self.lqdefect_down_right_camera = []
        self.lqdefect_left_camera = []
        self.lqdefect_right_camera = []

        #1212新增起楞缺陷信息
        self.qldefect_up_left_camera = []
        self.qldefect_up_right_camera = []
        self.qldefect_down_left_camera = []
        self.qldefect_down_center_camera = []
        self.qldefect_down_right_camera = []
        self.qldefect_left_camera = []
        self.qldefect_right_camera = []
        #凹槽
        self.acdefect_up_left_camera = []
        self.acdefect_up_right_camera = []
        self.acdefect_down_left_camera = []
        self.acdefect_down_center_camera = []
        self.acdefect_down_right_camera = []
        self.acdefect_left_camera = []
        self.acdefect_right_camera = []
        #气孔
        self.qkdefect_up_left_camera = []
        self.qkdefect_up_right_camera = []
        self.qkdefect_down_left_camera = []
        self.qkdefect_down_center_camera = []
        self.qkdefect_down_right_camera = []
        self.qkdefect_left_camera = []
        self.qkdefect_right_camera = []


        # 待坐标转换信息
        self.picdata_up_wait = []
        self.picdata_down_wait = []

        # 上表偏移量
        self.up_offset = [-1, -1]
        # 下表偏移量 左中 中右
        self.down_offset = [-1, -1, -1, -1]
        # 头部距离
        self.ul_up_dis = -1
        self.ur_up_dis = -1
        self.l_up_dis = -1
        self.r_up_dis = -1
        self.dl_up_dis = -1
        self.dc_up_dis = -1
        self.dr_up_dis = -1

    # 获得图片中钢材距离边界的距离
    def get_img_dixtance(self, img_path):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        # height, width = img.shape[:]
        # imgl = img[0:height, 700:2500]

        col_list = np.sum(img, axis=0)
        c_m = np.max(col_list) * 5 / 16

        row_list = np.sum(img, axis=1)
        r_m = np.max(row_list) * 5 / 16

        left = 0
        right = 0
        up = 0
        down = 0

        for i in range(len(col_list)):
            if col_list[i] >= c_m:
                left = i
                break

        for j in range(len(col_list) - 1, -1, -1):
            if col_list[j] >= c_m:
                right = len(col_list) - j
                break
        for i in range(len(row_list)):
            if row_list[i] >= r_m:
                up = i
                break

        for j in range(len(row_list) - 1, -1, -1):
            if row_list[j] >= r_m:
                down = len(row_list) - j
                break
        return up, down, left, right

    # 获得该图片是否含有头部 有返回头部距离 无返回-1
    def get_pic_dis(self, img_path):
        up, down, left, right = self.get_img_dixtance(img_path)
        if up < 10 and down < 10 and left < 10 and right < 10:  # 判断全黑
            return -1
        elif up < 20 and down > 400:  # 头部
            return -1
        else:  # 前几张中只有全黑 含头
            return [up, down, left, right]


def main(args):
    device_num = args.device_num
    es_num = args.es_num
    create3d_num = args.create3d_num
    # upsample = args.upsample
    upsample = False
    # http接收
    json_queue = multiprocessing.Queue()
    # 3d缺陷信息
    queue_3d = multiprocessing.Queue()
    res_queue = multiprocessing.Queue()
    predict_queue = multiprocessing.Queue()
    down_json_queue = multiprocessing.Queue()

    infer_list = []
    infer_ulr_qk_list = []
    infer2_list = []
    create3d_list = []
    es_list = []

    alive = Value('b', False)
    alive.value = True

    for index in range(0, 1):
        infer = InferProcess(device_id=index, model_ulr_path=args.model_ulr, model_ulr_qk=None,
                             json_queue=json_queue, res_queue=res_queue,
                             predict_queue=predict_queue, down_json_queue=down_json_queue,
                             queue3d=queue_3d, upsample=upsample, alive=alive)
        infer_list.append(infer)
        infer.start()

    for index in range(1, 2):
        infer_ulr_qk = InferProcess_ulr_qk(device_id=index, model_ulr_path=None,
                                           model_ulr_qk=args.model_ulr_qk,
                                           json_queue=json_queue, res_queue=res_queue,
                                           predict_queue=predict_queue, down_json_queue=down_json_queue,
                                           queue3d=queue_3d, upsample=upsample, alive=alive)
        
        infer_ulr_qk_list.append(infer_ulr_qk)
        infer_ulr_qk.start()

    for index in range(2, 3):
        infer2 = InferProcess2(device_id=index, model_d_path=args.model_d, down_json_queue=down_json_queue,
                               res_queue=res_queue,
                               predict_queue=predict_queue, queue3d=queue_3d, upsample=upsample, alive=alive)
        infer2_list.append(infer2)
        infer2.start()

    for index in range(es_num):
        es = EsProcess(res_queue=res_queue, index=index, alive=alive)
        es_list.append(es)
        es.start()
    for index in range(create3d_num):
        create3d = Create3dProcess(queue3d=queue_3d, index=index, alive=alive)
        create3d_list.append(create3d)
        create3d.start()

    host = localhost
    port = 9007
    httpServer = HttpProcess(host, port, json_queue, alive)
    httpServer.start()

    trans = PosTransformProcess(res_queue=res_queue, predict_queue=predict_queue, alive=alive)
    trans.start()

    def handle_exit(signum=None, frame=None):
        alive.value = False
        sys.exit()

    atexit.register(handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    while alive.value == True:
        time.sleep(600)
        if not httpServer.is_alive():
            httpServer = HttpProcess(host, port, json_queue, alive)
            httpServer.start()

        if not trans.is_alive():
            trans = PosTransformProcess(res_queue=res_queue, predict_queue=predict_queue, alive=alive)
            trans.start()

        down_infer = []
        for i, infer in enumerate(infer_list):
            if not infer.is_alive():
                down_infer.append(infer)
        down_infer2 = []
        for i, infer2 in enumerate(infer2_list):
            if not infer2.is_alive():
                down_infer2.append(infer2)
        down_infer3 = []
        for i, infer3 in enumerate(infer_ulr_qk_list):
            if not infer3.is_alive():
                down_infer3.append(infer3)
        for infer in down_infer:
            logger.warning('infer on device {} is terminated'.format(infer.device_id))
            infer_list.remove(infer)
            new_infer = InferProcess(device_id=infer.device_id, model_ulr_path=infer.model_ulr_path,
                                     model_ulr_qk=infer.model_ulr_qk_path, json_queue=json_queue,
                                     res_queue=res_queue, predict_queue=predict_queue, down_json_queue=down_json_queue,
                                     queue3d=queue_3d, upsample=upsample, alive=alive)

            infer_list.append(new_infer)
            new_infer.start()

        for infer in down_infer2:
            logger.warning('infer2 on device {} is terminated'.format(infer.device_id))
            infer2_list.remove(infer)
            new_infer = InferProcess2(device_id=infer.device_id, model_d_path=infer.model_d_path,
                                      down_json_queue=down_json_queue,
                                      res_queue=res_queue, predict_queue=predict_queue, queue3d=queue_3d,
                                      upsample=upsample, alive=alive)

            infer2_list.append(new_infer)
            new_infer.start()

        for infer in down_infer3:
            logger.warning('infer3qk on device {} is terminated'.format(infer.device_id))
            infer_ulr_qk_list.remove(infer)
            new_infer = InferProcess_ulr_qk(device_id=infer.device_id, model_ulr_path=infer.model_ulr_path,
                                     model_ulr_qk=infer.model_ulr_qk_path, json_queue=json_queue,
                                     res_queue=res_queue, predict_queue=predict_queue, down_json_queue=down_json_queue,
                                     queue3d=queue_3d, upsample=upsample, alive=alive)

            infer_ulr_qk_list.append(new_infer)
            new_infer.start()

        down_es = []
        for i, es in enumerate(es_list):
            if not es.is_alive():
                down_es.append(es)
        for es in down_es:
            logger.warning('es index {} is terminated'.format(es.index))
            es_list.remove(es)
            new_es = EsProcess(res_queue=res_queue, index=es.index, alive=alive)
            es_list.append(new_es)
            new_es.start()

        down_create3d = []
        for i, create3d in enumerate(create3d_list):
            if not create3d.is_alive():
                down_create3d.append(create3d)
        for create3d in down_create3d:
            logger.warning('create3d index {} is terminated'.format(create3d.index))
            create3d_list.remove(create3d)
            new_create3d = Create3dProcess(queue3d=queue_3d, index=create3d.index, alive=alive)
            create3d_list.append(new_create3d)
            new_create3d.start()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='YoloV5 offline model inference.')
    # model_ulr:上、左、右（u\l\r）模型
    parser.add_argument('--model_ulr', type=str,
                        default="/home/hongtai/yolo/Yolov5_for_Pytorch/yolov5/output/ulr916_nms_bs1.om",
                        help='om ulr model path')
    # model_d:下表模型
    parser.add_argument('--model_d', type=str,
                        default="/home/hongtai/yolo/Yolov5_for_Pytorch/yolov5/output/down1223_nms_bs1.om",
                        help='om d model path')
    # model_ulr_qk:上左右气孔模型
    parser.add_argument('--model_ulr_qk', type=str,
                        # default="/home/hongtai/yolo/Yolov5_for_Pytorch/yolov5/output/ulr916_nms_bs1.om",
                        #default="/home/hongtai/yolo/Yolov5_for_Pytorch/yolov5/output/qk_finetune_best_out2_nms_bs1.om",
                        default="/home/hongtai/yolo/Yolov5_for_Pytorch/yolov5/output/20240126qkrz_nms_bs1.om",
                        help='om ulr qk model path')
    parser.add_argument('--device_num', type=int, default=16, help='device num')
    parser.add_argument('--es_num', type=int, default=1, help='om batch size')
    parser.add_argument('--create3d_num', type=int, default=1, help='om batch size')
    flags = parser.parse_args()
    main(flags)