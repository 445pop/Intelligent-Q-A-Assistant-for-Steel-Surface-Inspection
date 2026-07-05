# 定义一个函数，计算两个缺陷框的并集（即包含两个矩形的最小矩形）
import copy
import uuid


def group_boxes_by_x(boxes, x_error, flag_group):
    """
    Group defect boxes by x-coordinate with a specified error interval.
    :param boxes: a list of defect boxes (x, y, w, h).
    :param x_error: error interval for x-coordinate grouping.
    :return: a 2D list representing grouped defect boxes.
    """
    boxes = sorted(boxes, key=lambda x: x[0])  # Sort boxes based on x-coordinate
    grouped_boxes = []
    if flag_group == 'lx':  # d对于连续性跨图，尽量保持越细越好的原则。不要出现聚合了别的框。
        start = 0
    elif flag_group == 'zq':  # 对于周期性，尽量保持越粗越好的原则。保证因振动偏移，覆盖到了尽可能符合周期的目标。
        start = -1
    else:
        start = 0
    while len(boxes) > 0:
        current_box = boxes[0]
        current_group = [current_box]
        to_remove = [0]

        # Identify and mark boxes for removal
        for i in range(1, len(boxes)):

            if abs(boxes[i][0] - current_group[start][0]) <= x_error:
                current_group.append(boxes[i])
                to_remove.append(i)
            else:
                break

        # Remove marked boxes in reverse order to avoid index issues
        for index in reversed(to_remove):
            boxes.pop(index)

        grouped_boxes.append(current_group)

    return grouped_boxes


def group_boxes_by_y(boxes, y_error, flag_group):
    """
    Group defect boxes by x-coordinate with a specified error interval.
    :param boxes: a list of defect boxes (x, y, w, h).
    :param y_error: error interval for x-coordinate grouping.
    :return: a 2D list representing grouped defect boxes.
    """
    boxes = sorted(boxes, key=lambda x: x[1])  # Sort boxes based on y-coordinate
    grouped_boxes = []
    if flag_group == 'lx':  # d对于连续性跨图，尽量保持越细越好的原则。不要出现聚合了别的框。
        start = 0
    elif flag_group == 'zq':  # 对于周期性，尽量保持越粗越好的原则。保证因振动偏移，覆盖到了尽可能符合周期的目标。
        start = -1
    else:
        start = 0
    while len(boxes) > 0:
        current_box = boxes[0]
        current_group = [current_box]
        to_remove = [0]

        # Identify and mark boxes for removal
        for i in range(1, len(boxes)):

            if abs(boxes[i][1] - current_group[start][1]) <= y_error:
                current_group.append(boxes[i])
                to_remove.append(i)
            else:
                break

        # Remove marked boxes in reverse order to avoid index issues
        for index in reversed(to_remove):
            boxes.pop(index)

        grouped_boxes.append(current_group)

    return grouped_boxes


class Aggregation:
    def __init__(self):
        self.flag_group_x = 'lx'
        self.flag_group_y = 'lx'

    def get_union(self, bbox1, bbox2):
        # 获取两个缺陷框的左上角和右下角坐标，并计算出并集矩形的左上角和右下角坐标
        x1, y1, w1, h1, cluster1 = bbox1
        x2, y2, w2, h2, cluster2 = bbox2
        x3 = min(x1, x2)
        y3 = min(y1, y2)
        x4 = max(x1 + w1, x2 + w2)
        y4 = max(y1 + h1, y2 + h2)
        # 返回并集矩形的左上角坐标和宽高
        return x3, y3, x4 - x3, y4 - y3, cluster2 + cluster1

    # 总缺陷合并
    def mergeBoxs(self, defect_list, img_height, s_threshold=0.1, x_error=10, y_error=13911):
        # 列表元素是json
        boundaries = []
        # temp_list = copy.copy(defect_list)
        for index, item in enumerate(defect_list):
            x = int(item['x'])
            y = int(item['y']) + int(item['flow_id']) * img_height
            w = int(item['w'])
            h = int(item['h'])
            box = (x, y, w, h, [index])
            boundaries.append(box)
        # 对boxlist进行检测合并.
        boundaries2 = self.merge_overlapping_defects(boundaries)
        boundaries3 = self.merge_boxes_by_group_threshold(boundaries2, s_threshold, x_error, y_error)
        return boundaries3

    def merge_boxes_by_group_threshold(self, boxs, S_threshold, x_error=10, y_error=13911):
        grouped_boxes_x = group_boxes_by_x(boxs, x_error, self.flag_group_x)

        # Display the grouped boxes
        merged_boxs = []
        for i, group1 in enumerate(grouped_boxes_x):
            grouped_boxes_y = group_boxes_by_y(group1, y_error, self.flag_group_y)
            for i, group2 in enumerate(grouped_boxes_y):
                temp = self.merge_boxes_by_S_threshold(group2, S_threshold)
                temp = self.merge_overlapping_defects(temp)
                merged_boxs += temp
        return merged_boxs

    # 缺陷信息合并，返回合并后的缺陷字典,这里的类型有：如果合并了疑似的，那么他就是疑似。否则还是原来的类型
    # 输入的是不同类型进行聚合。

    def target_types_defect_merge(self, defectList, img_height, s_threshold=0.1, x_error=10, y_error=13911):
        merge_list = []
        boxlist = self.mergeBoxs(defectList, img_height, s_threshold, x_error, y_error)
        # 对合并的框进行赋值，并把多余的删掉 保证合并后的框概率较大，似乎太低会被清除(可在这里尝试置信度提高)
        for i, box in enumerate(boxlist):
            raw_img_defect_ids = []
            raw_img_defect_scores = []
            raw_img_defect = []
            steel_defect_id = str(uuid.uuid4())
            for j in box[4]:
                # 追加id与置信度
                raw_img_defect_ids.append(defectList[j]['id'])
                raw_img_defect_scores.append(defectList[j]['confidence'])
                raw_img_defect.append(defectList[j])
                
            merge_list.append({
                'steel_defect_id': steel_defect_id,
                'x': box[0],
                'y': box[1],
                'w': box[2],
                'h': box[3],
                'type': defectList[box[4][0]]['type'],
                'confidence': round(sum(raw_img_defect_scores) / len(box[4]), 3),
                'image_defect_ids_text': ",".join(raw_img_defect_ids),
                'img_defect': raw_img_defect
            })

        return merge_list

    def one_pic_target_types_defect_merge(self, defectList, class_id , s_threshold=0.1, x_error=10, y_error=13911):
        merge_list = []
        boxlist = self.one_pic_mergeBoxs(defectList, s_threshold, x_error, y_error)
        # 对合并的框进行赋值，并把多余的删掉 保证合并后的框概率较大，似乎太低会被清除(可在这里尝试置信度提高)
        for i, box in enumerate(boxlist):
            raw_img_defect_scores = []
            steel_defect_id = str(uuid.uuid4())
            for j in box[4]:
                # 追加id与置信度
                raw_img_defect_scores.append(defectList[j][4])
            merge_list.append([box[0],box[1],box[0]+box[2],box[1]+box[3],round(sum(raw_img_defect_scores) / len(box[4]), 3),class_id])
            # merge_list.append({
            #     'steel_defect_id': steel_defect_id,
            #     'x': box[0],
            #     'y': box[1],
            #     'w': box[2],
            #     'h': box[3],
            #     'type': defectList[box[4][0]]['type'],
            #     'confidence': round(sum(raw_img_defect_scores) / len(box[4]), 3),
            #     'image_defect_ids_text': ",".join(raw_img_defect_ids),
            #     'img_defect': raw_img_defect
            # })
        return merge_list

    def one_pic_mergeBoxs(self, defect_list, s_threshold=0.1, x_error=10, y_error=13911):
        boundaries = []
        for index, item in enumerate(defect_list):
            x1, y1, x2, y2, conf, class_id = int(item[0]), int(item[1]), int(item[2]), int(
                item[3]), float(item[4]), int(item[5])
            x = x1
            y = y1
            w = x2-x1
            h = y2-y1
            box = (x, y, w, h, [index])
            boundaries.append(box)
        boundaries2 = self.merge_overlapping_defects(boundaries)
        boundaries3 = self.merge_boxes_by_group_threshold(boundaries2, s_threshold, x_error, y_error)
        return boundaries3

    def merge_overlapping_defects(self, defect_list):
        # defect_list = defect_list1.copy()
        merged_list = []
        while len(defect_list) > 0:
            defect = defect_list.pop(0)
            merged = False
            for i, merged_defect in enumerate(merged_list):
                if self.is_overlapping(defect, merged_defect):
                    merged_list[i] = self.get_union(defect, merged_defect)
                    merged = True
                    break
            if not merged:
                merged_list.append(defect)
        return merged_list

    def is_overlapping(self, rect1, rect2):
        x1, y1, w1, h1, _ = rect1
        x2, y2, w2, h2, _ = rect2

        # 计算矩形框的右下角坐标
        x1_right = x1 + w1
        y1_bottom = y1 + h1
        x2_right = x2 + w2
        y2_bottom = y2 + h2

        # 检查 rect1 是否在 rect2 的左侧
        if x1_right <= x2 or x2_right <= x1:
            return False

        # 检查 rect1 是否在 rect2 的上方
        if y1_bottom <= y2 or y2_bottom <= y1:
            return False

        # 如果上述两个条件都不满足，则矩形框有重叠区域
        return True

    def calculate_overlap_area(self, box1, box2):
        x_overlap = max(0, min(box1[0] + box1[2], box2[0] + box2[2]) - max(box1[0], box2[0]))
        y_overlap = max(0, min(box1[1] + box1[3], box2[1] + box2[3]) - max(box1[1], box2[1]))
        overlap_area = x_overlap * y_overlap
        return overlap_area

    # 根据合并前后面积比来进行合并
    def merge_boxes_by_S_threshold(self, boxs, threshold):
        """
        Merge defect boxes with overlap less than 80%.
        :param boxes: a list of defect boxes (x, y, w, h).
        :return: a list of merged defect boxes.
        """
        boxes = boxs.copy()
        smallBoxOccupy = [box[2] * box[3] for box in boxes]
        merged_boxes = []
        while len(boxes) > 0:
            box = boxes.pop(0)
            # 第一次是小图100%，第n次是大图中小图占比面积
            temp_area = smallBoxOccupy.pop(0)
            merged = False
            for i in range(len(boxes)):
                # 计算合并大图面积
                bigPicbox = self.get_union(box, boxes[i])
                # 计算重叠面积
                area1 = self.calculate_overlap_area(box, boxes[i])
                # Check if the overlap is less than 80%.
                # area1 = box[2] * box[3]
                area2 = boxes[i][2] * boxes[i][3]
                area3 = bigPicbox[2] * bigPicbox[3]
                current_small_area = temp_area + area2 - area1
                if current_small_area / area3 < threshold:
                    if not self.is_overlapping(box, boxes[i]):
                        continue

                # 被合并的删掉
                merged = True
                boxes.pop(i)
                smallBoxOccupy.pop(i)
                # 新的大图增加
                boxes.append(bigPicbox)
                smallBoxOccupy.append(current_small_area)
                break

            if not merged:
                merged_boxes.append(box)

        return merged_boxes
