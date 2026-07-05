# init_settings.py

import enum
import json
from datetime import datetime
import socket

import traceback
import uuid

import requests
import urllib3
import numpy as np
import cv2
import os
import yaml

from UtilObject.LoggerUtil import LoggerUtil

current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)


class MySettings:
    def __init__(self):
        try:
            self.logger = LoggerUtil.create_logger()
            # 当前各个进程运行状态

            self.cfg_setting_path = os.path.join(parent_dir, 'config', 'setting.yaml')
            self.cfg_model_path = os.path.join(parent_dir, 'config', 'model.yaml')
            self.labelme_templete_path = os.path.join(parent_dir, 'config', 'labelme_templete.json')
            self.appraise_path = os.path.join(parent_dir, 'config', 'appraise_mg.json')

            # 如果有需要在初始化时设置的实例属性，可以在这里定义
            self.parse_config()
            # 关于一些性能方面的配置
            # 在不同的文件中定义这些函数并调用，对于全局配置来说是有效的，只要这些函数在主文件中被正确调用即可。
            self.setup_network_and_computations()

        except Exception as e:
            self.logger.error("----------------------Mysetting解析失败-------------------------")
            traceback.print_exc()
            self.logger.error(e)

    def parse_config(self):
        # 不方便用try、否则项目不终止
        # 其中Appraise是评级配置
        with open(self.cfg_setting_path, encoding='utf-8') as f:
            self.cfg_runner = yaml.load(f, Loader=yaml.FullLoader)
        with open(self.cfg_model_path, encoding='utf-8') as f:
            self.model_runner = yaml.load(f, Loader=yaml.FullLoader)
        with open(self.labelme_templete_path, 'r', encoding='utf-8') as file:
            self.labelme_templete = json.load(file)
        with open(self.appraise_path, 'r', encoding='utf-8') as file:
            temp_appraise_cfg = json.load(file)
            self.logger.error('默认套餐读取成功' + str(temp_appraise_cfg))
            self.appraise = Appraise(self, temp_appraise_cfg)

    def post_client_data(self, database, msg_type, msg_id, insert_time, message, main_id):
        # 给客户端发送报警信息
        # 消息发送成功，服务端会返回状态码
        # 主要在summary中调用
        from UtilObject.DatabaseUtil import MyDatabase
        database = MyDatabase(self)
        database.create_es()
        try:
            alert_info_id = str(uuid.uuid4())
            data = {
                'id': alert_info_id,
                'msg_type': msg_type,
                'msg_id': msg_id,
                'insert_time': str(insert_time),
                'message': message,  # .encode('utf-8')
                'main_id': main_id
            }
            proxies={
                'http': 'http://192.168.100.100:8094'
            }
            header_info = {
                "Content-type": "application/json;charset=utf-8"
            }
            # 发送 一个POST请求
            # url: 请求的url，必填；
            # data: 选填，请求参数；
            # json: 选填，请求参数；
            # kwargs：选填，可以传入headers、cookies等。
            # return request('post', url, data=data, json=json, **kwargs)
            # 这里data是一个字典，用json.dumps方法转换为字符串
            res = requests.post(url=self.cfg_runner['post_client_url'],
                                data=json.dumps(data, ensure_ascii=False).encode('utf-8'),proxies=proxies, headers=header_info,
                                timeout=5)
            # print(res.text)
            database.insert_alert_info(alert_info_id, str(message), str(msg_type), str(msg_id), insert_time, main_id, 0,
                                       '')

        except Exception as e:
            self.logger.error(message)
            self.logger.error(traceback.format_exc())

    # 通知后再发么？
    def set_appraise_cfg(self, dic_appraise):
        # 将字典对象写入 JSON 文件
        with open(self.appraise_path, "w") as json_file:
            json.dump(dic_appraise, json_file)

    def updata_appraise(self):
        from UtilObject.DatabaseUtil import MyDatabase
        database = MyDatabase(self)
        database.create_es()

        current_appraise_cfg_id = database.get_current_appraise_cfg_id()
        if current_appraise_cfg_id is not None:
            # 当前套餐id不为空
            current_appraise_cfg = database.get_current_appraise_cfg_from_id(current_appraise_cfg_id)
            if current_appraise_cfg is not None:
                # 当前套餐读取数据库评级文件成功
                self.logger.error('summary当前套餐读取成功' + str(current_appraise_cfg))
                self.appraise = Appraise(self, current_appraise_cfg)
            else:
                self.logger.error('summary当前套餐读取成功当前套餐id对应评级配置为空')
                default_appraise_cfg = database.get_default_appraise_cfg()
                if default_appraise_cfg is not None:
                    # 读取默认套餐成功
                    self.appraise = Appraise(self, current_appraise_cfg)
                else:
                    self.logger.error('summary当前套餐读取成功没有套餐，数据库也没有默认套餐，使用配置文件默认配置')
        else:
            self.logger.error('summary当前套餐读取成功没有套餐，数据库也没有默认套餐，使用配置文件默认配置')
        
        # temp_appraise_cfg = database.get_appraise_cfg()
        # if temp_appraise_cfg is not None:
        #     self.appraise = Appraise(self, temp_appraise_cfg)
        # else:
        #     self.logger.error('读取数据库评级文件失败')

    '''
    allowed_gai_family() 函数被定义，用于设置 urllib3 库中的套接字地址簇。默认情况下，urllib3 会尝试使用 IPv6 和 IPv4 两种套接字地址簇进行连接，但是在某些环境下可能会导致连接延迟。通过将 allowed_gai_family 函数设置为只返回 socket.AF_INET，即 IPv4 地址簇，可以避免这种延迟。
    将 allowed_gai_family 函数赋值给 urllib3.util.connection.allowed_gai_family，从而修改 urllib3 库的默认行为。
    使用 np.set_printoptions(suppress=True) 来设置 numpy 数组的打印选项，使其在打印时不显示科学计数法，而是直接显示数值。
    使用 cv2.setNumThreads(1) 来设置 OpenCV 的线程数为 1，这可能有助于避免多线程竞争导致的性能问题。
    使用 os.environ['OPENBLAS_NUM_THREADS'] = '1' 来设置 OpenBLAS 的线程数为 1，这同样是为了避免多线程竞争导致的性能问题。
   
    
    对于全局配置来说是有效的，只要这些函数在主文件中被正确调用即可。
    '''

    def setup_network_and_computations(self):
        def allowed_gai_family():
            return socket.AF_INET

        urllib3.util.connection.allowed_gai_family = allowed_gai_family
        np.set_printoptions(suppress=True)
        cv2.setNumThreads(1)
        os.environ['OPENBLAS_NUM_THREADS'] = '1'


def create_inverse_dict(dictionary):
    inverse_dict = {}
    for key, value in dictionary.items():
        if value not in inverse_dict:
            inverse_dict[value] = [key]
        else:
            inverse_dict[value].append(key)
    return inverse_dict


class Appraise:
    def __init__(self, sys_setting, appraise_cfg):
        self.chinese_typeid_dict = None
        self.appraise_type_dict = None
        self.score_threshold = None
        self.appraise_cfg = appraise_cfg
        self.logger = sys_setting.logger
        self.cfg_runner = sys_setting.cfg_runner
        self.parse_appraise_cfg_json()

    def parse_appraise_cfg_json(self):
        self.score_threshold = self.appraise_cfg['score_threshold']
        self.appraise_type_dict = {}
        self.chinese_typeid_dict = create_inverse_dict(self.cfg_runner['Detect']['typeid_chinese'])
        loss_rule_dict = {}
        alarm_rule_dict = {}
        warning_rule_dict = {}
        filter_rule_dict = {}
        turn_rule_dict = {}

        loss_standard = self.appraise_cfg['loss_standard']
        alarm_setting = self.appraise_cfg['alarm_setting']
        warning_setting = self.appraise_cfg['warning_setting']
        # 灵敏度设置：过滤条件、转换条件
        filter_setting = self.appraise_cfg['filter_setting']

        for type_id in self.cfg_runner['Detect']['type_trans_a2c']:
            loss_rule_dict[type_id] = []
            alarm_rule_dict[type_id] = []
            warning_rule_dict[type_id] = []
            filter_rule_dict[type_id] = []
            turn_rule_dict[type_id] = []
        # 根据配置文件进行设置
        for rule in loss_standard:
            type_id = rule['type']
            loss_rule_dict[type_id].append(rule)

        for rule in alarm_setting:
            type_id = rule['type']
            alarm_rule_dict[type_id].append(rule)

        for rule in warning_setting:
            type_id = rule['type']
            warning_rule_dict[type_id].append(rule)
        # 过滤性质的内容
        for rule in filter_setting:
            type_chinese = rule['name']
            if type_chinese == "所有类型":
                for key in filter_rule_dict.keys():
                    filter_rule_dict[key].append(rule)
            else:
                # 如果出现多个id对应同一个中文，只取第一个
                type_id = self.chinese_typeid_dict[type_chinese][0]
                filter_rule_dict[type_id].append(rule)
        # 每个类别一个评级对象
        for type_id in self.cfg_runner['Detect']['type_trans_a2c']:

            if type_id not in self.appraise_type_dict.keys():
                type_name = self.cfg_runner['Detect']['typeid_chinese'][type_id]

                self.appraise_type_dict[type_id] = Appraise_Type(self.logger, self.cfg_runner, type_name, type_id,
                                                                 loss_rule_dict[type_id], alarm_rule_dict[type_id],
                                                                 warning_rule_dict[type_id], filter_rule_dict[type_id],
                                                                 turn_rule_dict[type_id])


Grade = enum.Enum('Grade', ('不评级', '疑似', '警告', '报警'))  # Grade索引从1开始 枚举


class Appraise_Type:
    '''
    每种类型有扣分情况、根据不同的级别扣除不同的分,唯一性
    每种类型有多种评级条件，在某个条件下，有不同程度的评估
    '''

    def __init__(self, logger, cfg_runner, type_name, type_id, loss_rule_list, alarm_rule_list, warning_rule_list,
                 filter_rule_list, turn_rule_list):
        self.logger = logger
        self.type_name = type_name
        self.type_id = type_id
        self.cfg_runner = cfg_runner
        self.loss_rule_list = loss_rule_list
        self.alarm_rule_list = alarm_rule_list
        self.warning_rule_list = warning_rule_list
        self.filter_rule_list = filter_rule_list
        self.turn_rule_list = turn_rule_list
        # 和评级相关的几个选项
        self.need_merge = False
        self.need_area = False
        # 20240630马钢新增评级需求
        self.need_other_depth = False   

        self.appraise_unit = {}
        self.filter_unit = {}
        self.turn_unit = {}
        self.parse_grade_rule()

    def parse_grade_rule(self):
        # 评判条件、范围低中高
        for condition in self.cfg_runner['Conclusion']['appraise_condition']:
            self.appraise_unit[condition] = [False, 0, 0, 0]
        for condition in self.cfg_runner['Conclusion']['filter_condition']:
            self.filter_unit[condition] = [False, 0, 0]
        for condition in self.cfg_runner['Conclusion']['turn_condition']:
            # 转换条件 该类能够转换、转换类型、下限上限
            self.turn_unit[condition] = [False, 0, 0, 0]
        try:
            for warning_rule, alarm_rule in zip(self.warning_rule_list, self.alarm_rule_list):
                if warning_rule['unit'] in self.appraise_unit.keys() and alarm_rule['unit'] in self.appraise_unit.keys():
                    self.appraise_unit[warning_rule['unit']][0] = True
                    self.appraise_unit[warning_rule['unit']][1] = warning_rule['range']['lower_limit']
                    self.appraise_unit[warning_rule['unit']][2] = warning_rule['range']['upper_limit']
                    self.appraise_unit[warning_rule['unit']][3] = alarm_rule['range']['upper_limit']

            if self.type_id in self.cfg_runner['Conclusion']['typeid_merge']:
                self.need_merge = True
            if self.type_id in self.cfg_runner['Conclusion']['typeid_area']:
                self.need_area = True
            # 20240630马钢新增
            if self.type_id in self.cfg_runner['Conclusion']['typeid_other_depth']:
                self.need_other_depth = True  
            if len(self.filter_rule_list) > 0:
                for filter_rule in self.filter_rule_list:
                    if filter_rule['unit'] in self.filter_unit.keys():
                        self.filter_unit[filter_rule['unit']][0] = True  # 滤除可能有多组条件滤除
                        self.filter_unit[filter_rule['unit']][1] = filter_rule['range']['lower_limit']
                        self.filter_unit[filter_rule['unit']][2] = filter_rule['range']['upper_limit']
            if len(self.turn_rule_list) > 0:
                for turn_rule in self.turn_rule_list:
                    if turn_rule['unit'] in self.turn_unit.keys():
                        self.turn_unit[turn_rule['unit']][0] = True
                        self.turn_unit[turn_rule['unit']][1] = turn_rule['target_period_type']
                        self.turn_unit[turn_rule['unit']][2] = turn_rule['range']['lower_limit']
                        self.turn_unit[turn_rule['unit']][3] = turn_rule['range']['upper_limit']



        except Exception as e:
            self.logger.error('配置文件出错，请检测拼写情况')
            self.logger.error(traceback.format_exc())

    # 按照评级条件、阈值判断等级和扣分情况
    def get_grade_loss(self, appraise_condition, value):
        try:
            # self.logger.error("评级上下限{}，{}，{}".format(self.appraise_unit[appraise_condition][1],self.appraise_unit[appraise_condition][2],self.appraise_unit[appraise_condition][3]))
            # self.logger.error("扣分{}，{}，{}".format(self.loss_rule_list[0]['loss'],self.loss_rule_list[0]['warning_loss'],self.loss_rule_list[0]['alarm_loss']))
            if self.appraise_unit[appraise_condition][0]:  # 有评级条件才会评级
                if value < self.appraise_unit[appraise_condition][1]:
                    return Grade(2), self.loss_rule_list[0]['loss']
                elif value < self.appraise_unit[appraise_condition][2]:
                    return Grade(3), self.loss_rule_list[0]['warning_loss']
                elif value < self.appraise_unit[appraise_condition][3]:
                    return Grade(4), self.loss_rule_list[0]['alarm_loss']
                else:
                    return Grade(1), 0  # 一般不会执行
            else:
                return None, None
        except Exception as e:
            self.logger.error('评级配置文件设置等级出错，请检测拼写情况')
            self.logger.error(traceback.format_exc())
            # 过滤设置 放在钢材类中了 filter_defect

    # 根据阈值判断是否可以进行合并，且进行类型转换 针对列表字典形式的图像缺陷
    def set_turn_type(self, image_defect_list, turn_condition, value):
        try:
            if self.turn_unit[turn_condition][0]:
                if self.turn_unit[turn_condition][2] <= value <= self.turn_unit[turn_condition][3]:
                    for image_defect in image_defect_list:
                        image_defect['type'] = self.turn_unit[turn_condition][1]
                    return True, self.turn_unit[turn_condition][1]

                else:
                    return False, None
        except Exception as e:
            self.logger.error('转换配置文件设置等级出错，请检测拼写情况')
            self.logger.error(traceback.format_exc())


if __name__ == '__main__':
    config = MySettings()
    # config.updata_appraise()
    print(config.appraise.appraise_type_dict[10].filter_unit)
    print(config.appraise.appraise_type_dict[10].turn_unit)
    print(config.appraise.appraise_type_dict[10].appraise_unit)
    # config.post_client_data(database=None, msg_type='steel_defect', msg_id='c35e2d23-1c7b-436c-b16f-9b7e952d65e7',
    #                         insert_time='2024-05-15 20:46:53',
    #                         message='20240515204633批次, 出现大面积[划伤]报警, 大小为2364.15mm^2, 位于距离钢材头部2.21m',
    #                         main_id='20240515204633')
