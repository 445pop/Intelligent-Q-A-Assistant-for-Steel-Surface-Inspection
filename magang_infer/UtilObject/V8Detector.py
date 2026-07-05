import torch
import numpy as np

import random
import cv2
import os
import yaml
import time
from MyObject.ProjectConfig import MySettings
from ais_bench.infer.interface import InferSession
import torchvision


def xywh2xyxy(x):
    # Convert nx4 boxes from [x, y, w, h] to [x1, y1, x2, y2] where xy1=top-left, xy2=bottom-right
    y = x.clone() if isinstance(x, torch.Tensor) else np.copy(x)
    y[:, 0] = x[:, 0] - x[:, 2] / 2  # top left x
    y[:, 1] = x[:, 1] - x[:, 3] / 2  # top left y
    y[:, 2] = x[:, 0] + x[:, 2] / 2  # bottom right x
    y[:, 3] = x[:, 1] + x[:, 3] / 2  # bottom right y
    return y


def box_iou(box1, box2):
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


def non_max_suppression(
        prediction,
        conf_thres=0.25,
        iou_thres=0.45,
        classes=None,
        agnostic=False,
        multi_label=False,
        labels=(),
        max_det=300,
        nm=0,  # number of masks
):
    """
    Perform non-maximum suppression (NMS) on a set of boxes, with support for masks and multiple labels per box.

    Arguments:
        prediction (torch.Tensor): A tensor of shape (batch_size, num_boxes, num_classes + 4 + num_masks)
            containing the predicted boxes, classes, and masks. The tensor should be in the format
            output by a model, such as YOLO.
        conf_thres (float): The confidence threshold below which boxes will be filtered out.
            Valid values are between 0.0 and 1.0.
        iou_thres (float): The IoU threshold below which boxes will be filtered out during NMS.
            Valid values are between 0.0 and 1.0.
        classes (List[int]): A list of class indices to consider. If None, all classes will be considered.
        agnostic (bool): If True, the model is agnostic to the number of classes, and all
            classes will be considered as one.
        multi_label (bool): If True, each box may have multiple labels.
        labels (List[List[Union[int, float, torch.Tensor]]]): A list of lists, where each inner
            list contains the apriori labels for a given image. The list should be in the format
            output by a dataloader, with each label being a tuple of (class_index, x1, y1, x2, y2).
        max_det (int): The maximum number of boxes to keep after NMS.
        nm (int): The number of masks output by the model.

    Returns:
        (List[torch.Tensor]): A list of length batch_size, where each element is a tensor of
            shape (num_boxes, 6 + num_masks) containing the kept boxes, with columns
            (x1, y1, x2, y2, confidence, class, mask1, mask2, ...).
    """

    # Checks
    assert 0 <= conf_thres <= 1, f'Invalid Confidence threshold {conf_thres}, valid values are between 0.0 and 1.0'
    assert 0 <= iou_thres <= 1, f'Invalid IoU {iou_thres}, valid values are between 0.0 and 1.0'
    if isinstance(prediction, (list, tuple)):  # YOLOv8 model in validation model, output = (inference_out, loss_out)
        prediction = prediction[0]  # select only inference output

    ### mod
    prediction = torch.tensor(prediction)
    device = 'cpu'
    prediction.to(device)
    ###

    device = prediction.device
    mps = 'mps' in device.type  # Apple MPS
    if mps:  # MPS not fully supported yet, convert tensors to CPU before NMS
        prediction = prediction.cpu()
    bs = prediction.shape[0]  # batch size
    nc = prediction.shape[1] - nm - 4  # number of classes
    mi = 4 + nc  # mask start index
    xc = prediction[:, 4:mi].amax(1) > conf_thres  # candidates

    # Settings
    # min_wh = 2  # (pixels) minimum box width and height
    max_wh = 7680  # (pixels) maximum box width and height
    max_nms = 30000  # maximum number of boxes into torchvision.ops.nms()
    time_limit = 0.5 + 0.05 * bs  # seconds to quit after
    redundant = True  # require redundant detections
    multi_label &= nc > 1  # multiple labels per box (adds 0.5ms/img)
    merge = False  # use merge-NMS

    t = time.time()
    output = [torch.zeros((0, 6 + nm), device=prediction.device)] * bs
    for xi, x in enumerate(prediction):  # image index, image inference
        # Apply constraints
        # x[((x[:, 2:4] < min_wh) | (x[:, 2:4] > max_wh)).any(1), 4] = 0  # width-height
        x = x.transpose(0, -1)[xc[xi]]  # confidence

        # Cat apriori labels if autolabelling
        if labels and len(labels[xi]):
            lb = labels[xi]
            v = torch.zeros((len(lb), nc + nm + 5), device=x.device)
            v[:, :4] = lb[:, 1:5]  # box
            v[range(len(lb)), lb[:, 0].long() + 4] = 1.0  # cls
            x = torch.cat((x, v), 0)

        # If none remain process next image
        if not x.shape[0]:
            continue

        # Detections matrix nx6 (xyxy, conf, cls)
        box, cls, mask = x.split((4, nc, nm), 1)
        box = xywh2xyxy(box)  # center_x, center_y, width, height) to (x1, y1, x2, y2)
        if multi_label:
            i, j = (cls > conf_thres).nonzero(as_tuple=False).T
            x = torch.cat((box[i], x[i, 4 + j, None], j[:, None].float(), mask[i]), 1)
        else:  # best class only
            conf, j = cls.max(1, keepdim=True)
            x = torch.cat((box, conf, j.float(), mask), 1)[conf.view(-1) > conf_thres]

        # Filter by class
        if classes is not None:
            x = x[(x[:, 5:6] == torch.tensor(classes, device=x.device)).any(1)]

        # Check shape
        n = x.shape[0]  # number of boxes
        if not n:  # no boxes
            continue
        x = x[x[:, 4].argsort(descending=True)[:max_nms]]  # sort by confidence and remove excess boxes

        # Batched NMS
        c = x[:, 5:6] * (0 if agnostic else max_wh)  # classes
        boxes, scores = x[:, :4] + c, x[:, 4]  # boxes (offset by class), scores
        i = torchvision.ops.nms(boxes, scores, iou_thres)  # NMS
        i = i[:max_det]  # limit detections
        if merge and (1 < n < 3E3):  # Merge NMS (boxes merged using weighted mean)
            # update boxes as boxes(i,4) = weights(i,n) * boxes(n,4)
            iou = box_iou(boxes[i], boxes) > iou_thres  # iou matrix
            weights = iou * scores[None]  # box weights
            x[i, :4] = torch.mm(weights, x[:, :4]).float() / weights.sum(1, keepdim=True)  # merged boxes
            if redundant:
                i = i[iou.sum(1) > 1]  # require redundancy

        output[xi] = x[i]
        if mps:
            output[xi] = output[xi].to(device)
        if (time.time() - t) > time_limit:
            print(f'WARNING ?? NMS time limit {time_limit:.3f}s exceeded')
            break  # time limit exceeded

    return output


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
    # Clip bounding xyxy bounding boxes to image shape (height, width)
    if isinstance(boxes, torch.Tensor):  # faster individually
        boxes[:, 0].clamp_(0, shape[1])  # x1
        boxes[:, 1].clamp_(0, shape[0])  # y1
        boxes[:, 2].clamp_(0, shape[1])  # x2
        boxes[:, 3].clamp_(0, shape[0])  # y2
    else:  # np.array (faster grouped)
        boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, shape[1])  # x1, x2
        boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, shape[0])  # y1, y2


current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)


class Detector:

    def __init__(self,sys_setting, device_id='0'):
        from ais_bench.infer.interface import InferSession
        self.logger = sys_setting.logger
        self.cfg_runner = sys_setting.cfg_runner
        self.model_runner = sys_setting.model_runner
        # model_path = r"/home/deployer/NNL/Maintenance/weight_files/nnl640v8m-base_bs1.om"
        self.model = InferSession(device_id, sys_setting.cfg_runner['model_path'])
        self.model2 = InferSession(device_id, sys_setting.cfg_runner['model_path2'])
        # self.model = InferSession(device_id, model_path)
        self.parse_setting()
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

    def letterbox(self, img, new_shape=(640, 640), color=(114, 114, 114), auto=False, scaleFill=False, scaleup=True,
                  stride=32):
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
            dw, dh = np.mod(dw, stride), np.mod(dh, stride)  # wh padding
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
        # img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)  # add border
        return img, ratio, (dw, dh)

    def preProcess(self, img_origins, neth=640, netw=640):
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
            return img_list, info_list, shape_list
        except Exception as e:
            self.logger.info()

    def xyxy2xywh(self, x):
        # convert nx4 boxes from [x1, y1, x2, y2] to [x, y, w, h] where xy1=top-left, xy2=botttom-right
        y = np.copy(x)
        y[:, 0] = (x[:, 0] + x[:, 2]) / 2  # x center
        y[:, 1] = (x[:, 1] + x[:, 3]) / 2  # y center
        y[:, 2] = x[:, 2] - x[:, 0]  # width
        y[:, 3] = x[:, 3] - x[:, 1]  # height
        return y

    def infer_pics(self, img_list, imginfo_list, shape_list, need_bs, cu_bs):
        # if cu_bs != need_bs:
        #     temp = need_bs - cu_bs
        #     img_list += [img_list[0]] * temp
        #
        # cu_img = np.concatenate(img_list, axis=0)
        cu_img = np.pad(img_list, ((0, need_bs-cu_bs), (0, 0), (0, 0), (0, 0)), 'constant', constant_values=0)
        preds = self.model.infer([cu_img])
        # non_max_suppression
        boxout = non_max_suppression(preds, conf_thres=self.conf_thres, iou_thres=self.iou_thres)

        for idx, pred in enumerate(boxout):
            scale_coords(cu_img[idx].shape[1:], pred[:, :4], shape_list[idx][0], shape_list[idx][1])
        
        one_pic_preds = [[[elem.item() for elem in row[:6]] for row in boxout[i]] for i in range(cu_bs)]
        # one_pic_pred2 = [[[elem.item() for elem in row[:6]] for row in tensor] for tensor in boxout][1]
        return one_pic_preds

    def infer_a_pic(self, img_list, imginfo_list, shape_list, need_bs, cu_bs=1):

        return self.infer_pics(img_list, imginfo_list, shape_list, need_bs, cu_bs)[0]

    def infer_one_pic(self, img, imginfo, shape,model_id):

        # img = torch.from_numpy(img).float()  
        # img = np.concatenate((img, img), axis=0) 
        if model_id == 1:
            preds = self.model.infer([img])
        else:
            preds = self.model2.infer([img])
        # non_max_suppression
        boxout = non_max_suppression(preds, conf_thres=self.conf_thres, iou_thres=self.iou_thres)

        for idx, pred in enumerate(boxout):
            scale_coords(img[idx].shape[1:], pred[:, :4], shape[0], shape[1])

        one_pic_pred = [[[elem.item() for elem in row[:6]] for row in tensor] for tensor in boxout][0]
        # one_pic_pred2 = [[[elem.item() for elem in row[:6]] for row in tensor] for tensor in boxout][1]

        return one_pic_pred

    def detect(self, imgs):
        cu_batch_result = []
        batch_imgs, batch_imginfos, batch_shapes = self.preProcess(imgs)
        for img, imginfo, shape in zip(batch_imgs, batch_imginfos, batch_shapes):
            cu_result = self.infer_one_pic(img, imginfo, shape)
            print(imginfo, cu_result)

        # return self.infer_pics(batch_imgs, batch_imginfos, batch_shapes, need_bs=4, cu_bs=len(imgs))
    def detect_after_preProcess(self, batch_imgs, batch_imginfos, batch_shapes,model_id):
        cu_batch_result = []
        for img, imginfo, shape in zip(batch_imgs, batch_imginfos, batch_shapes):
            cu_result = self.infer_one_pic(img, imginfo,shape,model_id)
            cu_batch_result.append(cu_result)
        return cu_batch_result
# not finish 
class Detector_Batch:
    def __init__(self, sys_setting, gpu_id='0'):
        self.logger = sys_setting.logger
        

if __name__ == '__main__':
    print('hello1')
    sys_setting = MySettings()
    detect = Detector(sys_setting,11)
    a = cv2.imread("/home/deployer/NNL/Test/00000_1.jpg")
    print('hello')
    imgs = [a] * 1
    batch_imgs, batch_imginfos, batch_shapes = detect.preProcess(imgs)
    print(detect.detect_after_preProcess(batch_imgs, batch_imginfos, batch_shapes))
