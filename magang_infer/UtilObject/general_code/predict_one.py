# -*- coding: GBK -*-
import yaml
import argparse
import tqdm
import os
import cv2
import json
import glob
import torch
import copy
import numpy as np
import shutil
import traceback
from functools import cmp_to_key
from ais_bench.infer.interface import InferSession
from run import forward_nmsscript_split_addition, compare_area, compare_score, merge_bboxes


def main(opt, model_path, cfg_model, cfg_infer):
    model = InferSession(11, model_path)
    if 'nms' not in model_path:
        inference = forward_nmsscript_split_addition
    else:
        # inference = forward_nmsop_split_addition
        print('No Model!')
        return
    if not opt.imgs_path:
        img_path = opt.img_path
        img_list = [img_path]
    else:
        imgs_dir = opt.imgs_path
        imgs_path = os.path.join(imgs_dir, '*.jpg')
        img_list = glob.glob(imgs_path)

    for img_path in tqdm.tqdm(img_list):

        img_name, sfx = os.path.splitext(os.path.basename(img_path))
        out_dir = os.path.join(opt.out_dir, img_name)
        os.makedirs(out_dir, exist_ok=True)
        new_name = os.path.join(out_dir, img_name + '_merge_' + sfx)

        raw_img = cv2.imread(img_path)
        whole_img = np.copy(raw_img)
        whole_img2 = np.copy(raw_img)

        preds = inference(model, img_path, cfg_infer['cls_id'], cfg_infer['conf_thred'], None, cfg_infer['label_dict'],
                          cfg_model)
        if opt.store_json:  # 推理结果直接放上去
            get_json_pic(preds, whole_img2, out_dir, img_path)
        # preds = preds[try_remove_repeat(preds,cfg_infer['conf_thred'])]
        preds.sort(key=cmp_to_key(compare_area))
        for i, pred in enumerate(preds):
            pred['score'] = 0.3 * pred['score'] + 0.7 * (len(preds) - i - 1) / len(preds)
        preds.sort(key=cmp_to_key(compare_score))
        for i, pred in enumerate(preds):
            pred.pop('score')
            pred.pop('label')

        boxes = {}
        for pred in preds:
            if pred['type'] not in boxes.keys():
                boxes[pred['type']] = []
            boxes[pred['type']].append([pred['x'], pred['y'], pred['w'], pred['h'], pred['conf']])

        for cls_, raw_box in boxes.items():
            print('cls_:', cls_)
            if cls_ != 1 and cls_ != 18:
                merged_box, cluster = merge_bboxes(raw_box, 500)
            else:  # out of hua shang
                merged_box = copy.deepcopy(raw_box)
            for i, box in enumerate(merged_box):
                x1 = int(box[0])
                y1 = int(box[1])
                x2 = int(box[0] + box[2])
                y2 = int(box[1] + box[3])
                conf = box[4]
                whole_img = cv2.rectangle(whole_img, (x1, y1), (x2, y2), (0, 165, 255), 3)
                whole_img = cv2.putText(whole_img, str(int(cls_)), (int(x1), int(y1 + 16)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 165, 255), 2)
                whole_img = cv2.putText(whole_img, str(round(conf, 2)), (int(x1), int(y1 + 96)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 165, 255), 2)

        cv2.imwrite(new_name, whole_img)


def get_json_pic(pred_json_list, whole_img, out_dir, img_path):
    try:
        shapes = []
        for pred in pred_json_list:
            # if pred['score'] >= 0.1:
            defect_x1 = pred['x']
            defect_y1 = pred['y']
            defect_x2 = pred['x'] + pred['w']
            defect_y2 = pred['y'] + pred['h']
            shapes.append(
                {
                    'label': pred['label'],
                    'points': [
                        [defect_x1, defect_y1], [defect_x2, defect_y2]
                    ],
                    'shape_type': 'rectangle',
                    'group_id': None,
                    'score': pred['score'],
                    'flags': {},
                }
            )
            # 绘制框在大图
            # whole_img = cv2.rectangle(whole_img, (defect_x1, defect_y1), (defect_x2, defect_y2), (255, 0, 0), 2)
            # whole_img = cv2.putText(whole_img, pred['label'], (defect_x1, int(defect_y1 + 16)),
            # cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        whole_name = os.path.join(out_dir, os.path.basename(img_path))
        cv2.imwrite(whole_name, whole_img)
        # save labelme data
        if len(shapes):
            img_name, ext = os.path.splitext(os.path.basename(img_path))
            json_file = whole_name.replace(ext, '.json')
            # json_file = os.path.join(json_dir, img_name+'.json')
            json_dict = {}
            json_dict['shapes'] = shapes
            json_dict['imagePath'] = os.path.basename(img_path)
            json_dict['imageData'] = None
            json_dict['imageWidth'] = whole_img.shape[1]
            json_dict['imageHeight'] = whole_img.shape[0]
            json_dict['flags'] = {}
            json_dict['version'] = '4.5.3'
            with open(json_file, 'w', encoding='utf-8') as wf:
                data = json.dumps(json_dict, separators=(',', ': '), indent=2)
                wf.write(data)

    except Exception as e:
        traceback.print_exc()
        print(e)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='YOLOv5 offline model inference.')
    parser.add_argument('--cfg_infer', type=str, default='common/setting_detect.yaml',
                        help='model parameters config file')
    parser.add_argument('--cfg_model', type=str, default='common/model.yaml', help='model parameters config file')
    parser.add_argument('--model_path', type=str, default='', help='model parameters config file')
    parser.add_argument('--imgs_path', type=str, default='', help='model parameters config file')
    parser.add_argument('--out_dir', type=str, default='./result', help='model parameters config file')
    parser.add_argument('--img_path', type=str, default='./1_00000017_6752.jpg', help='model parameters config file')
    parser.add_argument('--store_json', action='store_true')
    opt = parser.parse_args()

    with open(opt.cfg_infer) as f:
        cfg_infer = yaml.load(f, Loader=yaml.FullLoader)
    with open(opt.cfg_model) as f:
        cfg_model = yaml.load(f, Loader=yaml.FullLoader)
    model_path = opt.model_path if opt.model_path != '' else cfg_infer['model_path']
    print(model_path)
    main(opt, model_path, cfg_model, cfg_infer)
    # print(cfg['npu_num'])