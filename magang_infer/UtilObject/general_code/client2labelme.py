from collections import defaultdict
import copy
import json
import os
import shutil



camera_dict = {
    '1': defaultdict(list),
    '2': defaultdict(list),
    '3': defaultdict(list),
    '4': defaultdict(list),
    '5': defaultdict(list),
    '6': defaultdict(list),
}
LABEL_STR = {
    '0': 'ak',
    '1': 'ez',
    '2': 'lw',
    '5': 'hs',
    '6': 'yh',
    '13': 'zd',
    '17': 'qp',
    '20': '20',
    '21': 'akys',
    '22': 'hsys',
    '23': 'yhtp_hk',
    '24': 'yhtp_ht',
    '25': 'yhtp_bk',
    '26': 'yhtp_bt',
    '27': 'qt0',
    '29': 'ak_wj'
}
JSON_TEMP = '''
{
  "version": "5.0.1",
  "flags": {},
  "shapes": [
    {
      "label": "hs",
      "points": [
        [
          537.0481927710842,
          330.72289156626505
        ],
        [
          594.2771084337348,
          370.48192771084337
        ]
      ],
      "group_id": null,
      "shape_type": "rectangle",
      "flags": {},
      "confidence":0,
      "is_user_delete":""
    }
  ],
  "imagePath": "X52210272001_002_data_1296.png",
  "imageData": null,
  "imageHeight": 800,
  "imageWidth": 992
}
'''


# 导出函数，传入参数为图像表json文件images_json_path，缺陷表json文件defects_json_path，文件要保存的路径save_dir
def export_label(images_json_path, defects_json_path, save_dir):
    defect_logs = []
    image_logs = []
    # 获取image表数据以及defect表数据
    with open(defects_json_path, 'r', encoding='utf-8') as defect_file:
        defect_data = json.load(defect_file)
        defect_file.close()
    with open(images_json_path, 'r', encoding='utf-8') as image_file:
        image_data = json.load(image_file)
        image_file.close()
    for item in defect_data:
        defect_logs.append(item)
    for item in image_data:
        image_logs.append(item)
    if len(defect_logs) == 0:
        print('缺陷数为0')

    for log in defect_logs:
        try:
            image_url = log['crop_image__url']
        except:
            for item in image_logs:
                if item['id'] == log['image_id']:
                    image_url = item['image_url']
        finally:
            print("image不存在")
        print(image_url)
        diskb, server, _, date_time, camera_id, image_name = image_url.strip('\\').split('\\')
        camera_dict[camera_id][image_name].append(log)
    tjson = json.loads(JSON_TEMP)
    tshape = tjson['shapes'][0]
    tjson['shapes'].clear()
    tshape['points'].clear()
    for camera_id, image_defects in camera_dict.items():
        for image_name, defects in image_defects.items():

            shape_list = []
            for log in defects:

                save_dir1 = save_dir
                try:
                    image_url = log['crop_image__url']
                except:
                    for item in image_logs:
                        if item['id'] == log['image_id']:
                            image_url = item['image_url']
                            image_Height, image_Width = item['height'], item['width']
                finally:
                    print("image 不存在")

                # diskb, server, _,camera_id, date_time, a, b = image_url.strip('\\').split('\\')
                diskb, server, _, date_time, camera_id, imagename = image_url.strip('\\').split('\\')

                oneshape = copy.deepcopy(tshape)
                # 将xywh转换为x1,y1,x2,y2
                x1 = float(log['x'])
                y1 = float(log['y'])
                x2 = float(log['x']) + float(log['w'])
                y2 = float(log['y']) + float(log['h'])
                oneshape['points'].append([x1, y1])
                oneshape['points'].append([x2, y2])
                oneshape['label'] = LABEL_STR[str(log['type'])]
                oneshape['confidence'] = log['confidence']
                oneshape['is_user_delete'] = log['is_user_delete']
                shape_list.append(oneshape)
                json_file = os.path.join(save_dir1, image_name.replace('jpg', 'json'))

                onedict = copy.deepcopy(tjson)
                onedict['imagePath'] = image_name
                onedict['shapes'] = shape_list

                with open(json_file, 'w', encoding='utf8') as f:
                    json.dump(onedict, f, separators=(',', ': '), indent=4)

            onedict = copy.deepcopy(tjson)
            onedict['imagePath'] = image_name
            onedict['shapes'] = shape_list
            onedict['imageHeight'] = image_Height
            onedict['imageWidth'] = image_Width

            img_file = os.path.join(save_dir1, image_name)
            json_file = os.path.join(save_dir1, image_name.replace('jpg', 'json'))

            with open(json_file, 'w', encoding='utf8') as f:
                json.dump(onedict, f, separators=(',', ': '), indent=4)


if __name__ == "__main__":
    images_json_path = r"C:\Users\12247\Desktop\20240331074755 (2)\image.json"
    defects_json_path = r"C:\Users\12247\Desktop\20240331074755 (2)\defect.json"
    save_dir = r'D:\毕业设计\解析'
    export_label(images_json_path, defects_json_path, save_dir)