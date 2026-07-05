import multiprocessing
import threading
import traceback

import cv2
import numpy as np

# from UtilObject.V8Detector import Detector


class InferProcess(multiprocessing.Process):
    def __init__(self, device_id, daemon=True):

        multiprocessing.Process.__init__(self, daemon=daemon)
        self.device_id = device_id
        self.alive = multiprocessing.Value('i', 1)
    # 每次批次更新前读取评级文件

    def run(self):
        print('InferProcess {} start running'.format(self.device_id))
        while self.alive.value:
            try:
                # 创建消费者线程
                consumer_thread1 = threading.Thread(target=self.consumer, args=(1,))
                consumer_thread1.start()
                consumer_thread1.join()

            except Exception as e:
                print('threading prediction error')
                print(traceback.format_exc())
        print('InferProcess over running')


    def hw_pre_func(self, img_origins, neth=640, netw=640):
        """
        对输入的图像进行预处理，包括调整图像大小、归一化等，并返回处理后的图像列表、图像信息列表和图像形状列表。

        Args:
            img_origins (list[np.ndarray]): 原始图像列表，每个元素为一张图像的NumPy数组，形状为(H, W, C)。
            neth (int): 目标图像的高度。
            netw (int): 目标图像的宽度。

        Returns:
            tuple[list[np.ndarray], list[np.ndarray], list[tuple]]: 包含三个列表的元组，分别代表：
            - 处理后的图像列表，每个元素为一张处理后的图像的NumPy数组，形状为(1, C, H, W)，像素值范围在0到1之间，数据类型为np.float16。
            - 图像信息列表，每个元素为一张图像的信息，包括目标图像的高度、宽度、原始图像的高度和宽度，数据类型为np.float16。
            - 图像形状列表，每个元素为一个元组，包含原始图像的形状和填充信息。

        """
        img_list = []
        info_list = []
        shape_list = []
        for img_origin in img_origins:
            imgh, imgw = img_origin.shape[:2]
            img_origin, ratio, pad = self.letterbox(img_origin, new_shape=(neth, netw))
            shape = (imgh, imgw), ((img_origin.shape[0] / imgh, img_origin.shape[1] / imgw), pad)
            img_info = np.stack([np.array([neth, netw, imgh, imgw], dtype=np.float16)], axis=0)
            img_origin = (np.stack([img_origin], axis=0))

            img = img_origin[..., ::-1].transpose(0, 3, 1, 2)  # BGR tp RGB HWC to CHW
            image_np = np.array(img, dtype=np.float32)  # img 转换为NumPy数组
            image_np_expanded = image_np / 255.0  # 像素值进行归一化，将值范围从0到255缩放到0到1之间
            img = np.ascontiguousarray(image_np_expanded).astype(
                np.float16)  # image_np_expanded 转换为一个以连续内存存储的NumPy数组
            img_list.append(img)
            info_list.append(img_info)
            shape_list.append(shape)

        return img_list, info_list, shape_list

    def letterbox(self, img, new_shape=(640, 640), color=(114, 114, 114), auto=False, scaleFill=False, scaleup=True):
        """
        对输入图像进行letterbox调整，返回调整后的图像，比例和填充大小。

        Args:
            img: 输入图像，形状为(H, W, C)的ndarray数组。
            new_shape: 调整后的目标形状，可以是单个整数或元组(width, height)，表示宽度和高度。默认为(640, 640)。
            color: 填充边框的颜色，表示为(B, G, R)格式的元组，取值范围为0-255。默认为(114, 114, 114)。
            auto: 是否自动调整边框大小，使得宽度和高度均为32的倍数。默认为False。
            scaleFill: 是否进行等比缩放填充，若为True则忽略auto参数。默认为False。
            scaleup: 是否允许放大图像，若为False则只进行缩小操作。默认为True。

        Returns:
            tuple: 包含三个元素的元组，分别为调整后的图像、宽度和高度的缩放比例以及填充的大小。
                - 调整后的图像：形状为(H, W, C)的ndarray数组。
                - 缩放比例：表示宽度和高度的缩放比例，为(width_ratio, height_ratio)格式的元组。
                - 填充的大小：表示在图像四周填充的像素大小，为(left, right, top, bottom)格式的元组。

        """
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


    def consumer(self, index_c):
        import time
        from ais_bench.infer.interface import InferSession
        self.model = InferSession(index_c, '/home/hongtai/yolo/magang_infer/SteelDefectDetection-magang/magang_infer/Maintenance/weight_files/best_1020.om')
        self.model2 = InferSession(index_c, '/home/hongtai/yolo/magang_infer/SteelDefectDetection-magang/magang_infer/Maintenance/weight_files/best_1017.om')
        pic_blocks = [cv2.imread('/home/hongtai/yolo/export_es/export_label/20240101to20240110/20240102104748/1/2430001943_0_one_3.jpg')]
        # 如果结束信号来了，但是没有推理完
        while self.alive.value == True:
            time.sleep(0.2)
            img_list, info_list, shape_list = self.hw_pre_func(pic_blocks)
            preds = self.model.infer(img_list)
            preds2 = self.model2.infer(img_list)
            print("batch_results", len(preds) )
            print("batch_results2", len(preds2) )





