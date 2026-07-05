# -*- coding: utf-8 -*-

import torch
import numpy as np
import time
import random
import cv2
import os
import yaml
import torchvision

# from yolov5.infer_atalas.utils.general import non_max_suppression,scale_coords
#from MyObject.Defect import SteelDefect, ImageDefect
from ais_bench.infer.interface import InferSession


current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
def non_max_suppression(prediction, conf_thres=0.25, iou_thres=0.45, classes=None, agnostic=False, multi_label=False,
                        labels=(), max_det=300):
    """Runs Non-Maximum Suppression (NMS) on inference results

    Returns:
         list of detections, on (n,6) tensor per image [xyxy, conf, cls]
    """
    prediction = prediction.float()
    nc = prediction.shape[2] - 5  # number of classes
    xc = prediction[..., 4] > conf_thres  # candidates

    # Checks
    assert 0 <= conf_thres <= 1, f'Invalid Confidence threshold {conf_thres}, valid values are between 0.0 and 1.0'
    assert 0 <= iou_thres <= 1, f'Invalid IoU {iou_thres}, valid values are between 0.0 and 1.0'

    # Settings
    min_wh, max_wh = 2, 7680  # (pixels) minimum and maximum box width and height
    max_nms = 30000  # maximum number of boxes into torchvision.ops.nms()
    time_limit = 10.0  # seconds to quit after
    redundant = True  # require redundant detections
    multi_label &= nc > 1  # multiple labels per box (adds 0.5ms/img)
    merge = False  # use merge-NMS

    t = time.time()
    output = [torch.zeros((0, 6), device=prediction.device)] * prediction.shape[0]
    for xi, x in enumerate(prediction):  # image index, image inference
        # Apply constraints
        x[((x[..., 2:4] < min_wh) | (x[..., 2:4] > max_wh)).any(1), 4] = 0  # width-height
        x = x[xc[xi]]  # confidence

        # Cat apriori labels if autolabelling
        if labels and len(labels[xi]):
            lb = labels[xi]
            v = torch.zeros((len(lb), nc + 5), device=x.device)
            v[:, :4] = lb[:, 1:5]  # box
            v[:, 4] = 1.0  # conf
            v[range(len(lb)), lb[:, 0].long() + 5] = 1.0  # cls
            x = torch.cat((x, v), 0)

        # If none remain process next image
        if not x.shape[0]:
            continue

        # Compute conf
        x[:, 5:] *= x[:, 4:5]  # conf = obj_conf * cls_conf

        # Box (center x, center y, width, height) to (x1, y1, x2, y2)
        box = xywh2xyxy(x[:, :4])

        # Detections matrix nx6 (xyxy, conf, cls)
        if multi_label:
            i, j = (x[:, 5:] > conf_thres).nonzero(as_tuple=False).T
            x = torch.cat((box[i], x[i, j + 5, None], j[:, None].float()), 1)
        else:  # best class only
            conf, j = x[:, 5:].max(1, keepdim=True)
            x = torch.cat((box, conf, j.float()), 1)[conf.view(-1) > conf_thres]

        # Filter by class
        if classes is not None:
            x = x[(x[:, 5:6] == torch.tensor(classes, device=x.device)).any(1)]

        # Apply finite constraint
        # if not torch.isfinite(x).all():
        #     x = x[torch.isfinite(x).all(1)]

        # Check shape
        n = x.shape[0]  # number of boxes
        if not n:  # no boxes
            continue
        elif n > max_nms:  # excess boxes
            x = x[x[:, 4].argsort(descending=True)[:max_nms]]  # sort by confidence

        # Batched NMS
        c = x[:, 5:6] * (0 if agnostic else max_wh)  # classes
        boxes, scores = x[:, :4] + c, x[:, 4]  # boxes (offset by class), scores
        i = torchvision.ops.nms(boxes, scores, iou_thres)  # NMS
        # i = NMS(boxes, scores, iou_thres)
        if i.shape[0] > max_det:  # limit detections
            i = i[:max_det]
        if merge and (1 < n < 3E3):  # Merge NMS (boxes merged using weighted mean)
            # update boxes as boxes(i,4) = weights(i,n) * boxes(n,4)
            iou = box_iou(boxes[i], boxes) > iou_thres  # iou matrix
            weights = iou * scores[None]  # box weights
            x[i, :4] = torch.mm(weights, x[:, :4]).float() / weights.sum(1, keepdim=True)  # merged boxes
            if redundant:
                i = i[iou.sum(1) > 1]  # require redundancy

        # 默认输出
        output[xi] = x[i]
        # 继续对结果后处理，提升低阈值下性能（0.4）

        if (time.time() - t) > time_limit:
            LOGGER.warning(f'WARNING: NMS time limit {time_limit}s exceeded')
            break  # time limit exceeded

    return output
def xywh2xyxy(x):
    # Convert nx4 boxes from [x, y, w, h] to [x1, y1, x2, y2] where xy1=top-left, xy2=bottom-right
    y = x.clone() if isinstance(x, torch.Tensor) else np.copy(x)
    y[:, 0] = x[:, 0] - x[:, 2] / 2  # top left x
    y[:, 1] = x[:, 1] - x[:, 3] / 2  # top left y
    y[:, 2] = x[:, 0] + x[:, 2] / 2  # bottom right x
    y[:, 3] = x[:, 1] + x[:, 3] / 2  # bottom right y
    return y
def scale_coords(img1_shape, coords, img0_shape, ratio_pad=None):
    # Rescale coords (xyxy) from img1_shape to img0_shape
    if ratio_pad is None:  # calculate from img0_shape
        gain = min(img1_shape[0] / img0_shape[0], img1_shape[1] / img0_shape[1])  # gain  = old / new
        pad = (img1_shape[1] - img0_shape[1] * gain) / 2, (img1_shape[0] - img0_shape[0] * gain) / 2  # wh padding
    else:
        gain = ratio_pad[0][0]
        pad = ratio_pad[1]

    coords[:, [0, 2]] -= pad[0]  # x padding
    coords[:, [1, 3]] -= pad[1]  # y padding
    coords[:, :4] /= gain
    clip_coords(coords, img0_shape)
    return coords
def clip_coords(boxes, shape):
    boxes = boxes.float()#增加
    # Clip bounding xyxy bounding boxes to image shape (height, width)
    if isinstance(boxes, torch.Tensor):  # faster individually
        boxes[:, 0].clamp_(0, shape[1])  # x1
        boxes[:, 1].clamp_(0, shape[0])  # y1
        boxes[:, 2].clamp_(0, shape[1])  # x2
        boxes[:, 3].clamp_(0, shape[0])  # y2
    else:  # np.array (faster grouped)
        boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, shape[1])  # x1, x2
        boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, shape[0])  # y1, y2

class Detector:
    
    def __init__(self, gpu_id='0'):
        # self.logger = sys_setting.logger
        # self.cfg_runner = sys_setting.cfg_runner
        # self.model_runner = sys_setting.model_runner
        # self.device = gpu_id
        self.model_path = r'/home/deployer/NNL/Maintenance/weight_files/best1127_bs1.om'
        # self.parse_setting()
        self.model = InferSession(0, self.model_path)
        


    def parse_setting(self):
        with open(r'./model.yaml') as f:
            self.model_runner = yaml.load(f, Loader=yaml.FullLoader)
        
        self.anchors = torch.tensor(self.model_runner['anchors'])
        self.stride = torch.tensor(self.model_runner['stride'])
        self.cls_num = self.model_runner['class_num']
        self.conf_thres = self.model_runner['conf_thres']
        self.iou_thres = self.model_runner['iou_thres']

    def letterbox(self,img, new_shape=(640, 640), color=(114, 114, 114), auto=False, scaleFill=False, scaleup=True):
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
    def preProcess(self,img_origins, neth = 640, netw = 640):
        img_list = []
        info_list = []
        shape_list = []
        try:
            for img_origin in img_origins:
                imgh, imgw = img_origin.shape[:2]
                img_origin, ratio, pad = self.letterbox(img_origin)
                shape = (imgh, imgw), ((img_origin.shape[0] / imgh, img_origin.shape[1] / imgw), pad)
                img_info = np.stack([np.array([neth, netw, imgh, imgw], dtype=np.float16)], axis=0)
                img_origin = (np.stack([img_origin], axis=0))

                img = img_origin[..., ::-1].transpose(0, 3, 1, 2) 
                image_np = np.array(img, dtype=np.float32)  
                image_np_expanded = image_np / 255.0  
                img = np.ascontiguousarray(image_np_expanded).astype(np.float16)  
                img_list.append(img)
                info_list.append(img_info)
                shape_list.append(shape)
            return img_list, info_list,shape_list
        except Exception as e:
            self.logger.info()
    def infer_one_pic(self,img,imginfo,shape):
        result = self.model.infer([img])
        #result = self.model.infer_pipeline()
        if len(result) == 3:  
            out = []
            for i in range(len(result)):
                correct_bbox(result[i], self.anchors[i], self.stride[i], self.cls_num, out)
            box_out = torch.cat(out, 1)
        else:  # only use the first output node, which shape is (bs, -1, no)
            box_out = torch.tensor(result[0])

        # non_max_suppression
        boxout = non_max_suppression(box_out, conf_thres=0.2, iou_thres=0.3)
        for idx, pred in enumerate(box_out):
            scale_coords(img[idx].shape[1:], pred[:, :4], shape[0], shape[1])
        #print(boxout)
        aa = [[[elem.item() for elem in row[:6]] for row in tensor] for tensor in boxout]
        
        return aa[0]

        
    def detect(self, batch_imgs):
        cu_batch_result = []
        batch_imgs,batch_imginfos,batch_shapes = self.preProcess(batch_imgs)
        for img,imginfo,shape in zip(batch_imgs,batch_imginfos, batch_shapes): 
            
            cu_result = self.infer_one_pic(img,imginfo,shape)
            
            cu_batch_result.append(cu_result)
            

        return cu_batch_result





if __name__ == '__main__':
    print('hello1')
    detect = Detector()
    a = cv2.imread("/home/deployer/NNL/Test/00000_2.jpg")
    print('hello')
    imgs = [a] * 2
    print(detect.detect(imgs)) 
