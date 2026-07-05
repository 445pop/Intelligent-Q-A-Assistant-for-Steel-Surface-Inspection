import functools
import glob
import json
import os

import cv2
import numpy as np
import torch





def select_device(device='', batch_size=0, newline=True):
    # device = None or 'cpu' or 0 or '0' or '0,1,2,3'
    s = f'YOLOv5 🚀 '
    device = str(device).strip().lower().replace('cuda:', '').replace('none', '')  # to string, 'cuda:0' to '0'
    cpu = device == 'cpu'
    mps = device == 'mps'  # Apple Metal Performance Shaders (MPS)
    if cpu or mps:
        os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # force torch.cuda.is_available() = False
    elif device:  # non-cpu device requested
        os.environ['CUDA_VISIBLE_DEVICES'] = device  # set environment variable - must be before assert is_available()
        assert torch.cuda.is_available() and torch.cuda.device_count() >= len(device.replace(',', '')), \
            f"Invalid CUDA '--device {device}' requested, use '--device cpu' or pass valid CUDA device(s)"

    if not cpu and not mps and torch.cuda.is_available():  # prefer GPU if available
        devices = device.split(',') if device else '0'  # range(torch.cuda.device_count())  # i.e. 0,1,6,7
        n = len(devices)  # device count
        if n > 1 and batch_size > 0:  # check batch_size is divisible by device_count
            assert batch_size % n == 0, f'batch-size {batch_size} not multiple of GPU count {n}'
        space = ' ' * (len(s) + 1)
        for i, d in enumerate(devices):
            p = torch.cuda.get_device_properties(i)
            s += f"{'' if i == 0 else space}CUDA:{d} ({p.name}, {p.total_memory / (1 << 20):.0f}MiB)\n"  # bytes to MB
        arg = 'cuda:0'
    elif mps and getattr(torch, 'has_mps', False) and torch.backends.mps.is_available():  # prefer MPS if available
        s += 'MPS\n'
        arg = 'mps'
    else:  # revert to CPU
        s += 'CPU\n'
        arg = 'cpu'

    if not newline:
        s = s.rstrip()

    return torch.device(arg)

def generate_labelme_json(coord_type, coordinates, image_path, label_name="object"):
    """
    Generate labelme json file.

    Args:
        coord_type (str): Type of coordinates, either "xy" or "xywh".
        coordinates (list): List of coordinates. If coord_type is "xy", each coordinate should be a list of [x, y] pairs.
                            If coord_type is "xywh", each coordinate should be a list of [x, y, width, height].
        image_path (str): Path to the image associated with the annotations.
        label_name (str): Label name for the annotations.

    Returns:
        str: JSON string representing the labelme annotation.
    """
    if coord_type not in ["xy", "xywh"]:
        raise ValueError("Invalid coordinate type. It should be either 'xy' or 'xywh'.")

    image_dir = os.path.dirname(image_path)
    image_filename = os.path.basename(image_path)

    shapes = []
    for coord in coordinates:
        if coord_type == "xy":
            x, y = coord
            shape = {
                "label": label_name,
                "points": [[x, y], [x + 10, y + 10]],  # Example points, modify as needed
                "group_id": None,
                "shape_type": "rectangle",
                "flags": {}
            }
        elif coord_type == "xywh":
            x, y, w, h,ty = coord
            shape = {
                "label": ty,
                "points": [[x, y], [x + w, y + h]],  # Example points, modify as needed
                "group_id": None,
                "shape_type": "rectangle",
                "flags": {}
            }
        shapes.append(shape)

    data = {
        "version": "4.5.6",
        "flags": {},
        "shapes": shapes,
        "imagePath": image_filename,
        "imageData": None,
        "imageHeight": 512,  # Example image height, modify as needed
        "imageWidth": 650,   # Example image width, modify as needed
    }

    json_filename = os.path.splitext(image_filename)[0] + ".json"
    json_path = os.path.join(image_dir, json_filename)

    with open(json_path, 'w') as json_file:
        json.dump(data, json_file, indent=2)

    return json_path

if __name__ == '__main__':
    folder_path = r"../yolov5/infer/data/images"

    path_weight3 = r'../yolov5/infer/yolov5s.pt'


    # get_conclusion(dic_defect_labelme, dic_defect_model1)
    device = select_device('0')

    model = torch.hub.load(r'/home/asus/XX_infer_project/yolov5/infer', 'custom', path=path_weight3, source='local',
                           autoshape=True)
    model.conf = 0.01
    model.half()
    model.to(device).eval()
    dic_defect_list = []
    image_files = glob.glob(os.path.join(folder_path, '*.jpg'))
    for image_file in image_files:
        image = cv2.imread(image_file)
        results = model([image])

        result = [[[elem.item() for elem in row[:6]] for row in tensor] for tensor in results.xyxy]
        current_boxs = []

        for defect in result[0]:

            x = int(defect[0])
            y = int(defect[1])
            w = int(defect[2]) - x
            h = int(defect[3]) - y
            type1 = results.names[int(defect[5])]
            print(x,y,w,h,type1)

