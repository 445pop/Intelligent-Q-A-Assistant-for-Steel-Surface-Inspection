import torch
import torchvision

import numpy as np
import cv2
import os
from MyObject.Defect import SteelDefect, ImageDefect
from MyObject.ProjectConfig import MySettings
import sys
import traceback
import time


# 获取当前文件所在目录的父级目录路径
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)



class Detector:
    
    def __init__(self, sys_setting, device_id='0'):
        from ais_bench.infer.interface import InferSession
        self.logger = sys_setting.logger
        self.cfg_runner = sys_setting.cfg_runner
        self.model_runner = sys_setting.model_runner
        # print(sys_setting.cfg_runner['model_path'])
        self.model = InferSession(device_id, sys_setting.cfg_runner['model_path'])
        self.parse_setting()
    def box_iou(self,box1, box2):
        # https://github.com/pytorch/vision/blob/master/torchvision/ops/boxes.py
        """
        Return intersection-over-union (Jaccard index) of boxes.
        Both sets of boxes are expected to be in (x1, y1, x2, y2) format.
        Arguments:
            box1 (Tensor[N, 4])
            box2 (Tensor[M, 4])
        Returns:
            iou (Tensor[N, M]): the NxM matrix containing the pairwise
                IoU values for every element in boxes1 and boxes2
        """

        def box_area(box):
            # box = 4xn
            return (box[2] - box[0]) * (box[3] - box[1])

        area1 = box_area(box1.T)
        area2 = box_area(box2.T)

        # inter(N,M) = (rb(N,M,2) - lt(N,M,2)).clamp(0).prod(2)
        inter = (torch.min(box1[:, None, 2:], box2[:, 2:]) - torch.max(box1[:, None, :2], box2[:, :2])).clamp(0).prod(2)
        return inter / (area1[:, None] + area2 - inter)  # iou = inter / (area1 + area2 - inter)
    def non_max_suppression(self,prediction, conf_thres=0.25, iou_thres=0.45, classes=None, agnostic=False, multi_label=False,
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
            box = self.xywh2xyxy(x[:, :4])

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
                iou = self.box_iou(boxes[i], boxes) > iou_thres  # iou matrix
                weights = iou * scores[None]  # box weights
                x[i, :4] = torch.mm(weights, x[:, :4]).float() / weights.sum(1, keepdim=True)  # merged boxes
                if redundant:
                    i = i[iou.sum(1) > 1]  # require redundancy

            # 默认输出
            output[xi] = x[i]
            # 继续对结果后处理，提升低阈值下性能（0.4）

            if (time.time() - t) > time_limit:
                print(f'WARNING: NMS time limit {time_limit}s exceeded')
                break  # time limit exceeded

        return output
    
    def xywh2xyxy(self,x):
        # Convert nx4 boxes from [x, y, w, h] to [x1, y1, x2, y2] where xy1=top-left, xy2=bottom-right
        y = x.clone() if isinstance(x, torch.Tensor) else np.copy(x)
        y[:, 0] = x[:, 0] - x[:, 2] / 2  # top left x
        y[:, 1] = x[:, 1] - x[:, 3] / 2  # top left y
        y[:, 2] = x[:, 0] + x[:, 2] / 2  # bottom right x
        y[:, 3] = x[:, 1] + x[:, 3] / 2  # bottom right y
        return y
    def scale_coords(self,img1_shape, coords, img0_shape, ratio_pad=None):
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
        self.clip_coords(coords, img0_shape)
        return coords
    def clip_coords(self,boxes, shape):
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
    def nms(self, boxes, thresh):
        """Pure Python NMS baseline."""
        if boxes.size == 0: return []  # 无bboxes则直接返回
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        scores = boxes[:, 4]

        # 计算每一个anchor的面积
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        # 按照从小到大排序后返回下标，然后顺序取反，即从大到小对应的下标
        order = scores.argsort()[::-1]

        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            # 置信度高的预测框即当前框与其他框的交集
            # 选择的区域就是取最大的x1, y1和最小的 x2, y2
            xx1 = np.maximum(x1[i], x1[order[1:]])  # 这个就是较差区域的左上角的坐标，下面以此类推
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            # 计算交叉区域的面积，就是用当前的anchor与其它的anchor计算，是否有相交的面积，如果有，那相交的面积是多少
            w = np.maximum(0.0, xx2 - xx1 + 1)  # 计算w
            h = np.maximum(0.0, yy2 - yy1 + 1)  # 计算h
            inter = w * h  # 交叉面积
            # 计算IOU,  相交区域 / (当前区域 + 某区域面积 - 相交区域面积)
            ovr = inter / (areas[i] + areas[order[1:]] - inter)
            # 保留IOU小于阈值的框
            inds = np.where(ovr <= thresh)[0]
            # 因为ovr数组的长度比order数组少一个,所以这里要将所有下标后移一位
            order = order[inds + 1]
        return boxes[keep]


    def parse_setting(self):
        self.anchors = torch.tensor(self.model_runner['anchors'])
        self.stride = torch.tensor(self.model_runner['stride'])
        self.cls_num = self.model_runner['class_num']
        self.conf_thres = self.model_runner['conf_thres']
        self.iou_thres = self.model_runner['iou_thres']


    # 将输入图像的上下或者左右添加填充，使其成为一个指定大小的矩形图像（640*640）   img:输入图像 new_shape:目标图像大小
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
                img_origin, ratio, pad = self.letterbox(img_origin,new_shape=(neth, netw))
                shape = (imgh, imgw), ((img_origin.shape[0] / imgh, img_origin.shape[1] / imgw), pad)
                img_info = np.stack([np.array([neth, netw, imgh, imgw], dtype=np.float16)], axis=0)
                img_origin = (np.stack([img_origin], axis=0))

                img = img_origin[..., ::-1].transpose(0, 3, 1, 2)  # BGR tp RGB HWC to CHW
                image_np = np.array(img, dtype=np.float32)  # img 转换为NumPy数组
                image_np_expanded = image_np / 255.0  # 像素值进行归一化，将值范围从0到255缩放到0到1之间
                img = np.ascontiguousarray(image_np_expanded).astype(np.float16)  # image_np_expanded 转换为一个以连续内存存储的NumPy数组
                img_list.append(img)
                info_list.append(img_info)
                shape_list.append(shape)
            return img_list, info_list,shape_list
        except Exception as e:
            self.logger.error(traceback.format_exc())
    
    
    
    def infer_one_pic(self,img,info,shape):
        from yolov5.infer_atalas.common.util.dataset import correct_bbox
        
        result = self.model.infer([img])
        if len(result) == 3:
            out = []
            for i in range(len(result)):
                correct_bbox(result[i], self.anchors[i], self.stride[i], self.cls_num, out)
            box_out = torch.cat(out, 1)
            
        else:  # only use the first output node, which shape is (bs, -1, no)
            box_out = torch.tensor(result[0]) # 执行了这个

        boxout = self.non_max_suppression(box_out, conf_thres=self.conf_thres, iou_thres=self.iou_thres)
        
        for idx, pred in enumerate(boxout):
            self.scale_coords(img[idx].shape[1:], pred[:, :4], shape[0], shape[1])
        # 仅会单张图推理
        one_pic_pred = [[[elem.item() for elem in row[:6]] for row in tensor] for tensor in boxout][0]

        return one_pic_pred
    def infer_bs_pic(self,img_list, imginfo_list, shape_list, need_bs, cu_bs):#未测试
        from yolov5.infer_atalas.common.util.dataset import correct_bbox
        if cu_bs != need_bs:
            temp = need_bs - cu_bs
            img_list += [img_list[0]] * temp
            shape_list += [shape_list[0]] * temp
        img_list = np.concatenate(img_list, axis=0)
        shape_list = np.concatenate(shape_list, axis=0)
        result = self.model.infer([img_list])
        if len(result) == 3:
            out = []
            for i in range(len(result)):
                correct_bbox(result[i], self.anchors[i], self.stride[i], self.cls_num, out)
            box_out = torch.cat(out, 1)
            
        else:  # only use the first output node, which shape is (bs, -1, no)
            box_out = torch.tensor(result[0]) # 执行了这个

        boxout = self.non_max_suppression(box_out, conf_thres=self.conf_thres, iou_thres=self.iou_thres)
        
        for idx, pred in enumerate(boxout):
            self.scale_coords(img_list[idx].shape[1:], pred[:, :4], shape_list[idx][0], shape_list[idx][1])
        
        bs_pic_pred = [[[elem.item() for elem in row[:6]] for row in tensor] for tensor in boxout]

        return bs_pic_pred

    def infer_one_pic_op(self,img,info,shape):
        from yolov5.infer_atalas.common.util.dataset import correct_bbox
        
        result = self.model.infer([img,info])
        batch_boxout, boxnum = result
        
        num_det = int(boxnum[0][0])
        boxout = batch_boxout[0][:num_det * 6].reshape(6, -1).transpose().astype(np.float32)  # 6xN -> Nx6
        # print(box_out)        
        return  boxout
    def infer_bs_pic_op(self, img_list, imginfo_list, shape_list, need_bs, cu_bs):
        if cu_bs != need_bs:
            temp = need_bs - cu_bs
            img_list += [img_list[0]] * temp
            imginfo_list += [imginfo_list[0]] * temp
        
        img_list = np.concatenate(img_list, axis=0)
        imginfo_list = np.concatenate(imginfo_list, axis=0)
        # img_list = np.pad(img_list, ((0, need_bs-cu_bs), (0, 0), (0, 0), (0, 0)), 'constant', constant_values=0)
        result = self.model.infer([img_list,imginfo_list])
        batch_boxout, boxnum = result
        
        for idx in range(cu_bs):  
            num_det = int(boxnum[idx][0])
            boxout = batch_boxout[idx][:num_det * 6].reshape(6, -1).transpose()  # 6xN -> Nx6
            # print(boxout)
        num_det = int(boxnum[0][0])
        # boxout = batch_boxout[0][:num_det * 6].reshape(6, -1).transpose().astype(np.float32)  # 6xN -> Nx6
        return batch_boxout


    def detect(self, batch_imgs):
        cu_batch_result = []
        batch_imgs,batch_imginfos,batch_shapes = self.preProcess(batch_imgs)
        for img,imginfo,shape in zip(batch_imgs,batch_imginfos, batch_shapes):
            cu_result = self.infer_one_pic(img,shape)
            cu_batch_result.append(cu_result)
        return cu_batch_result
    def detect_after_preProcess(self, batch_imgs, batch_imginfos, batch_shapes):
        cu_batch_result = []
        
        for img, imginfo, shape in zip(batch_imgs, batch_imginfos, batch_shapes):
            cu_result = self.infer_one_pic_op(img, imginfo,shape)
            cu_batch_result.append(cu_result)
        return cu_batch_result
    
    def detect_op_test2(self,batch_imgs):
        cu_batch_result = []
        batch_imgs,batch_imginfos,batch_shapes = self.preProcess(batch_imgs)
        # 一共6400张图
        t1 = time.time()
        
        item = 6400 // batch
        t1 = time.time()
        for i in range(item):
            cu_batch_result = self.infer_bs_pic_op(batch_imgs, batch_imginfos, batch_shapes, batch, batch)
            #cu_batch_result = self.infer_bs_pic(batch_imgs, batch_imginfos, batch_shapes, batch, batch)
        print('batch:{} time{}'.format(batch,time.time()-t1))
        return cu_batch_result
    def detect_test(self,batch_imgs):
        cu_batch_result = []
        batch_imgs,batch_imginfos,batch_shapes = self.preProcess(batch_imgs)
        for img,imginfo,shape in zip(batch_imgs,batch_imginfos, batch_shapes):        
            cu_result = self.infer_one_pic(img,imginfo,shape)
            cu_batch_result.append(cu_result)
        return cu_batch_result
class Detector_Batch:
    def __init__(self, sys_setting, gpu_id='0'):
        from yolov5.infer_nvidia.utils.torch_utils import select_device
        self.logger = sys_setting.logger
        self.cfg_runner = sys_setting.cfg_runner
        self.model_runner = sys_setting.model_runner
        self.device = gpu_id
        self.device = select_device(self.device)
        yolov5_code_path =  os.path.join(parent_dir, 'yolov5', 'infer_nvidia')
        self.model = torch.hub.load(yolov5_code_path, 'custom', path=self.cfg_runner['model_path'],
                                    source='local', autoshape=True)
        self.model.conf = self.model_runner['conf_thres']
        self.model.iou = self.model_runner['iou_thres']
        self.model.to(self.device).eval()

    def nms(self, boxes, thresh):
        """Pure Python NMS baseline."""
        if boxes.size == 0: return []  # 无bboxes则直接返回
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        scores = boxes[:, 4]

        # 计算每一个anchor的面积
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        # 按照从小到大排序后返回下标，然后顺序取反，即从大到小对应的下标
        order = scores.argsort()[::-1]

        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            # 置信度高的预测框即当前框与其他框的交集
            # 选择的区域就是取最大的x1, y1和最小的 x2, y2
            xx1 = np.maximum(x1[i], x1[order[1:]])  # 这个就是较差区域的左上角的坐标，下面以此类推
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            # 计算交叉区域的面积，就是用当前的anchor与其它的anchor计算，是否有相交的面积，如果有，那相交的面积是多少
            w = np.maximum(0.0, xx2 - xx1 + 1)  # 计算w
            h = np.maximum(0.0, yy2 - yy1 + 1)  # 计算h
            inter = w * h  # 交叉面积
            # 计算IOU,  相交区域 / (当前区域 + 某区域面积 - 相交区域面积)
            ovr = inter / (areas[i] + areas[order[1:]] - inter)
            # 保留IOU小于阈值的框
            inds = np.where(ovr <= thresh)[0]
            # 因为ovr数组的长度比order数组少一个,所以这里要将所有下标后移一位
            order = order[inds + 1]
        return boxes[keep]
    def detect(self, batch_imgs):
        results = self.model(batch_imgs)
        # results.print()
        result = [[[elem.item() for elem in row[:6]] for row in tensor] for tensor in results.xyxy]
        torch.cuda.empty_cache()
        return result

    def result2defect(self, results):
        # [[object,object],[object,object],[object,object]]
        temp_batch_defects = []
        for pred_boxs in results:
            temp_image_defect_list = []
            for row_info in pred_boxs:
                x1, y1, x2, y2, conf, class_id = row_info[0], row_info[1], row_info[2], row_info[3], row_info[
                    4], row_info[5]
                typeid = self.cfg_runner['type_trans_a2c'][int(class_id)]
              

                temp_image_defect = ImageDefect()
                temp_image_defect.x = x1
                temp_image_defect.y = y1
                temp_image_defect.w = x2 - x1
                temp_image_defect.h = y2 - y1
                temp_image_defect.confidence = round(conf, 3)
                temp_image_defect.type = typeid
                temp_image_defect_list.append(temp_image_defect)
            temp_batch_defects.append(temp_image_defect_list)
        return temp_batch_defects
    #坐标转换方便
    def read_data_split5(self, img0):
        # img0 = cv2.imread(img_path)
        img_list = []
        x1 = [0, 612, 1224, 1808]
        x2 = [639, 1251, 1863, 2447]
        for i in range(len(x1)):
            a = x1[i]
            b = x2[i]

            img_list.append(img0[:, a:b + 1])

        return img_list





if __name__ == '__main__':
    print('hello1')
    batch = 1
    sys_setting = MySettings()
    detect = Detector(sys_setting,11)
    path = '/home/deployer/NNL/Test/00000_2.jpg'
    a = cv2.imread(path)
    print('hello')
    imgs = [a] * batch
    print(detect.detect_test(imgs))
    
