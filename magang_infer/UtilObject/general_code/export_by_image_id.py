# 根据图像号导出某张图像及其缺陷(包括用户修改的)
from MyObject.ProjectConfig import MySettings
from UtilObject.DatabaseUtil import MyDatabase
from collections import defaultdict
import json
import copy
import os
from tqdm import tqdm
import shutil
import logging

JSON_TEMP = '''
{
  "version": "4.5.6",
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
      "flags": {}
    }
  ],
  "imagePath": "X52210272001_002_data_1296.png",
  "imageData": null,
  "imageHeight": 2048,
  "imageWidth": 4096
}
'''
LABEL_STR = {
    0: 'qipao',
    1: "huashang",
    2: "fushi",
    3: "mianzhuangcashang",
    4: "qipi",
    6: "qiebianbuliang",
    7: "secha",
    8: "liangxian",
    9: "youban",
    10: "lvhui",
    12: "jinshuyaru",
    13: "nianshang",
    14: "yaguohuahen",
    16: "cashang",
    18: "kunyin",
    19: "qiebianbuqi",
    20: "shui",
    21: "fuquexian",
    22: "wujian"
}
# LABEL_STR = {
#     '15':'dhk',
#     '16':'hh',
#     '11':'rz',
#     '0':'lq',
#     '6':'qk',
#     '17':'ac',
#     '4':'cs',
#     '3':'ql',
# }
def export_label(input_id, save_dir):
    logs = database.search_es_nnl(image_id=input_id, table_name=IMAGE_DEFECT)
    images = database.search_es_nnl(id=input_id,table_name=IMAGE_TABLE)
    #logs = ES.search(image_id=input_id, table_name=IMAGE_DEFECT)
    # images = ES.search(id=input_id,table_name=IMAGE_TABLE)
    #print('images',images)
    if len(logs) == 0:
        logging.info('图像{}的缺陷数为0.'.format(input_id))
        return

    logs = [log['_source'] for log in logs]
    print("logs-------------------------------------------------")
    print("缺陷数目:",len(logs))

    images = [image['_source'] for image in images]
    # print("images-==============================================")
    # print("length of images:",len(images))
    image_defects = defaultdict(list)
    image_url = images[0]['image_url']
    share_name,_,image_id,dir_type,image_name = image_url.strip('\\').split('\\')
    if share_name == "WIN-HE6S3HFE15G":
        path = '/diskb/server113/grab_img'
    if share_name == "WIN-O5GVAHM4DSB":
        path = '/diskb/server112/grab_img'
    #收集同一名字的图片缺陷
    for log in logs:
        #diskb, server, camera_id, date_time, _, image_name = image_url.strip('/').split('/')
        image_defects[image_name].append(log)
    
    img_url = os.path.join(path,image_id,dir_type,image_name)
    tjson = json.loads(JSON_TEMP)
    tshape = tjson['shapes'][0]
    tjson['shapes'].clear()
    tshape['points'].clear()
    #名字，缺陷，（开始处理）

    for image_name, defects in image_defects.items():
        shape_list = []
        try:
            log = defects[0]
            if log['other0']=='new':
                save_dir = os.path.join(save_dir,'new')
                os.makedirs(save_dir, exist_ok=True)
            elif log['other0']=='modify':
                save_dir = os.path.join(save_dir,'modify')
                os.makedirs(save_dir, exist_ok=True)
            elif log['other0']=='delete' or log['is_user_delete']==True:
                save_dir = os.path.join(save_dir,'delete')
                #os.makedirs(save_dir, exist_ok=True)
                print('save_dir',save_dir)
            else :
                save_dir = os.path.join(save_dir,'save')
                print('save_dir',save_dir)
                os.makedirs(save_dir, exist_ok=True)
        except:
            print("log error",log)
        for log in defects:
            #一张图片的多个缺陷
            #print(log)

            image_url = images[0]['image_url']
            share_name,_,image_id,dir_type,image_name = image_url.strip('\\').split('\\')
            # diskb, server, camera_id, date_time, a, b = image_url.strip('/').split('/')

            oneshape = copy.deepcopy(tshape)
            x1 = float(log['x'])
            y1 = float(log['y'])
            x2 = float(log['x']) + float(log['w'])
            y2 = float(log['y']) + float(log['h'])
            oneshape['points'].append([x1, y1])
            oneshape['points'].append([x2, y2])
            oneshape['label'] = LABEL_STR[log['type']]
            shape_list.append(oneshape)
            
        onedict = copy.deepcopy(tjson)
        onedict['imagePath'] = image_name
        onedict['shapes'] = shape_list
        # 保存图片路径
        parent_dir = os.path.join(save_dir, input_id)    
        os.makedirs(parent_dir, exist_ok=True)
        img_url = os.path.join(path,image_id,dir_type,image_name)
        img_parent_path, _ = os.path.split(img_url) 
        # 保存时名字加一个mainid
        image_name = image_id +'_'+ image_name
        img_file = os.path.join(parent_dir, image_name)
        # img_url2 = os.path.join(path,image_id,dir_type,image_name)
        # 这里应该替换成机械盘路径
        # image_url2 = '//' + '/'.join([diskb, server, camera_id, date_time, a, b])
        if os.path.exists(img_url):   
            shutil.copy(img_url, img_file)
        # elif os.path.exists(image_url2):
        #     shutil.copy(image_url2, img_file)
        else:
            print(img_url, '不存在。')
        json_file = os.path.join(parent_dir, image_name.replace('jpg', 'json'))
        #print('parent_dir',parent_dir)
        #print('img_file',img_file)
        #print('json_file',json_file)
        # print('image_url2',image_url2)
        # print('json',tjson)
        with open(json_file, 'w', encoding='utf8') as f:
            json.dump(onedict, f, separators=(',', ': '), indent=4)
        
def export_img_label_from_ids(ids, save_dir):
    for it in tqdm(ids):
        export_label(input_id=it, save_dir=save_dir)


if __name__ == '__main__':
    sys_setting = MySettings()
    database = MyDatabase(sys_setting)
    database.create_es()
    img_width_pix = sys_setting.cfg_runner['Image']['image_w']
    img_hight_pix = sys_setting.cfg_runner['Image']['image_h']
    IMAGE_TABLE= sys_setting.cfg_runner['Database']['ES']['es_table'][0]
    IMAGE_DEFECT= sys_setting.cfg_runner['Database']['ES']['es_table'][1]
    STEEL_DEFECT = sys_setting.cfg_runner['Database']['ES']['es_table'][2]
    ids = [
'5A9AA3F7-0D5A-446B-AD40-BE1BA2172230',
'0236AB43-DB5F-421F-8EB9-54042D1FF500',
'D1CE5C0C-A906-4DEB-A5CA-606BCC6E8F49',
'5A9AA3F7-0D5A-446B-AD40-BE1BA2172230',
'0236AB43-DB5F-421F-8EB9-54042D1FF500',
'324AEE13-35BD-405C-B1E4-136A1FE0C910',
'D1CE5C0C-A906-4DEB-A5CA-606BCC6E8F49',
'8E327D3A-897C-4335-A712-38095E72F703',
'8E327D3A-897C-4335-A712-38095E72F703',
'8E327D3A-897C-4335-A712-38095E72F703',
'2B8FDCB0-0DA1-4280-8C8C-73609D0473D5',
'98E70A40-0F3A-439B-B393-A57D9FC8DA16',
'C265CD9D-D20B-4A6B-A645-19CBFD8115B6',
'FB5FF2F5-7CCD-4A78-8B21-C2FC01DF1D1A',
'4AE5FCC7-C960-4B3E-803D-327B4D586246',
'6CA05EEF-76C2-4AD7-90E0-338B566424C5',
'7E6E8F31-3DD4-4458-9D26-65347E1D5657',
'92646384-DC58-4B5D-ABE8-384D95D59CCE',
'E90FE116-4E1E-481B-A4C7-C316509AB35F',
'24CB86E3-ED7B-4A03-9DC1-B30DF6321127',
'E60FA2AA-199C-4E23-A5AF-269813400266',
'01064F7C-12EF-4EAC-A47D-8868A4AA3839',
'24CB86E3-ED7B-4A03-9DC1-B30DF6321127',
'2611EEB0-9BCC-4F56-A0F0-DC32F40E18BB',
'6FDDBB8A-72B7-40B0-B159-173F663D9468',
'2611EEB0-9BCC-4F56-A0F0-DC32F40E18BB',
'2611EEB0-9BCC-4F56-A0F0-DC32F40E18BB',
'2611EEB0-9BCC-4F56-A0F0-DC32F40E18BB',
'7989923D-00B5-4321-896A-8E2EDD6A6243',
'7989923D-00B5-4321-896A-8E2EDD6A6243',
'44CDEBAE-FCE1-4979-97A7-4856F5BC870D',
'5D7563AC-CE78-4AE3-8E27-932E9CAAB9EB',
'94EF78A4-7FE8-424B-B3EE-CF9BAC43E228',
'F25A836D-13AD-42FF-ACA1-470785E64673',
'94EF78A4-7FE8-424B-B3EE-CF9BAC43E228',
'94EF78A4-7FE8-424B-B3EE-CF9BAC43E228',
'907A35F5-7D6D-4A51-B061-6FA65B2EDD14',
'907A35F5-7D6D-4A51-B061-6FA65B2EDD14',
'BBBF2ECE-8C16-4901-ABCF-DCA8A9838F01',
'606DFF9F-CD28-46FA-B00F-0A1F8305D434',
'907A35F5-7D6D-4A51-B061-6FA65B2EDD14',
'BBBF2ECE-8C16-4901-ABCF-DCA8A9838F01',
'D6367702-C46B-4A20-A793-26D060F4C9A4',
'E5C93CFF-CB4E-4F64-B6D8-B447EAF50F4A',
'4F837D81-8D8F-4BF6-ACE3-B8C3E449EC12',
'4F837D81-8D8F-4BF6-ACE3-B8C3E449EC12',
'C3C2C076-5ADC-4B13-AA72-93306F96EC4B',
'C3C2C076-5ADC-4B13-AA72-93306F96EC4B',
'62C9BD53-9C8D-43A6-AF54-FDD118B2B43A',
'62C9BD53-9C8D-43A6-AF54-FDD118B2B43A',
'FB5FF2F5-7CCD-4A78-8B21-C2FC01DF1D1A',
'0B7E3D69-BC01-4AA8-8DC8-1EDFBE3871CE',
'E9F7DA7A-0DB1-4168-BDEA-1F23FD43FC90',
'E659959F-5547-4D4F-941C-41F65E2A4BD5',
'FCCFB500-56E8-475B-86F3-50990393B8A5',
'F6129AC5-8E1D-46F2-95C9-91223EFA242D',
'96181013-C46C-46ED-8848-EED9B0A6431A',
'2FF4C233-8028-47DA-94D1-365B75026A25',
'5960E62F-83D5-424F-8943-B0A2BC8B808B',
'45CD4DA7-642C-4FDC-B301-8E7E16575FAD',
'86552611-2E83-4B9B-BB86-72F9BC79EC8E',
    ]
    export_img_label_from_ids(ids=ids, save_dir=r'/home/deployer/NNLexport/20240517to20240520')
    #export_img_label_from_ids(ids=ids, save_dir=r'/home/hongtai/yolo/export_es/export_label')
