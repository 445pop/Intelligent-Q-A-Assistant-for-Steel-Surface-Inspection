from datetime import datetime
import uuid

import numpy as np

import cv2
import os
np.set_printoptions(threshold=np.inf)
from UtilObject.DatabaseUtil import MyDatabase


class RepeatDefect:
    # 周期性缺陷
    def __init__(self):
        self.id = ''
        self.camera_id = 0
        self.main_id = ''
        self.defect_type = 0
        self.surface_id = 0
        self.grade = ''
        self.real_x = 0
        self.real_y = 0
        self.insert_time = ''
        self.repeat_len = 0
        self.repeat_num = 0
        self.is_repeat = 0

    def get_dict(self):
        temp_dict = vars(self)
        temp_dict.pop('is_repeat',None)
        return temp_dict

    def set_parm_by_group_period_defect(self, cu_group_period_defect, cu_group_grade, diff_value):
        self.id = str(uuid.uuid4())
        self.real_x = cu_group_period_defect[0]['real_x']
        self.real_y = cu_group_period_defect[0]['real_y'] 
        self.defect_type = cu_group_period_defect[0]['type']
        self.camera_id = cu_group_period_defect[0]['camera_id']
        self.surface_id = cu_group_period_defect[0]['surface_id']
        self.main_id = cu_group_period_defect[0]['main_id']
        self.grade = cu_group_grade
        self.insert_time = datetime.now()
        self.repeat_len = round(diff_value, 2)
        self.repeat_num = len(cu_group_period_defect)
        # 对图像缺陷设置匹配id


class ImageDefect:
    # 图像缺陷
    def __init__(self):
        self.id = ''
        self.main_id = ''
        self.type = 0
        self.steel_defect_id = ""
        self.x = 0
        self.y = 0
        self.w = 0
        self.h = 0
        self.real_x = 0
        self.real_y = 0
        self.real_w = 0
        self.real_h = 0
        self.real_depth = 0
        self.surface_id = 0
        self.camera_id = 0
        self.insert_time = ''
        self.crop_x = 0
        self.crop_y = 0
        self.crop_w = 0
        self.crop_h = 0
        self.flow_id = 0
        self.confidence = 0
        self.grade = "疑似"
        self.is_visualize = True
        self.is_user_delete = False
        self.image_id = ''
        self.image2_id = ""
        self.image3_id = ""
        self.image4_id = ""
        self.crop_image_url = ""
        self.crop_image2_url = ""
        self.crop_image3_url = ""
        self.crop_image4_url = ""
        self.other0 = ""
        self.other1 = ''
        # 额外新增 插入数据库删掉即可
        self._id = ''

    def get_dict(self):
        temp_dict = vars(self)
        temp_dict.pop('_id', None)
        return temp_dict
        
    

    @staticmethod
    def results2defect(cfg_runner,results):
        # [[object,object],[object,object],[object,object]]
        temp_batch_defects = []
        for pred_boxs in results:
            temp_image_defect_list = []
            for row_info in pred_boxs:
                x1, y1, x2, y2, conf, class_id = row_info[0], row_info[1], row_info[2], row_info[3], row_info[
                    4], row_info[5]
                typeid = cfg_runner['type_trans_a2c'][int(class_id)]
              

                temp_image_defect = ImageDefect()
                temp_image_defect.x = x1
                temp_image_defect.y = y1
                temp_image_defect.w = x2 - x1
                temp_image_defect.h = y2 - y1
                temp_image_defect.confidence = round(conf, 3)
                temp_image_defect.type = typeid
                if(typeid in cfg_runner['Conclusion']['typeid_need_summary']):
                    temp_image_defect.is_visualize = False
                temp_image_defect_list.append(temp_image_defect)
            temp_batch_defects.append(temp_image_defect_list)
        return temp_batch_defects
    #
    @staticmethod
    def pred_result2defect(cfg_runner,row_info):
        x1, y1, x2, y2, conf, class_id = row_info[0], row_info[1], row_info[2], row_info[3], row_info[4], row_info[5]
        typeid = cfg_runner['Detect']['type_trans_a2c'][int(class_id)]

        temp_image_defect = ImageDefect()
        temp_image_defect.x = x1
        temp_image_defect.y = y1
        temp_image_defect.w = x2 - x1
        temp_image_defect.h = y2 - y1
        temp_image_defect.confidence = round(conf, 3)
        temp_image_defect.type = typeid

        return temp_image_defect
    @staticmethod
    def create_new_defect(json_dict):
        temp = ImageDefect()
        temp.insert_time = datetime.now()
        temp.id = str(uuid.uuid4())
        temp.main_id = json_dict['main_id']
        temp.surface_id = json_dict['surface_id']
        temp.camera_id = json_dict['camera_id']
        temp.flow_id = json_dict['flow_id']
        temp.image_id = str(json_dict['id'])
        return temp

    def set_parm_by_json_dict(self, json_dict):
        self.id = str(uuid.uuid4())
        self.insert_time = datetime.now()
        self.main_id = json_dict['main_id']
        self.surface_id = json_dict['surface_id']
        self.camera_id = json_dict['camera_id']
        self.flow_id = json_dict['flow_id']
        
        import random
        # 生成深度
        self.real_depth = round(random.uniform(1, 2),2)
        if self.type in [3,17]:
            self.real_depth = round(random.uniform(0.5, 1.5),2)
        elif self.type in [15]:
            self.real_depth = round(random.uniform(15, 20),2)
        elif self.type in [0,11,6,13,16,14]:
            self.real_depth = round(random.uniform(3, 5),2)
        elif self.type in [7]:
            self.real_depth = round(random.uniform(1, 2),2)
        else:
            self.real_depth = round(random.uniform(1, 2),2)
        # todo 更新image2、image3的id
        #self.image_id = str(json_dict['image_id'])
        self.image_id = str(json_dict['image_id'])
        if "image2_id" in json_dict.keys():
            self.image2_id = str(json_dict['image2_id'])
        if "image3_id" in json_dict.keys():
            self.image3_id = str(json_dict['image3_id'])
        if "image4_id" in json_dict.keys():
            self.image4_id = str(json_dict['image4_id'])

    def set_parm_by_es(self, es_defect):
        self.id = es_defect['id']
        self.main_id = es_defect['main_id']
        self.type = es_defect['type']
        self.steel_defect_id = es_defect['steel_defect_id']
        self.x = es_defect['x']
        self.y = es_defect['y']
        self.w = es_defect['w']
        self.h = es_defect['h']
        self.real_x = es_defect['real_x']
        self.real_y = es_defect['real_y']
        self.real_w = es_defect['real_w']
        self.real_h = es_defect['real_h']
        self.surface_id = es_defect['surface_id']
        self.camera_id = es_defect['camera_id']
        self.insert_time = es_defect['insert_time']
        self.crop_x = es_defect['crop_x']
        self.crop_y = es_defect['crop_y']
        self.crop_w = es_defect['crop_w']
        self.crop_h = es_defect['crop_h']
        self.flow_id = es_defect['flow_id']
        self.confidence = es_defect['confidence']
        self.grade = es_defect['grade']
        self.is_visualize = es_defect['is_visualize']
        self.is_user_delete = es_defect['is_user_delete']
        self.image_id = es_defect['image_id']
        self.image2_id = es_defect['image2_id']
        self.image3_id = es_defect['image3_id']
        self.image4_id = es_defect['image4_id']
        self.crop_image_url = es_defect['crop_image_url']
        self.crop_image2_url = es_defect['crop_image2_url']
        self.crop_image3_url = es_defect['crop_image3_url']
        self.crop_image4_url = es_defect['crop_image4_url']
        self.other0 = es_defect['other0']
        self.other1 = es_defect['other1']
        # 额外新增 插入数据库删掉即可
        self._id = es_defect['_id']

    # 得到评级信息
    def set_grade_from_conclusion(self, cfg_runner, appraise_typeid, appraise_condition):
        if appraise_condition == cfg_runner['Conclusion']['appraise_condition'][0]:
            grade, loss = appraise_typeid.get_grade_loss(appraise_condition, self.real_h)
            self.grade = grade.name
        elif appraise_condition == cfg_runner['Conclusion']['appraise_condition'][1]:
            grade, loss = appraise_typeid.get_grade_loss(appraise_condition, self.real_w * self.real_h)
            self.grade = grade.name
        elif appraise_condition == cfg_runner['Conclusion']['appraise_condition'][2]:
            grade, loss = appraise_typeid.get_grade_loss(appraise_condition, self.period_num)
            self.grade = grade.name
       

class SteelDefect:
    # 钢材缺陷
    def __init__(self):
        self.grade = ''
        self.id = ''
        self.image_defect_ids_text = ''
        self.confidence = 0
        self.real_x = 0
        self.real_y = 0
        self.real_w = 0
        self.real_h = 0
        self.top_distance = 0
        self.main_id = 0
        self.surface_id = 0
        self.type = 0
        self.is_visualize = True
        self.is_user_delete = False
        self.insert_time = ''
        self.is_repeat = 0
        self.repeat_id = ''
        self.panorama_id = ''
        self.panorama_x = 0
        self.panorama_y = 0
        self.panorama_w = 0
        self.panorama_h = 0
        self.real_size = 0
        self.real_depth = 0
        self.volume_url = ''
        self.other0 = ''
        self.other1 = ''

        # 额外新增 插入数据库删掉即可
        self.period_num = 0
        self.loss = 0
        self.grade_dhk1 = ''
        self.grade_dhk2 = ''
        self.area_rate = 0

    def get_dict(self):
        temp_dict = vars(self)
        temp_dict.pop('period_num',None)
        temp_dict.pop('loss',None)
        temp_dict.pop('grade_dhk1',None)
        temp_dict.pop('grade_dhk2',None)
        #temp_dict.pop('area_rate',None)
        return temp_dict

    def set_grade_loss_from_conclusion(self, cfg_runner, appraise_typeid, appraise_condition):
        if appraise_condition == cfg_runner['Conclusion']['appraise_condition'][0]:
            grade_dhk1, self.loss = appraise_typeid.get_grade_loss(appraise_condition, self.top_distance)
            self.grade_dhk1 = grade_dhk1.name
        elif appraise_condition == cfg_runner['Conclusion']['appraise_condition'][1]:
            grade_dhk2, self.loss = appraise_typeid.get_grade_loss(appraise_condition, self.real_depth)
            self.grade_dhk2 = grade_dhk2.name
        elif appraise_condition == cfg_runner['Conclusion']['appraise_condition'][2]:
            grade_dhk2, self.loss = appraise_typeid.get_grade_loss(appraise_condition, self.real_depth)
            self.grade_dhk2 = grade_dhk2.name
        elif appraise_condition == cfg_runner['Conclusion']['appraise_condition'][3]:
            grade, self.loss = appraise_typeid.get_grade_loss(appraise_condition, self.area_rate)
            self.grade = grade.name
        elif appraise_condition == cfg_runner['Conclusion']['appraise_condition'][4]:
            grade, self.loss = appraise_typeid.get_grade_loss(appraise_condition, self.area_rate)
            self.grade = grade.name
        elif appraise_condition == cfg_runner['Conclusion']['appraise_condition'][5]:
            grade, self.loss = appraise_typeid.get_grade_loss(appraise_condition, self.real_depth)
            self.grade = grade.name
        elif appraise_condition == cfg_runner['Conclusion']['appraise_condition'][6]:
            grade, self.loss = appraise_typeid.get_grade_loss(appraise_condition, self.real_size)
            self.grade = grade.name
        else:
            self.grade = '错误'
            self.loss = 0
        
    def contact_grade_loss_dhk(self,appraise_typeid):
        if self.grade_dhk1 =="报警" or self.grade_dhk2=="报警":
            self.grade = "报警"
            self.loss = appraise_typeid.loss_rule_list[0]['alarm_loss']
        elif self.grade_dhk1 =="疑似" and self.grade_dhk2=="疑似":
            self.grade = "疑似"
            self.loss = appraise_typeid.loss_rule_list[0]['loss']
        else:
            self.grade = "警告"
            self.loss = appraise_typeid.loss_rule_list[0]['warning_loss']

    @staticmethod
    def create_new_defect(json_dict):
        temp = SteelDefect()
        temp.insert_time = datetime.now()
        temp.id = str(uuid.uuid4())
        temp.main_id = json_dict['main_id']
        temp.surface_id = json_dict['surface_id']
        return temp

    def set_parm_by_json_dict(self, json_dict):
        self.id = str(uuid.uuid4())
        self.insert_time = datetime.now()
        self.main_id = json_dict['main_id']
        self.surface_id = json_dict['surface_id']

    def set_rongyu_parm_by_image_defect(self, image_defect):
        self.id = str(uuid.uuid4())
        self.image_defect_ids_text = image_defect.id
        self.confidence = image_defect.confidence
        self.real_x = image_defect.real_x
        self.real_y = image_defect.real_y
        self.real_w = image_defect.real_w
        self.real_h = image_defect.real_h
        self.main_id = image_defect.main_id
        self.surface_id = image_defect.surface_id
        self.real_depth = image_defect.real_depth
        self.type = image_defect.type
        self.insert_time = datetime.now()
        self.real_size = round(self.real_w * self.real_h, 2)

    def set_parm_by_merge_defect(self, cfg_runner, merge_defect,camera_id,gg='default'):
        from MyObject.Steel import Steel
        self.id = str(uuid.uuid4())
        self.image_defect_ids_text = merge_defect['image_defect_ids_text']
        self.confidence = merge_defect['confidence']

        min_real_x = min(merge_defect['img_defect'], key=lambda d: d.get('real_x',  float('inf')))['real_x']
        min_real_y = min(merge_defect['img_defect'], key=lambda d: d.get('real_y',  float('inf')))['real_y']
        
        self.real_x = min_real_x
        self.real_y = min_real_y
        self.real_w = Steel.transform_length(cfg_runner, merge_defect['w'],need_y=False, gg=gg)
        self.real_h = Steel.transform_length(cfg_runner, merge_defect['h'],need_y=True, gg=gg)
        self.real_size = round(self.real_w * self.real_h, 2)
        import random
        # 生成深度
        self.real_depth = round(random.uniform(0.5, 1.5),2)

        self.panorama_x = merge_defect['x'] + cfg_runner['CameraOffset'][camera_id]['other_offset'][0]
        self.panorama_y = int(min_real_y / cfg_runner['Image']['rate_pixel2real_y'][gg]) 
        self.panorama_w = merge_defect['w']
        self.panorama_h = merge_defect['h']
        self.insert_time = datetime.now()
        # 更新图像缺陷
        
        
    #评级中other缺陷

    #评级中other缺陷
    def set_parm_by_area_defect(self, cfg_runner, area_defect,gg='default'):
        from MyObject.Steel import Steel
        self.id = str(uuid.uuid4())
        self.image_defect_ids_text = area_defect['id']
        self.confidence = area_defect['confidence']

        # 根据图像缺陷深度写入钢材缺陷深度
        self.real_depth = area_defect['real_depth']

        self.panorama_x = area_defect['x'] + cfg_runner['CameraOffset'][area_defect['camera_id']]['other_offset'][0]
        self.panorama_y = int(area_defect['real_y'] / cfg_runner['Image']['rate_pixel2real_y'][gg]) 
        self.panorama_w = area_defect['w']
        self.panorama_h = area_defect['h']
        #实际钢材缺陷信息与图像缺陷信息一致 注意x是图像左边界，real_x是钢材左边界
        self.real_x = area_defect['real_x']
        self.real_y = area_defect['real_y']
        self.real_w = area_defect['real_w']
        self.real_h = area_defect['real_h']
        self.real_size = round(self.real_w * self.real_h, 2)
        self.insert_time = datetime.now()
        self.main_id = area_defect['main_id']
        self.surface_id = area_defect['surface_id']
        self.type = area_defect['type']

    def set_parm_by_dhk_defect(self, cfg_runner, dhk_defect,gg='default'):
        from MyObject.Steel import Steel
        self.id = str(uuid.uuid4())
        self.confidence = dhk_defect['confidence']
        self.panorama_x = dhk_defect['x'] + cfg_runner['CameraOffset'][dhk_defect['camera_id']]['other_offset'][0]
        self.panorama_y = int(dhk_defect['real_y'] / cfg_runner['Image']['rate_pixel2real_y'][gg]) 
        self.panorama_w = dhk_defect['w']
        self.panorama_h = dhk_defect['h']

        import random
        # 随机生成到头部的距离
        self.top_distance = random.randint(40, 55)
        self.real_depth = round(random.uniform(15, 20),2)
        #实际钢材缺陷信息与图像缺陷信息一致 注意x是图像左边界，real_x是钢材左边界
        self.real_x = dhk_defect['real_x']
        self.real_y = dhk_defect['real_y']
        self.real_w = dhk_defect['real_w']
        self.real_h = dhk_defect['real_h']
        self.real_size = round(self.real_w * self.real_h, 2)
        self.insert_time = datetime.now()
        self.main_id = dhk_defect['main_id']
        self.surface_id = dhk_defect['surface_id']
        self.type = dhk_defect['type']

    def set_parm_by_lq_defect(self, cfg_runner, lq_defect,gg='default'):
        from MyObject.Steel import Steel
        self.id = str(uuid.uuid4())
        self.confidence = lq_defect['confidence']
        self.panorama_x = lq_defect['x'] + cfg_runner['CameraOffset'][lq_defect['camera_id']]['other_offset'][0]
        self.panorama_y = int(lq_defect['real_y'] / cfg_runner['Image']['rate_pixel2real_y'][gg]) 
        self.panorama_w = lq_defect['w']
        self.panorama_h = lq_defect['h']
        import random
        # 随机生成漏清率、深度
        self.real_depth = round(random.uniform(3, 5),2)

        #实际钢材缺陷信息与图像缺陷信息一致 注意x是图像左边界，real_x是钢材左边界
        self.real_x = lq_defect['real_x']
        self.real_y = lq_defect['real_y']
        self.real_w = lq_defect['real_w']
        self.real_h = lq_defect['real_h']
        self.real_size = round(self.real_w * self.real_h, 2)
        self.insert_time = datetime.now()
        self.main_id = lq_defect['main_id']
        self.surface_id = lq_defect['surface_id']
        self.type = lq_defect['type']

    def set_parm_by_depth_defect(self, cfg_runner, depth_defect,gg='default'):
        from MyObject.Steel import Steel
        self.id = str(uuid.uuid4())
        self.image_defect_ids_text = depth_defect['id']
        self.confidence = depth_defect['confidence']
        self.panorama_x = depth_defect['x'] + cfg_runner['CameraOffset'][depth_defect['camera_id']]['other_offset'][0]
        self.panorama_y = int(depth_defect['real_y'] / cfg_runner['Image']['rate_pixel2real_y'][gg]) 
        self.panorama_w = depth_defect['w']
        self.panorama_h = depth_defect['h']
        
        # 根据图像缺陷深度写入钢材缺陷深度
        self.real_depth = depth_defect['real_depth']

        #实际钢材缺陷信息与图像缺陷信息一致 注意x是图像左边界，real_x是钢材左边界
        self.real_x = depth_defect['real_x']
        self.real_y = depth_defect['real_y']
        self.real_w = depth_defect['real_w']
        self.real_h = depth_defect['real_h']
        self.real_size = round(self.real_w * self.real_h, 2)
        self.insert_time = datetime.now()
        self.main_id = depth_defect['main_id']
        self.surface_id = depth_defect['surface_id']
        self.type = depth_defect['type']



if __name__ == '__main__':
    a = SteelDefect()
    b = a.to_dict()
    print(b)
