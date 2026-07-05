import os
import json
import shutil

import numpy as np

# from UtilObject.AggregationUtil import Aggregation
from magang_infer.UtilObject.AggregationUtil import Aggregation


def one_pic_defect_aggregation( one_pic_defect_list,aggregation):
    # 以前的聚合代码用的数据格式是从es数据库里读出来的，最初源头是database.get_defects_by_main_id，得到的结构是一种json格式
    # 现在的小图聚合大图，用的是one_pic_defect_list，且是在大图中的位置，如下 x1, y1, x2, y2, conf, class_id
    # 进行聚合前，现根据类型分组
    # 聚合 要x方向y方向都聚合
    merge_defect_list = []

    one_pic_defect_type_dict = {}

    for batch_defect in one_pic_defect_list:
        try:
            # 根据缺陷类型分类，放入batch_defect_type_dict
            class_id = int(batch_defect[5])
            if class_id not in one_pic_defect_type_dict.keys():
                one_pic_defect_type_dict[class_id] = []
            one_pic_defect_type_dict[class_id].append(batch_defect)
        except Exception as e:
            print('batch_defect_type_dict error')
            print('batch_defect_type_dict' + str(batch_defect))

    for class_id, type_defects in one_pic_defect_type_dict.items():
        # 遍历这一张大图中 所有的缺陷（按照缺陷类型进行遍历）
        y_grouping_space = 0.3
        x_grouping_space = 4096
        s_threshold = 0.5
        y_error = (y_grouping_space * 1000) / 0.17544  # 2m为纵向间隔
        y_error = 4096
        # 聚合每个类
        type_merge_defect_list = aggregation.one_pic_target_types_defect_merge(type_defects,
                                                                                    class_id,
                                                                                    s_threshold=s_threshold,
                                                                                    x_error=x_grouping_space,
                                                                                    y_error=y_error)
        # 把每个类的都加进来
        merge_defect_list.extend(type_merge_defect_list)
    return merge_defect_list

def convert_json2list(json_path):
    # 将json文件转为list
    one_pic_defect_list = []
    with open(json_path, "r", encoding='utf-8') as json_path:
        jsonx = json.load(json_path)
        width = int(jsonx["imageWidth"])  # 原图的宽
        height = int(jsonx["imageHeight"])  # 原图的高
        for shape in jsonx["shapes"]:
            obj_cls = int(shape["label"])  # 获取类别
            points = np.array(shape["points"])  # 获取(x1,y1,x2,y2)
            x1 = int(points[0][0])
            y1 = int(points[0][1])
            x2 = int(points[1][0])
            y2 = int(points[1][1])
            box = [x1,y1,x2,y2,1,obj_cls]
            one_pic_defect_list.append(box)
    return one_pic_defect_list

def convert_list2json(one_pic_defect_list,json_path_copy):
    # 创建LabelMe格式的JSON数据结构
    labelme_data = {
        "version": "5.1.1",
        "flags": {},
        "shapes": [],
        "imagePath": "2_2_copy.jpg",
        "imageData": None,
        "imageHeight": 2048,
        "imageWidth": 4096,
    }
    for box in one_pic_defect_list:
        x1 = box[0]
        y1 = box[1]
        x2 = box[2]
        y2 = box[3]
        # 构建LabelMe格式的标注
        labelme_shape = {
            "label": str(box[5]),
            "points": [
                [x1, y1],
                [x2, y2]
            ],
            "group_id": None,
            "shape_type": "rectangle",
            "flags": {}
        }
        labelme_data["shapes"].append(labelme_shape)
        # print('写入成功')
    with open(json_path_copy, 'w') as json_file:
        json.dump(labelme_data, json_file, indent=1)



if __name__ == '__main__':
    aggregation = Aggregation()
    json_path = r'E:\File\historyfile\File\gitee\SteelDefectDetection-magang\SteelDefectDetection-magang\magang_infer\Test\2_2.json'
    json_path_copy = r'E:\File\historyfile\File\gitee\SteelDefectDetection-magang\SteelDefectDetection-magang\magang_infer\Test\2_2_copy.json'
    one_pic_defect_list = convert_json2list(json_path)
    print("聚合前",len(one_pic_defect_list))
    one_pic_defect_list = one_pic_defect_aggregation(one_pic_defect_list,aggregation)
    print("聚合后",len(one_pic_defect_list))
    convert_list2json(one_pic_defect_list,json_path_copy)

