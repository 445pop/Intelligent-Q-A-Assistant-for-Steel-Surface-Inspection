import cv2
import numpy as np

def get_img_dixtance(img_path,):
    # img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8),
                     cv2.IMREAD_GRAYSCALE)
    # height, width = img.shape[:]
    img = img[372:, 840:]

    col_list = np.sum(img, axis=0)
    c_m = np.max(col_list) * 5 / 16

    row_list = np.sum(img, axis=1)
    r_m = np.max(row_list) * 5 / 16

    left = 0
    right = 0
    up = 0
    down = 0

    for i in range(len(col_list)):
        if col_list[i] >= c_m:
            left = i
            break

    for j in range(len(col_list) - 1, -1, -1):
        if col_list[j] >= c_m:
            right = len(col_list) - j
            break
    for i in range(len(row_list)):
        if row_list[i] >= r_m:
            up = i
            break

    for j in range(len(row_list) - 1, -1, -1):
        if row_list[j] >= r_m:
            down = len(row_list) - j
            break
    return up, down, left, right
def findHead(src):
    # 改进寻头算法
    src = cv2.imdecode(np.fromfile(src, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    src = src[:, 860:1862]
    row, col = src.shape[:2]

    temp = src  # 通过切片截取图像的浅拷贝
    sum_list_temp = np.sum(temp, axis=1, dtype=np.int32)
    sum_list2 = sum_list_temp.T  # 转置为行向量
    minv2, maxv2, pt_min2, pt_max2 = cv2.minMaxLoc(sum_list2)

    headRow = -2  # 尾部\中间
    P2 = sum_list2
    yuzhi_zaw = 30000#障碍物阈值
    yuzhi_bj = 15000#背景阈值
    yuzhi_gc = 42000#钢材阈值
    if minv2 < 20000:  # 这张图片可能有头
        if P2[0] < yuzhi_bj and P2[1] < yuzhi_bj and P2[2] < yuzhi_bj:  # 非经验阈值
            headRow = -1  # 可能是第一张（前几张）全是背景、首部
        if P2[-1] < yuzhi_bj and P2[-2] < yuzhi_bj and P2[-3] < yuzhi_bj:
            headRow = -1
            return headRow
        for j in range(row - 1):
            if P2[j] > yuzhi_gc:  # 首部经验阈值
                headRow = j
                break
        flag_head = True
        if headRow > 0:  # 可能是障碍物，也可能是头。仅2段 即判断是否后续还是大于20000的
            for i in range(j, row - 1):
                if P2[i] < yuzhi_zaw:
                    flag_head = False
                    break
            if not flag_head:
                for j in range(i, row - 1):
                    if P2[j] > yuzhi_gc:  # 首部经验阈值
                        headRow = j
                        break
    return headRow
def findTail(src):
    # 改进寻头算法
    src = cv2.imdecode(np.fromfile(src, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    src = src[:, 900:1900]
    row, col = src.shape[:2]
    temp = src  # 通过切片截取图像的浅拷贝
    sum_list_temp = np.sum(temp, axis=1, dtype=np.int32)
    sum_list2 = sum_list_temp.T  # 转置为行向量
    minv2, maxv2, pt_min2, pt_max2 = cv2.minMaxLoc(sum_list2)

    tailRow = -2  # 中间
    P2 = sum_list2
    yuzhi_zaw = 30000
    yuzhi_bj = 15000
    yuzhi_gc = 42000
    if minv2 < 20000:  # 这张图片可能有头尾 阴影阈值
        if P2[-1] < yuzhi_bj and P2[-2] < yuzhi_bj and P2[-3] < yuzhi_bj:  # 非经验阈值
            tailRow = -1  # 阴影
        if P2[0] < yuzhi_bj and P2[1] < yuzhi_bj and P2[3] < yuzhi_bj:  # 非经验阈值
            tailRow = -1
            return tailRow
        for j in range(row - 1, -1, -1):
            if P2[j] > yuzhi_gc:  # 尾部经验阈值
                tailRow = 2048 - j
                break
        flag_tail = True
        if tailRow > 0:  # 可能是障碍物，也可能是头。即判断是否后续还是大于20000的
            for i in range(j - 1, -1, -1):
                if P2[i] < yuzhi_zaw:
                    flag_tail = False
                    break
            if not flag_tail:
                for j in range(i - 1, -1, -1):
                    if P2[j] > yuzhi_gc:  # 首部经验阈值
                        tailRow = 2048 - j
                        break
    return tailRow

def get_head_tail(src,isHead,sample_interval=10):
    # 改进寻头算法
    gray_image = cv2.imdecode(np.fromfile(src, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    kernel_size = 15
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    # 开闭运算
    gray_image = cv2.morphologyEx(gray_image, cv2.MORPH_CLOSE, kernel)
    if isHead:
        gray_image = gray_image[:, 900:1900]
    else:
        gray_image = gray_image[:, 900:1900]
    # 对每行像素值求和
    sum_list_temp = np.sum(gray_image, axis=1, dtype=np.int32)
    row_sum = sum_list_temp.T  # 转置为行向量

    is_bac = min(row_sum)<20000
    # 初始化结果点列表
    points = []
    # 遍历每个像素值曲线
    for i in range(0, len(row_sum) - sample_interval, sample_interval):
        # 当前点和下一个点的像素值差异
        diff = row_sum[i + sample_interval] - row_sum[i]
        if diff > 14000 or diff < -14000:
            points.append((i, diff))
    sorted_sequence = sorted(points, key=lambda x: x[1])
    # 取得最大的3个元素和最小的3个元素
    max_three = sorted_sequence[-3:]
    min_three = sorted_sequence[:3]

    # print("按value升序排序的序列:", sorted_sequence)
    # print("最大的3个元素:", max_three)
    # print("最小的3个元素:", min_three)

    if isHead:
        if len(max_three) == 0:  # 说明是中间图或者是背景
            if is_bac:
                flag = -1
            else:
                flag = -2
        elif len(max_three) == 1:  # 目前来看是边界值的
            flag = max_three[0][0]
        else:
            if abs(max_three[-2][1] - max_three[-1][1]) > 4000:
                flag = max_three[-1][0]
            else:
                flag = max(max_three[-2][0], max_three[-1][0])
    else:
        if len(min_three) == 0:  # 说明是中间图或者是背景
            if is_bac:
                flag = -1
            else:
                flag = -2
        elif len(min_three) == 1:  # 目前来看是边界值的
            flag = 2048 -  min_three[0][0]
        else:
            if abs(min_three[0][1] - min_three[1][1]) > 4000:
                flag = 2048 - min_three[0][0]
            else:
                flag = 2048 -  min(min_three[0][0], min_three[1][0])

    return flag
