# -*- coding: utf-8 -*-
# coding=utf-8
# coding: utf-8

from elasticsearch import Elasticsearch
import argparse
import os
from tqdm import tqdm
from pathlib import Path
import shutil
import json
import copy
import cv2
import base64
from elasticsearch.helpers import bulk
import datetime
import traceback
from logger import logger

IMAGE_TABLE = "image"
IMAGE_DEFECT = "image_defect_table"
STEEL_DEFECT = "steel_defect_table"


class ESoperation:
    def __init__(self, host='192.168.2.111', port='9200'):
        self.host = host
        self.port = port
        self.es = Elasticsearch('http://' + host + ':' + port)

    def search_url(self, pic_id):
        body = {
            'query': {
                'bool': {
                    'must': [
                        {
                            'match_phrase': {
                                'id': pic_id
                            }

                        }

                    ]
                }
            }
        }
        filter_path = [
            'hits.hits._source.image_url',
        ]
        res = self.es.search(index='image_table', filter_path=filter_path, body=body, size=10000)
        log_dict = {}
        if not res:
            print('search empty')
            return
        num = 0
        for log in res['hits']['hits']:
            image_url = log['_source']['image_url']

            prefix_index = image_url.find(r"grab_img")
            if prefix_index != -1:
                new_path = "D:" + image_url[prefix_index + len(r"grab_img"):]
            return image_url

    def search(
            self,
            item_id=None,
            table_name=IMAGE_DEFECT,
            main_id=None,
            target_type=None,
            camera_id=None,
            conf=None,
            s_time=None,
            e_time=None,
            surface_id=None,
            is_raw=None,
            is_user_delete=None,
            other0=None,
            image_id=None,
            nohave_delete=None,
            num_limit=None
    ):

        if s_time is None:
            now_time = datetime.datetime.now()
            offset = datetime.timedelta(days=-1)
            s_time = (now_time + offset).strftime('%Y-%m-%dT%H:%M:%S')
            e_time = now_time.strftime('%Y-%m-%dT%H:%M:%S')

        logs = []
        content_size = 10000  # 设置一页的数据量
        if num_limit is not None and content_size > num_limit:
            content_size = num_limit
        total_size = 0
        size_cont = content_size
        next_id = 0  # 初始化next_id，每次循环是从  此数据 之后的第1个数据开始

        first = True
        while size_cont == content_size:

            # 按照main_id、时间查询
            body = {
                'query': {
                    'bool': {
                        'must': [
                            # {
                            #     'range': {
                            #         'insert_time':{
                            #             'gte': s_time,
                            #             'lt': e_time
                            #         }
                            #     }
                            # }
                        ],
                        "must_not": [

                        ]
                    }
                },
                'sort': [{'insert_time': 'asc'}],  # 以ziduan2为next_id，需要先对其进行排序
                'size': content_size  # 指定当前页数据量
            }

            if first:
                first = False
            else:
                body['search_after'] = next_id

            if s_time and e_time:
                query_dict = {
                    'range': {
                        'insert_time': {
                            'gte': s_time,
                            'lt': e_time
                        }
                    }
                }
                body['query']['bool']['must'].append(query_dict)

            if item_id:
                query_dict = {
                    'term': {
                        'id': item_id,
                    }
                }
                body['query']['bool']['must'].append(query_dict)
            if nohave_delete:
                query_dict = {
                    'term': {
                        'other0': 'delete',
                    }
                }
                body['query']['bool']['must_not'].append(query_dict)
                query_dict = {
                    'term': {
                        'other0': 'null',
                    }
                }
                body['query']['bool']['must_not'].append(query_dict)
            else:
                query_dict = {
                    'term': {
                        'other0': 'null',
                    }
                }
                body['query']['bool']['must_not'].append(query_dict)

            if image_id is not None:
                query_dict = {
                    'term': {
                        'image_id': image_id,
                    }
                }
                body['query']['bool']['must'].append(query_dict)
            if main_id:
                query_dict = {
                    'term': {
                        'main_id': main_id,
                    }
                }
                body['query']['bool']['must'].append(query_dict)

            if target_type is not None:
                query_dict = {
                    'term': {
                        'type': target_type,
                    }
                }
                body['query']['bool']['must'].append(query_dict)

            if camera_id is not None:
                query_dict = {
                    'term': {
                        'camera_id': camera_id,
                    }
                }
                body['query']['bool']['must'].append(query_dict)

            if is_user_delete is not None:
                query_dict = {
                    'term': {
                        'is_user_delete': is_user_delete,
                    }
                }
                body['query']['bool']['must'].append(query_dict)
            if is_raw is not None:
                query_dict = {
                    'term': {
                        'is_raw': is_raw,
                    }
                }
                body['query']['bool']['must'].append(query_dict)
            if surface_id is not None:
                query_dict = {
                    'term': {
                        'surface_id': surface_id,
                    }
                }
                body['query']['bool']['must'].append(query_dict)
            if conf is not None:
                query_dict = {
                    'range': {
                        'confidence': {
                            'gte': conf
                        }
                    }
                }
                body['query']['bool']['must'].append(query_dict)
            if other0 is not None:
                query_dict = {
                    'term': {
                        'other0': other0,
                    }
                }
                body['query']['bool']['must'].append(query_dict)

            res = self.es.search(index=table_name, body=body, request_timeout=60)  # 翻页取消使用filter

            try:
                size_cont = len(res['hits']['hits'])
                if size_cont == 0:
                    break
                logs += res['hits']['hits']

                next_id = res['hits']['hits'][-1]['sort']  # 更新next_id
                total_size += size_cont
                if num_limit is not None and total_size >= num_limit:
                    logs = logs[0:num_limit]
                    break

            except Exception as e:
                logger.info('error in es search! :', e)
                # print(('error in es search! :', e))
                traceback.print_exc()

        # print('total num: ', len(logs))
        # return [log['_source'] for log in logs]
        return logs

    def bulk(self, actions):
        res = bulk(self.es, actions)
        return res


#


def search_from_es(args):
    item_id = None
    table_name = 'image_defect_table'
    is_raw = None
    main_id = '20240220110954'
    target_type = None
    conf = None
    camera_id = None
    surface_id = None
    is_user_delete = None
    other0 = None
    s_time = "2023-10-11T17:12:00"
    e_time1 = "2023-10-11T17:12:40"
    e_time = None
    # 是否下载
    #
    es = ESoperation('192.168.2.111', '9200')
    res = es.search(item_id, table_name, main_id, target_type, camera_id, conf, s_time, e_time, surface_id, is_raw,
                    is_user_delete, other0, None, None, None)

    # print(res)

    log_dict = {}
    if not res:
        print('search empty')
        return
    num = 0
    imageid_list = []
    for log in res:
        try:
            image_id = log['_source']['image_id']
            if image_id not in imageid_list:
                imageid_list.append(image_id)
        except:
            print('image_id')
            continue
    print('picnum', len(imageid_list))
    for image_id in imageid_list:
        res = es.search(item_id, table_name, main_id, target_type, camera_id, conf, s_time, e_time, surface_id, is_raw,
                        is_user_delete, other0, image_id, True, None)
        for log in res:
            try:
                if 'image_url' in log['_source'].keys():
                    image_url = log['_source']['image_url']
                    print('image1',image_url)
                else:
                    image_url = es.search_url(log['_source']['image_id'])
                    if image_url is None:
                        print('image3', image_url)
                    else:
                        print('image2', image_url)
                        continue
            except:
                print('image')
                continue
            if image_url not in log_dict.keys():
                log_dict[image_url] = []
            x = int(log['_source']['x'])
            y = int(log['_source']['y'])
            w = int(log['_source']['w'])
            h = int(log['_source']['h'])
            surface_id = int(log['_source']['surface_id'])
            defect_label = label_dict[str(log['_source']['type'])]
            item = (x, y, w, h, defect_label, surface_id)
            num += 1
            log_dict[image_url].append(item)
    print('pic:', len(log_dict.keys()))
    print('defect_num:', num)
    new_dict = {}
    for key, value in log_dict.items():
        if len(value) > 0:
            new_dict[key] = value



    if args.store_json:
        if args.target_dir:
            if not os.path.exists(args.target_dir):
                os.makedirs(args.target_dir)
            target_dir = args.target_dir
        else:
            target_dir = mainid
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

        for imageurl in log_dict:
            main_id, file_name = get_mainid_filename(imageurl)
            input_image_path = target_dir + "/" + main_id + "_" + file_name
            labelme_dict = {}
            for i in range(len(log_dict[imageurl])):
                (x, y, w, h, defect_label, surface_id) = log_dict[imageurl][i]
                if surface_id not in labelme_dict.keys():
                    labelme_dict[surface_id] = create_labelme_annotation(input_image_path, imageurl, x, y, w, h,
                                                                         defect_label, surface_id)

                else:
                    shape = {
                        "label": defect_label,
                        "points": [[x, y], [x + w, y + h]],
                        "group_id": None,
                        "shape_type": "rectangle",
                        "flags": {}
                    }
                    labelme_dict[surface_id]["shapes"].append(shape)
            for s_id in labelme_dict.keys():
                labelme_data = labelme_dict[s_id]

                output_json_path = input_image_path.replace('.jpg', '_' + str(s_id) + '.json')
                with open(output_json_path, "w") as f:
                    json.dump(labelme_data, f, indent=2)


def create_labelme_annotation(targetpath, image_path, x, y, w, h, label, surface_id):
    # 使用os.path模块来分离文件名和扩展名
    dirname, filename = os.path.split(targetpath)
    name, ext = os.path.splitext(filename)
    st = image_path.find("grab_img")
    if surface_id == 2:
        new_img_path = os.path.join('/diskb/server112', image_path[st:].replace('\\', '/'))
        image_height, image_width = 2048, 4096
        new_name = name + '_2' + ext
    if surface_id == 1:
        new_img_path = os.path.join('/diskb/server113', image_path[st:].replace('\\', '/'))
        image_height, image_width = 2048, 4096
        new_name = name + '_1' + ext
    targetpath = os.path.join(dirname, new_name)

    shutil.copy(new_img_path, targetpath)

    annotation = {
        "version": "5.1.1",
        "flags": {},
        "shapes": [],
        "imagePath": new_name,
        "imageData": None,
        "imageHeight": image_height,
        "imageWidth": image_width
    }

    # Create shape annotation for the box
    shape = {
        "label": label,
        "points": [[x, y], [x + w, y + h]],
        "group_id": None,
        "shape_type": "rectangle",
        "flags": {}
    }

    # Add the shape annotation to the Labelme annotation
    annotation["shapes"].append(shape)

    return annotation


def get_mainid_filename(path):
    # 解析path
    parts = path.split('\\')
    date_and_number = parts[-3]
    filename = parts[-1]
    return [date_and_number, filename]


if __name__ == '__main__':
    label_dict = {
        '0': 'qipao',  # 气泡
        '1': 'huashang',  # 划伤
        '2': 'fushi',  # 腐蚀
        '3': 'mianzhuangcashang',  # 面状擦伤
        '4': 'qipi',  # 起皮
        '6': 'qiebianbuliang',  # 切边不良
        '7': 'secha',  # 色差
        '8': 'liangxian',  # 亮线
        '9': 'youban',  # 油斑
        '10': 'lvhui',  # 铝灰
        '12': 'jinshuyaru',  # 金属压入
        '13': 'nianshang',  # 粘伤
        '14': 'yaguohuahen',  # 压过划痕
        '16': 'cashang',  # 擦伤
        '18': 'kunyin',  # 锟印
    }
    parser = argparse.ArgumentParser(description='Elasticsearch .')
    parser.add_argument('--store-json', action='store_true')
    parser.add_argument('--target-dir', type=str, default=None, help='eg. /home/hongtai/workspace/data/yg_data')

    flags = parser.parse_args()
    main_ids = ['20240220110954','20240220164814','20240220200101','20240220230251']
    search_from_es(flags)
