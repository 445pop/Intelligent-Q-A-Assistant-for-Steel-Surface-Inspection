import os
import json
import shutil
from pathlib import Path
import os
import numpy as np

'''
# @Time    : 2024-03-10
# @Author  : 尚善蒲
# @File    : json_diff.py
# @useage: : 钢材缺陷检测任务 算法推理结果与真值标注结果的PR统计
# 先统计真值标注结果、算法推理结果每一个类多少个
# 然后统计每类PR
# 值标注结果、算法推理结果不一样的数据——提取真值数据去训练
'''

## youban kunyin mianzhuangcashang 单独训练
## 其他缺陷单独训练
# 类和索引
# CLASSES=["沟槽", "凹坑", "起棱","擦伤","气孔","裂纹"]#灰度数据
# CLASSES = ["cashang", "qipi", "youban", "kunyin", "lw", "gc", "lvhui", 'nianshang', 'ak']  # 基于深度图的灰度数据
CLASSES = ["cashang", "huashang", 'lvhui', 'kunyin', 'nianshang', 'mianzhuangcashang', 'qipi', 'youban', 'jinshuyaru',
           'secha', "yaguohuahen"]  # 基于深度图的灰度数据
# CLASSES = ["youban", "mianzhuangcashang", 'kunyin']
# cashang_list = []
# huashang_list = []
# lvhui_list = []
# kunyin_list = []
# nianshang_list = []
# mianzhuangcashang_list = []
# qipi_list = []
# youban_list = []
# jinshuyaru_list = []
# secha_list = []
# yaguohuahen_list = []
class_num_dict = {}

for item in CLASSES:
    class_num_dict[item] = []


def convert(size, box):
    '''
    input:
    size:(width,height);
    box:(x1,x2,y1,y2)
    output:
    (x,y,w,h)
    '''
    dw = 1. / size[0]
    dh = 1. / size[1]
    x = (box[0] + box[1]) / 2.0
    y = (box[2] + box[3]) / 2.0
    w = abs(box[1] - box[0])
    h = abs(box[3] - box[2])
    x = x * dw
    w = w * dw
    y = y * dh
    h = h * dh
    return (x, y, w, h)


# json -> txt
def json2txt(path_json, path_txt):
    with open(path_json, "r", encoding='utf-8') as path_json:
        jsonx = json.load(path_json)
        width = int(jsonx["imageWidth"])  # 原图的宽
        height = int(jsonx["imageHeight"])  # 原图的高
        with open(path_txt, "w+") as ftxt:
            # 遍历每一个bbox对象
            for shape in jsonx["shapes"]:
                obj_cls = str(shape["label"])  # 获取类别
                if obj_cls == 'huahen':
                    obj_cls = 'huashang'
                elif obj_cls == 'qikong' or obj_cls == 'qp':
                    obj_cls = 'nianshang'
                elif obj_cls == 'dianhuokeng':
                    obj_cls = 'cashang'
                elif obj_cls == 'jinshuyaru':
                    obj_cls = 'jinshuyaru'

                class_num_dict[obj_cls].append(path_txt)

                cls_id = CLASSES.index(obj_cls)  # 获取类别索引
                points = np.array(shape["points"])  # 获取(x1,y1,x2,y2)
                x1 = int(points[0][0])
                y1 = int(points[0][1])
                x2 = int(points[1][0])
                y2 = int(points[1][1])
                # (左上角,右下角) -> (中心点,宽高) 归一化
                bb = convert((width, height), (x1, x2, y1, y2))
                ftxt.write(str(cls_id) + " " + " ".join([str(a) for a in bb]) + "\n")


def output():
    total_defect_num = 0
    for key in class_num_dict.keys():
        print(key, ':', len(class_num_dict[key]))
        total_defect_num += len(class_num_dict[key])
        class_num_dict[key].clear()

    print('total_num:', total_defect_num)


if __name__ == "__main__":
    # 标注人员
    # annotation_dir = r"E:\File\historyfile\File\pycharmproject\Steeldetection\mgDataProcess\difftest\example\old\list\\"
    annotation_dir = r"F:\南铝标注\训练数据\开始微调用[新数据]\3-1~3-7厂人员标注（已裁剪）\a1\\"
    # annotation_dir = r"E:\File\historyfile\File\pycharmproject\Steeldetection\mgDataProcess\difftest\example\oneold\\"

    # 算法
    # prediction_dir = r"E:\File\historyfile\File\pycharmproject\Steeldetection\mgDataProcess\difftest\example\new\list\\"
    prediction_dir = r"F:\南铝标注\训练数据\开始微调用[新数据]\3-1~3-7厂人员标注（已裁剪）\a\\"
    # prediction_dir = r"E:\File\historyfile\File\pycharmproject\Steeldetection\mgDataProcess\difftest\example\onenew\\"

    # 最终需要训练的文件目录  如果一个文件中，有标注结果和检出结果有不同，说明推理还有缺陷，要把图片放进模型继续训练。
    output_dir = r"F:\南铝标注\训练数据\开始微调用[新数据]\3-1~3-7厂人员标注（已裁剪）\o1\\"
    jsonfile_num = 0
    # 得到所有json文件
    list_json = os.listdir(annotation_dir)
    # print(list_json)
    # 遍历每一个json文件,转成txt文件
    for cnt, json_name in enumerate(list_json):
        if not json_name.endswith('.json'):
            # print(json_name)
            # shutil.copy(annotation_dir + json_name, dir_jpg)
            continue
        jsonfile_num += 1
        # print("算法端检出结果jsonfile_num=%d,name=%s" % (jsonfile_num, json_name))
        path_json = annotation_dir + json_name
        path_txt = annotation_dir + json_name.replace(".json", ".txt")
        # (x1,y1,x2,y2)->(x,y,w,h)
        json2txt(path_json, path_txt)
    print("算法端检出结果统计")
    output()

    jsonfile_num = 0
    # 得到所有json文件
    list_json = os.listdir(prediction_dir)
    # print(list_json)
    # 遍历每一个json文件,转成txt文件
    for cnt, json_name in enumerate(list_json):
        if not json_name.endswith('.json'):
            # print(json_name)
            # shutil.copy(prediction_dir + json_name, dir_jpg)
            continue
        jsonfile_num += 1
        # print("算法端检出结果jsonfile_num=%d,name=%s" % (jsonfile_num, json_name))
        path_json = prediction_dir + json_name
        path_txt = prediction_dir + json_name.replace(".json", ".txt")
        # (x1,y1,x2,y2)->(x,y,w,h)
        json2txt(path_json, path_txt)
    print("标注结果统计")
    output()
    # 获得路径、文件名
    ann_files = Path(annotation_dir).glob('.txt')
    pre_files = Path(prediction_dir).glob('.txt')

    list_ann_txt = os.listdir(annotation_dir)
    list_pre_txt = os.listdir(prediction_dir)

    annotation = {}
    prediction = {}

    CONF_THRE = 0.5  # 置信度阈值
    IOU_THRE = 0.9  # iou阈值
    # 遍历标注文件 将每一个标注对象（标注框）记录下来放入一个dict
    for cnt, ann_txt_name in enumerate(list_ann_txt):
        if not ann_txt_name.endswith('.txt'):
            continue
        annotation[Path(ann_txt_name).name] = []
        path_ann_name = annotation_dir + ann_txt_name
        with open(path_ann_name, 'r') as fin:
            for line in fin:
                line_list = line.split()
                x_min = float(line_list[1]) - float(line_list[3]) / 2
                y_min = float(line_list[2]) - float(line_list[4]) / 2
                x_max = float(line_list[1]) + float(line_list[3]) / 2
                y_max = float(line_list[2]) + float(line_list[4]) / 2
                obj = [x_min, y_min, x_max, y_max, int(line_list[0])]  # x_min, y_min, x_max, y_max, annotation_class_id
                annotation[Path(ann_txt_name).name].append(obj)
    # 遍历推理文件 将每一个标注对象（标注框）记录下来放入一个dict
    for cnt, pre_txt_name in enumerate(list_pre_txt):
        if not pre_txt_name.endswith('.txt'):
            continue
        prediction[Path(pre_txt_name).name] = []
        path_pre_name = prediction_dir + pre_txt_name
        with open(path_pre_name, 'r') as fin:
            for line in fin:
                line_list = line.split()
                # print(line_list)
                x_min = float(line_list[1]) - float(line_list[3]) / 2
                y_min = float(line_list[2]) - float(line_list[4]) / 2
                x_max = float(line_list[1]) + float(line_list[3]) / 2
                y_max = float(line_list[2]) + float(line_list[4]) / 2
                obj = [x_min, y_min, x_max, y_max, int(line_list[0])]  # x_min, y_min, x_max, y_max, prediction_class_id
                prediction[Path(pre_txt_name).name].append(obj)


    def calculate_iou(rect1, rect2):
        # 计算iou的函数——用于对比，如果IOU=1，则说明标注与推理的结果没变，证明推理正确
        overlap_x1 = max(rect1[0], rect2[0])
        overlap_y1 = max(rect1[1], rect2[1])
        overlap_x2 = min(rect1[2], rect2[2])
        overlap_y2 = min(rect1[3], rect2[3])
        if overlap_x2 - overlap_x1 <= 0 or overlap_y2 - overlap_y1 <= 0:
            return 0
        iou_area = (overlap_x2 - overlap_x1) * (overlap_y2 - overlap_y1)
        union_area = (rect1[2] - rect1[0]) * (rect1[3] - rect1[1]) + (rect2[2] - rect2[0]) * (
                rect2[3] - rect2[1]) - iou_area
        return float(iou_area) / union_area


    # 定义推理的类别
    # CLASSES = ["cashang", "huashang", 'lvhui', 'kunyin', 'nianshang', 'mianzhuangcashang', 'qipi', 'youban', 'jinshuyaru']
    l = len(CLASSES)
    correct_obj_num = 0
    prediction_obj_num = 0
    annotation_obj_num = 0
    annotation_obj_num_temp = [0] * l
    prediction_obj_num_temp = [0] * l
    correct_obj_num_temp = [0] * l
    p_temp = [0] * l
    r_temp = [0] * l

    train_list = []

    #  这部分改为以old predict 为遍历list，寻找new annoation
    # for key, value in annotation.items():
    #     for cnt,i in enumerate(value):
    #         # 获取当前类别
    #         cls = value[cnt][4]
    #         annotation_obj_num_temp[cls] += 1
    #     annotation_obj_num += len(value)
    #     if key in prediction:
    #         prediction_value = prediction[key]
    #         for cnt,i in enumerate(prediction_value):
    #             # 获取当前类别
    #             cls = prediction_value[cnt][4]
    #             prediction_obj_num_temp[cls] += 1
    #         prediction_obj_num += len(prediction_value)
    #         for i in range(len(prediction_value)):
    #             for j in range(len(value)):
    #                 iou = calculate_iou(prediction_value[i], value[j])
    #                 if iou >= IOU_THRE and prediction_value[i][4] == value[j][4]:
    #                     correct_obj_num += 1
    #                     break

    # 以预测结果为目录遍历，遍历每一个预测结果文件，然后遍历文件内每一个标注对象，对照同名文件的标注结果文件，在文件内遍历所有标注对象，进行对比，如果相同则说明预测正确
    for key, value in prediction.items():
        # 遍历list内每一个文件
        for cnt, i in enumerate(value):
            # 遍历文件内每一个对象
            # 获取当前类别
            cls = value[cnt][4]
            prediction_obj_num_temp[cls] += 1
        prediction_obj_num += len(value)
        if key in annotation:
            annotation_value = annotation[key]
            key_correct_obj_num = 0
            for cnt, i in enumerate(annotation_value):
                # 获取当前类别
                cls = annotation_value[cnt][4]
                annotation_obj_num_temp[cls] += 1
            annotation_obj_num += len(annotation_value)
            for i in range(len(annotation_value)):
                cls = annotation_value[i][4]
                for j in range(len(value)):
                    # iou = calculate_iou(annotation_value[i], value[j])
                    iou = calculate_iou(value[j], annotation_value[i])
                    if iou >= IOU_THRE and annotation_value[i][4] == value[j][4]:
                        correct_obj_num += 1
                        key_correct_obj_num += 1
                        correct_obj_num_temp[cls] += 1
                        break
            if key_correct_obj_num != annotation_obj_num:
                train_list.append(key)

    for key in train_list:
        # 将train_list里的内容复制到output文件夹
        img_file_jpg = key.replace(".txt", ".jpg")
        img_file_png = key.replace(".txt", ".png")
        src_img_jpg = os.path.join(annotation_dir, img_file_jpg)
        src_img_png = os.path.join(annotation_dir, img_file_png)
        if os.path.exists(src_img_jpg):
            src_img = src_img_jpg
            img_file = img_file_jpg
        if os.path.exists(src_img_png):
            src_img = src_img_png
            img_file = img_file_png
        src_txt = os.path.join(annotation_dir, key)
        if not os.path.exists(src_img):
            continue
        if not os.path.exists(src_txt):
            continue
        dst_img = os.path.join(output_dir, img_file)
        dst_txt = os.path.join(output_dir, key)
        shutil.copy(src_img, dst_img)
        shutil.copy(src_txt, dst_txt)
        # print(key)
        # print(img_file)

    print("correct_obj_num", correct_obj_num)
    print("prediction_obj_num", prediction_obj_num)
    print("annotation_obj_num", annotation_obj_num)
    print("train_list", train_list)
    print("train_list length", len(train_list))

    P = 0
    R = 0
    # 小数点保留两位
    if prediction_obj_num != 0:
        P = float(correct_obj_num) / prediction_obj_num
        P = int(P * 1000) / 1000
    if annotation_obj_num != 0:
        R = float(correct_obj_num) / annotation_obj_num
        R = int(R * 1000) / 1000

    from prettytable import *

    # 下面是打印表格
    for i in range(l):
        if prediction_obj_num_temp[i] == 0:
            # print("class",CLASSES[i],"检出结果为0")
            continue
        if annotation_obj_num_temp[i] == 0:
            # print("class",CLASSES[i],"标注结果为0")
            continue
        p_temp[i] = float(correct_obj_num_temp[i]) / prediction_obj_num_temp[i]
        r_temp[i] = float(correct_obj_num_temp[i]) / annotation_obj_num_temp[i]
        p_temp[i] = int(p_temp[i] * 1000) / 1000
        r_temp[i] = int(r_temp[i] * 1000) / 1000
        # print(CLASSES[i],'Precision ratio: ', p_temp[i])
        # print(CLASSES[i],'Recall ratio: ', r_temp[i])

    table = PrettyTable(['类别', '推理总数', '标注总数', '推理正确数量', 'P', 'R'])
    table.border = True

    for i in range(l):
        table.add_row(
            [CLASSES[i], prediction_obj_num_temp[i], annotation_obj_num_temp[i], correct_obj_num_temp[i], p_temp[i],
             r_temp[i]])
    table.add_row(['all', prediction_obj_num, annotation_obj_num, correct_obj_num, P, R])
    print(table)
