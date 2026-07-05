from deepdiff import DeepDiff
import os
import json
import re
import shutil

# TP(Truth Positive)：预测对的正类，我说他对，而且他本来也是对的
# TN(Truth Negative)：预测对的负类，我说他错，而且他本来也是错的
# FP(False Positive)：预测错的正类，我说他对，但是他错了
# FN(False Negative)：预测错的负类，我说他错，但是他是对的


# False Positive(简称FP)：判断为正，但是判断错了。（实际为负）
# False Negative(简称FN)：判断为负，但是判断错了。（实际为正）
# True Positive(简称TP)：判断为正，且实际为正。
# True Negative(简称TN)：判断未负，且实际为负。

# Precision (准确率 / 精确率)：准确率是模型只找到相关目标的能力，等于TP/(TP+FP)。即模型给出的所有预测结果中命中真实目标的比例。
# Recall (召回率)：召回率是模型找到所有相关目标的能力，等于TP/(TP+FN)。即模型给出的预测结果最多能覆盖多少真实目标。

#一般来说，对于多分类目标检测的任务，会分别计算每个类别的TP、FP、FN数量，进一步计算每个类别的Precision、Recall。


def jsondiff(path_json1,path_json2):
    #json对比函数，主要调用deepdiff库实现
    f1 = open(path_json1, "r", encoding='utf-8')
    json1=json.load(f1)

    if path_json2 == "delete":
        json2 = {}
    else:
        f2 = open(path_json2, "r", encoding='utf-8')
        json2=json.load(f2)


    print(path_json1)
    print(path_json2)
    result = DeepDiff(json1,json2,exclude_types={str,int}).pretty()
    print(DeepDiff(json1,json2,exclude_types={str,int}).pretty())
    # print(result)


    #没有推理出来的，标注公司新加的部分，为FN
    sub = "added"
    a1 = result.count(sub)
    #内容修改，标注框位置不对，为FN
    #使用正则表达式匹配Value of root['shapes'][1]['points'][1][1] changed from 698.0 to 431.0593.中shape与points之间的东西加一
    reg = re.findall(r'shapes\']\[(.*)\]\[\'points', result)
    #print("reg",reg)
    print("reg:",reg)
    #print(type(reg))
    a2 = 0
    if reg:
        max_value = max(reg)
        a2 = int(max_value)+1
    print("result.count(FN) : ",a1+a2)
    #推理出来错误的，标注公司删掉的部分，为FP
    sub = "root['shapes'] removed"
    b = result.count(sub)
    print("result.count(FP) : ", b)
    #统计总的推理结果，即TP+FP
    print(json1['shapes'])
    c = len(json1['shapes'])
    print("TP+FP:",c)
    #推理出来，没有改变，为TP
    d = c-b
    print("TP:",d)
    #FN  FP  TP+FP  TP
    return a1+a2, b, c, d



if __name__ == "__main__":
    # old_json = r"E:\File\historyfile\File\pycharmproject\Steeldetection\mgDataProcess\difftest\example\old\list\\"
    # new_json = r"E:\File\historyfile\File\pycharmproject\Steeldetection\mgDataProcess\difftest\example\new\list\\"

    old_json = r"F:\南铝标注\训练数据\开始微调用[新数据]\3-1~3-7厂人员标注（已裁剪）\a\\"
    new_json = r"F:\南铝标注\训练数据\开始微调用[新数据]\3-1~3-7厂人员标注（已裁剪）\a1\\"
    #新的json文件目录，与旧的json文件目录

    list_old_json = os.listdir(old_json)
    list_new_json = os.listdir(new_json)

    #定义计算数据,计算结果P、R
    TP = 0
    TN = 0
    FP = 0
    FN = 0
    P = 0
    R = 0


    for cnt, json_name in enumerate(list_old_json):
        if not json_name.endswith('.json'):
            # shutil.copy(dir_json + json_name, dir_jpg)
            continue
        path_old_json = old_json + json_name
        path_new_json = new_json + json_name
        if not os.path.exists(path_new_json):
            print(path_new_json," not exit")
            path_new_json = "delete"
        # FN  FP  TP+FP  TP
        a,b,c,d = jsondiff(path_old_json, path_new_json)
        FN = FN + a
        FP = FP + b
        TP = TP + d
        #jsondiff(path_old_json, path_new_json)

    # Precision (准确率 / 精确率)：准确率是模型只找到相关目标的能力，等于TP/(TP+FP)。即模型给出的所有预测结果中命中真实目标的比例。
    # Recall (召回率)：召回率是模型找到所有相关目标的能力，等于TP/(TP+FN)。即模型给出的预测结果最多能覆盖多少真实目标。
    P = TP/(TP+FP)
    R = TP/(TP+FN)
    print("TP:", TP)
    print("FP:", FP)
    print("FN:", FN)
    print("TP+FP(推理总数):", TP+FP)

    print('P: {:.2%}'.format(P))
    print('R: {:.2%}'.format(R))
