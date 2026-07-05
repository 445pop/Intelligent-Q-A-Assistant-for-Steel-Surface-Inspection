import copy
import ctypes
import os
import time

import cv2

import numpy as np

from Stitcher import Stitcher


class mainTool():

    def __init__(self, input_address, output_address):
        # 大图命名
        self.name = 'result.jpg'
        self.extension = '.jpg'
        # 大图通道格式
        self.isColorMode = False
        self.input_address = input_address
        self.output_address = output_address
        # 文件列表
        self.fileList = []
        self.dirFileDict = {}
        # 相对偏移量
        self.offsetList = []
        self.tempErrorPosList = [0]
        self.tempOffsetList = []

        self.stitcher = Stitcher()
        self.fuseMethod = "trigonometric"
        # 相对位置

        self.select = 0  # 逐行拼接（从下往上）1是向下拼接

    def resizeImg(self, image, resizeTimes, interMethod=cv2.INTER_AREA):
        """
        功能：缩放图像
        :param image:原图像
        :param resizeTimes:缩放比例
        :param interMethod: 插值方法，默认cv2.INTER_AREA
        :return:
        """
        if image.ndim == 2:
            (h, w) = image.shape
        else:
            (h, w, _) = image.shape

        resizeH = int(h * resizeTimes)
        resizeW = int(w * resizeTimes)
        # cv2.INTER_AREA是测试后最好的方法
        return cv2.resize(image, (resizeW, resizeH), interpolation=interMethod)

    def initStitcher(self, type):
        # 设置特征搜索方法
        self.stitcher.featureMethod = 'surf'
        if type == 1:
            # 设置增量搜索参数  上-下拼接
            self.stitcher.direction = 1
            self.stitcher.directIncre = 0
        elif type == 2:
            # 设置增量搜索参数  左-右拼接
            self.stitcher.direction = 2
            self.stitcher.directIncre = 0
        # 设置融合方式
        self.stitcher.fuseMethod = "trigonometric"
        self.stitcher.isColorMode = False


    def changeDirection(self, flag):
        direction = 1  # 1： 第一张图像在上，第二张图像在下；   2： 第一张图像在左，第二张图像在右；
        # 3： 第一张图像在下，第二张图像在上；   4： 第一张图像在右，第二张图像在左；
        directIncre = 1  # 拼接增长方向，可以为1. 0， -1
        if flag == 1:  # 上下拼
            self.stitcher.direction = 1
            self.stitcher.directIncre = 0
        elif flag == 2:  # 下上拼
            self.stitcher.direction = 3
            self.stitcher.directIncre = 0
        elif flag == 3:  # 左右拼
            self.stitcher.direction = 2
            self.stitcher.directIncre = 0
        elif flag == 4:  # 右左拼
            self.stitcher.direction = 4
            self.stitcher.directIncre = 0

    def get_all_file(self, input_parent_address):
        # input_parent_address = r"C:\Users\12247\Desktop\马钢\2330102134\2330102134"
        self.dirFileDict = {}
        # (True, 'C:\\Users\\12247\\Desktop\\马钢\\2330102134\\2330102134', ['中', '右', '左'])
        _, root_abs_dir, dir_list = self.get_dirList(input_parent_address)
        # file_list有序，从小到大
        for i in range(len(dir_list)):
            _, _, _, file_list = self.get_fileList(os.path.join(root_abs_dir, dir_list[i]))
            self.dirFileDict[str(dir_list[i])] = file_list
        # 逐行拼接文件顺序 左中右 右中左依次进行(序列拼接)
        # for i in range(1,len(self.dirFileDict[str(dir_list[0])])):
        #     # 偶数行 左中右
        #     if i % 2 == 0:
        #         self.fileList.append(self.dirFileDict['左'][i])
        #         self.fileList.append(self.dirFileDict['中'][i])
        #         self.fileList.append(self.dirFileDict['右'][i])
        #     else:
        #         self.fileList.append(self.dirFileDict['右'][i])
        #         self.fileList.append(self.dirFileDict['中'][i])
        #         self.fileList.append(self.dirFileDict['左'][i])
        # 逐列拼接 左中右 倒N
        # for i in range(len(dir_list)):
        #     for j in range(len(self.dirFileDict[str(dir_list[0])])):
        #         # 偶数列 从上到下
        #         # if i == 0:
        #         #     if j == 0:
        #         #         continue
        #         #     self.fileList.append(self.dirFileDict['左'][j])
        #         # elif i == 1:
        #         #     if j == len(self.dirFileDict[str(dir_list[0])])-1:
        #         #         continue
        #         #     self.fileList.append(
        #         #         self.dirFileDict['中'][len(self.dirFileDict[str(dir_list[0])]) - j - 1])
        #         # elif i == 2:
        #         #     if j == 0:
        #         #         continue
        #         #     self.fileList.append(self.dirFileDict['右'][j])
        #         # 正N型
        #         if i == 0:
        #             if j == len(self.dirFileDict[str(dir_list[0])])-1:
        #                 continue
        #             self.fileList.append(
        #                 self.dirFileDict['左'][len(self.dirFileDict[str(dir_list[0])]) - j - 1])
        #         elif i == 1:
        #             if j == 0:
        #                 continue
        #             self.fileList.append(self.dirFileDict['中'][j])
        #         elif i == 2:
        #             if j == len(self.dirFileDict[str(dir_list[0])])-1:
        #                 continue
        #
        #             self.fileList.append(
        #                 self.dirFileDict['右'][len(self.dirFileDict[str(dir_list[0])]) - j - 1])
        # 第一个图拼接dai测试
        for i in range(1, len(self.dirFileDict[str(dir_list[0])])):
            # 偶数行 左中右
            self.fileList.append(self.dirFileDict['左'][i])
            self.fileList.append(self.dirFileDict['中'][i])
            self.fileList.append(self.dirFileDict['右'][i])

    def get_offset(self, input_parent_address):
        self.initStitcher(1)
        # 获得整理好的文件
        self.get_all_file(input_parent_address)
        # 循环得到相对偏移量
        self.get_relative_offset()

    def change_file_row_col(self, oldFileList, num):
        # oldFileList ：原来的文件
        # return :新顺序文件
        # num:逐行拼接输入列数；逐列拼接输入行数

        count_file = len(oldFileList)
        shang = int(count_file / num)
        yu = int(count_file % num)
        newList = []
        # 按照行拼接或列拼接的逻辑处理
        for i in range(0, shang):
            if i % 2 == 0:
                for j in range(0, num):
                    newList.append(oldFileList[i * num + j])
            else:
                for j in range(0, num):
                    newList.append(oldFileList[(i + 1) * num - j - 1])
        # 将末尾算上
        for k in range(0, yu):
            newList.append(oldFileList[count_file - yu + k])
        return newList

    def get_fileList(self, dir):
        '''
        根据文件目录获取下面的文件列表（完整路径）
        :return:
        '''
        state = False
        root_abs_dir = ''
        output_default_name = ''
        file_list = []
        if os.path.exists(dir):
            state = True
            root_abs_dir = os.path.abspath(dir)
            output_default_name = dir.split("/")[-1] + "-stitch_result"
            for fn in os.listdir(dir):
                file_list.append(os.path.join(root_abs_dir, fn))
        return state, root_abs_dir, output_default_name, file_list

    def get_dirList(self, dir):
        '''
        获取子目录列表
        :param dir:
        :return:
        '''
        state = False
        root_abs_dir = ''
        dir_list = []
        if os.path.exists(dir):
            state = True
            root_abs_dir = os.path.abspath(dir)
            for fn in os.listdir(dir):
                dir_list.append(fn)  # 文件夹名称列表

        return state, root_abs_dir, dir_list

    def get_relative_offset(self):
        s = time.time()
        picNum = len(self.fileList) // 3
        print('picNum = ', picNum)

        for fileIndex in range(len(self.fileList) - 1):
            print("  stitching " + str(self.fileList[fileIndex]).split('/')[-1] + " and " +
                  str(self.fileList[fileIndex + 1]).split('/')[-1])
            imageA = cv2.imdecode(np.fromfile(self.fileList[fileIndex], dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            imageB = cv2.imdecode(np.fromfile(self.fileList[fileIndex + 1], dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            # 采用倒N型拼接，左中右均裁剪 以获取正确的匹配

            if fileIndex < picNum - 1:
                self.changeDirection(flag=2)  # 左列 上下拼 1340 372(宽高)
                imageB = imageB[372:, 1340:]
                imageA = imageA[372:, 1340:]
                print('l_pic', imageA.shape)
            elif fileIndex == picNum - 1:  # 左中
                self.changeDirection(flag=3)
                self.offsetList.append(fileIndex)
                continue
            elif fileIndex < 2 * picNum - 1:  # 中列 下上拼
                self.changeDirection(flag=1)
                imageA = imageA[600:, :]
                imageB = imageB[600:, :]
                print('c_pic', imageA.shape)
            elif fileIndex == 2 * picNum - 1:
                self.changeDirection(flag=3)  # 中右
                self.offsetList.append(fileIndex)
                continue
            elif fileIndex < 3 * picNum - 1:
                self.changeDirection(flag=2)  # 右列 上下拼 (宽高) :1220 :452
                imageA = imageA[452:, :1220]
                imageB = imageB[452:, :1220]
                print('r_pic', imageA.shape)

            (status, offset) = self.stitcher.calculateOffsetForFeatureSearchIncre([imageA, imageB])
            if status == False:
                (status1, offset1) = self.stitcher.calculateOffsetForFeatureSearchIncre([imageB, imageA])
                if status1 == False:
                    describtion = "  " + str(self.fileList[fileIndex]).split('/')[-1] + " and " + str(
                        self.fileList[fileIndex + 1]).split('/')[-1] + " can not be stitched"
                    print(describtion)
                    self.offsetList.append(fileIndex)
                else:
                    aoffset = [1, 2]
                    aoffset[0] = -1 * offset1[0]
                    aoffset[1] = -1 * offset1[1]
                    self.offsetList.append(aoffset)
            else:
                self.offsetList.append(offset)

        tempPartOffsetList = []

        for i in range(0, len(self.offsetList)):
            # ----Qt信号发送（微调列表增加图片和偏移信息）----
            # 前面offsetList在第一个元素插入的(0,0)，此时数量与fileList相同
            # 把一维信息过滤,取得是拼接成功的序列
            # 出错2 - 3, 假如3张图片的result等于2比较合适
            if isinstance(self.offsetList[i], int):
                # 保存出错位置
                self.tempErrorPosList.append(self.offsetList[i])

                self.tempOffsetList.append(tempPartOffsetList)
                tempPartOffsetList = []
                # 一种情况是1-2-3-4-5，出现4-5拼接失败，或者1-2拼接失败，即首位 末尾因为无完整的offset，不能添加到临时的偏移量列表，故首尾在最后添加至图片列表中算了，还有全部出错
                if (self.offsetList[i] == len(self.offsetList) - 1):
                    self.tempErrorPosList.append(len(self.offsetList))
                    self.tempOffsetList.append(tempPartOffsetList)
            else:
                tempPartOffsetList.append(self.offsetList[i])
                if i == len(self.offsetList) - 1:
                    self.tempOffsetList.append(tempPartOffsetList)
                    self.tempErrorPosList.append(len(self.offsetList))
        print('耗时：', time.time() - s)

    def get_relative_offset_surf_H(self, fileList):
        offsetList = []
        for fileIndex in range(len(fileList) - 1):
            imageA = fileList[fileIndex]
            imageB = fileList[fileIndex + 1]
            # 采用倒N型拼接，左中右均裁剪 以获取正确的匹配

            (status, offset) = self.stitcher.calculateOffsetForFeatureSearchIncre([imageA, imageB])
            if status == False:
                (status1, offset1) = self.stitcher.calculateOffsetForFeatureSearchIncre([imageB, imageA])
                if status1 == False:
                    describtion = str(fileIndex) + " and " + str(fileIndex + 1) + " can not be stitched"
                    print(describtion)
                    offsetList.append(fileIndex)
                else:
                    aoffset = [1, 2]
                    aoffset[0] = -1 * offset1[0]
                    aoffset[1] = -1 * offset1[1]
                    offsetList.append(aoffset)
            else:
                offsetList.append(offset)
        return offsetList

    def get_relative_offset_has_exp(self, fileList, exp):
        # exp = [100, 100]
        offsetList = []
        for fileIndex in range(len(fileList) - 1):
            imageA = fileList[fileIndex]
            imageB = fileList[fileIndex + 1]
            # 采用倒N型拼接，左中右均裁剪 以获取正确的匹配

            (status, offset) = self.stitcher.calculateOffsetForFeatureSearchIncre([imageA, imageB])
            if status == False:
                offsetList.append(exp)
            else:
                offsetList.append(offset)
        return offsetList

    def get_temp_offsetList_surf_H(self, offsetList):
        tempPartOffsetList = []
        tempErrorPosList = [0]
        tempOffsetList = []
        for i in range(0, len(offsetList)):
            # ----Qt信号发送（微调列表增加图片和偏移信息）----
            # 前面offsetList在第一个元素插入的(0,0)，此时数量与fileList相同
            # 把一维信息过滤,取得是拼接成功的序列
            # 出错2 - 3, 假如3张图片的result等于2比较合适
            if isinstance(offsetList[i], int):
                # 保存出错位置
                tempErrorPosList.append(offsetList[i])

                tempOffsetList.append(tempPartOffsetList)
                tempPartOffsetList = []
                # 一种情况是1-2-3-4-5，出现4-5拼接失败，或者1-2拼接失败，即首位 末尾因为无完整的offset，不能添加到临时的偏移量列表，故首尾在最后添加至图片列表中算了，还有全部出错
                if (offsetList[i] == len(offsetList) - 1):
                    tempErrorPosList.append(len(offsetList))
                    tempOffsetList.append(tempPartOffsetList)
            else:
                tempPartOffsetList.append(offsetList[i])
                if i == len(offsetList) - 1:
                    tempOffsetList.append(tempPartOffsetList)
                    tempErrorPosList.append(len(offsetList))
        return tempOffsetList, tempErrorPosList

    def get_relative_offset_group_surf_H(self, fileList):
        offsetList = self.get_relative_offset_surf_H(fileList)
        tempOffsetList, tempErrorPosList = self.get_temp_offsetList_surf_H(offsetList)
        return tempOffsetList, tempErrorPosList

    def write_all_pic(self):
        stitchImagesNames = []
        if (self.name is not None):
            if len(self.tempOffsetList) == 1:
                stitchImagesNames.append(self.name)
            else:
                name_not_file_extension = self.name.split('.')[0]
                file_extension = self.name.split('.')[-1]
                for j in range(0, len(self.tempOffsetList)):
                    stitchImagesNames.append(name_not_file_extension + "_" + str(j + 1) + "." + file_extension)
        for j in range(0, len(self.tempOffsetList)):
            # 参数是对应的图0：26，（0,25）；26:38，（26,37）的图...
            # 内含join方法，即循环是完成一个进行下一个，多线程？
            if (j == 0):
                self.write_pic(self.fileList[self.tempErrorPosList[0]:self.tempErrorPosList[1] + 1],
                               self.tempOffsetList[0],
                               self.output_address, stitchImagesNames[0])
            else:
                self.write_pic(self.fileList[self.tempErrorPosList[j] + 1:self.tempErrorPosList[j + 1] + 1],
                               self.tempOffsetList[j], self.output_address, stitchImagesNames[j])

    def write_all_pic_surf_H(self, tempOffsetList, fileList, tempErrorPosList):
        stitchImagesNames = []
        if (self.name is not None):
            if len(tempOffsetList) == 1:
                stitchImagesNames.append(self.name)
            else:
                name_not_file_extension = self.name.split('.')[0]
                file_extension = self.name.split('.')[-1]
                for j in range(0, len(tempOffsetList)):
                    stitchImagesNames.append(name_not_file_extension + "_" + str(j + 1) + "." + file_extension)
        for j in range(0, len(tempOffsetList)):
            # 参数是对应的图0：26，（0,25）；26:38，（26,37）的图...
            # 内含join方法，即循环是完成一个进行下一个，多线程？
            if (j == 0):
                self.write_pic_surf_H(fileList[tempErrorPosList[0]:tempErrorPosList[1] + 1],
                                      tempOffsetList[0],
                                      self.output_address, stitchImagesNames[0])
            else:
                self.write_pic_surf_H(fileList[tempErrorPosList[j] + 1:tempErrorPosList[j + 1] + 1],
                                      tempOffsetList[j], self.output_address, stitchImagesNames[j])

    def write_pic(self, fileList, originOffsetList, output_address=None, name=None):
        '''
            功能：通过偏移量列表和文件列表得到最终的拼接结果,并写入到文件中
            :param fileList: 图像列表
            :param indexqueue: 计数队列
            :param originOffsetList: 偏移量列表
            :param output_address: 输出文件夹
            :param name: 文件名
            '''
        # 如果你不细心，不要碰这段代码
        # 已优化到根据指针来控制拼接，CPU下最快了

        # 合成图之前假设内存足够，初始化.假如最后一张图存的上，但还是拼接失败，那只初始化一遍？点击拼接线程
        # self.is_can_save = True

        dxSum = dySum = 0
        tempImage = None
        # imageList.append(cv2.imread(fileList[0], 0))
        if self.isColorMode:
            tempImage = cv2.imdecode(np.fromfile(fileList[0], dtype=np.uint8), cv2.IMREAD_COLOR)
        else:
            tempImage = cv2.imdecode(np.fromfile(fileList[0], dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        resultRow = tempImage.shape[0]  # 拼接最终结果的横轴长度,先赋值第一个图像的横轴
        resultCol = tempImage.shape[1]  # 拼接最终结果的纵轴长度,先赋值第一个图像的纵轴
        originOffsetList.insert(0, [0, 0])  # 增加第一张图像相对于最终结果的原点的偏移量

        rangeX = [[0, 0] for x in range(len(originOffsetList))]  # 主要用于记录X方向最大最小边界
        rangeY = [[0, 0] for x in range(len(originOffsetList))]  # 主要用于记录Y方向最大最小边界
        # print("originOffsetList=",originOffsetList)
        offsetList = copy.deepcopy(originOffsetList)
        rangeX[0][1] = tempImage.shape[0]
        rangeY[0][1] = tempImage.shape[1]

        print('------------------------offsetList-----------------------\noffsetList=', offsetList)
        # offsetList= [[0, 0], [-35, -513], [-16, -565], [6, -543]]

        for i in range(1, len(offsetList)):
            # self.printAndWrite("  stitching " + str(fileList[i]))
            # 适用于流形拼接的校正,并更新最终图像大小
            # tempImage = cv2.imread(fileList[i], 0)
            # Stitcher.isColorMode修改为self.isColorMode【2021.12.21】，避免单独对Stitcher对象修改isCorlorMode不生效
            dxSum = dxSum + offsetList[i][0]
            dySum = dySum + offsetList[i][1]
            # self.printAndWrite("  The dxSum is " + str(dxSum) + " and the dySum is " + str(dySum))
            if dxSum < 0:
                for j in range(0, i):
                    offsetList[j][0] = offsetList[j][0] + abs(dxSum)
                    rangeX[j][0] = rangeX[j][0] + abs(dxSum)
                    rangeX[j][1] = rangeX[j][1] + abs(dxSum)
                resultRow = resultRow + abs(dxSum)
                rangeX[i][1] = resultRow
                dxSum = rangeX[i][0] = offsetList[i][0] = 0
            else:
                offsetList[i][0] = dxSum
                resultRow = max(resultRow, dxSum + tempImage.shape[0])
                rangeX[i][1] = resultRow
            if dySum < 0:
                for j in range(0, i):
                    offsetList[j][1] = offsetList[j][1] + abs(dySum)
                    rangeY[j][0] = rangeY[j][0] + abs(dySum)
                    rangeY[j][1] = rangeY[j][1] + abs(dySum)
                resultCol = resultCol + abs(dySum)
                rangeY[i][1] = resultCol
                dySum = rangeY[i][0] = offsetList[i][1] = 0
            else:
                offsetList[i][1] = dySum
                resultCol = max(resultCol, dySum + tempImage.shape[1])
                rangeY[i][1] = resultCol

        is_small = True

        if is_small:
            print('使用内存存储')

            self.writeSmallPic(fileList, offsetList, originOffsetList,
                               resultRow, resultCol, rangeX, rangeY, name,
                               output_address)

    def write_pic_surf_H(self, fileList, originOffsetList, output_address=None, name=None):
        '''
            功能：通过偏移量列表和文件列表得到最终的拼接结果,并写入到文件中
            :param fileList: 图像列表
            :param indexqueue: 计数队列
            :param originOffsetList: 偏移量列表
            :param output_address: 输出文件夹
            :param name: 文件名
            '''
        # 如果你不细心，不要碰这段代码
        # 已优化到根据指针来控制拼接，CPU下最快了

        # 合成图之前假设内存足够，初始化.假如最后一张图存的上，但还是拼接失败，那只初始化一遍？点击拼接线程
        # self.is_can_save = True

        dxSum = dySum = 0
        tempImage = fileList[0]
        # imageList.append(cv2.imread(fileList[0], 0))
        # if self.isColorMode:
        #     tempImage = cv2.imdecode(np.fromfile(fileList[0], dtype=np.uint8), cv2.IMREAD_COLOR)
        # else:
        #     tempImage = cv2.imdecode(np.fromfile(fileList[0], dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        resultRow = tempImage.shape[0]  # 拼接最终结果的横轴长度,先赋值第一个图像的横轴
        resultCol = tempImage.shape[1]  # 拼接最终结果的纵轴长度,先赋值第一个图像的纵轴
        originOffsetList.insert(0, [0, 0])  # 增加第一张图像相对于最终结果的原点的偏移量

        rangeX = [[0, 0] for x in range(len(originOffsetList))]  # 主要用于记录X方向最大最小边界
        rangeY = [[0, 0] for x in range(len(originOffsetList))]  # 主要用于记录Y方向最大最小边界
        # print("originOffsetList=",originOffsetList)
        offsetList = copy.deepcopy(originOffsetList)
        rangeX[0][1] = tempImage.shape[0]
        rangeY[0][1] = tempImage.shape[1]

        print('------------------------offsetList-----------------------\noffsetList=', offsetList)
        # offsetList= [[0, 0], [-35, -513], [-16, -565], [6, -543]]

        for i in range(1, len(offsetList)):
            # self.printAndWrite("  stitching " + str(fileList[i]))
            # 适用于流形拼接的校正,并更新最终图像大小
            # tempImage = cv2.imread(fileList[i], 0)
            # Stitcher.isColorMode修改为self.isColorMode【2021.12.21】，避免单独对Stitcher对象修改isCorlorMode不生效
            dxSum = dxSum + offsetList[i][0]
            dySum = dySum + offsetList[i][1]
            # self.printAndWrite("  The dxSum is " + str(dxSum) + " and the dySum is " + str(dySum))
            if dxSum < 0:
                for j in range(0, i):
                    offsetList[j][0] = offsetList[j][0] + abs(dxSum)
                    rangeX[j][0] = rangeX[j][0] + abs(dxSum)
                    rangeX[j][1] = rangeX[j][1] + abs(dxSum)
                resultRow = resultRow + abs(dxSum)
                rangeX[i][1] = resultRow
                dxSum = rangeX[i][0] = offsetList[i][0] = 0
            else:
                offsetList[i][0] = dxSum
                resultRow = max(resultRow, dxSum + tempImage.shape[0])
                rangeX[i][1] = resultRow
            if dySum < 0:
                for j in range(0, i):
                    offsetList[j][1] = offsetList[j][1] + abs(dySum)
                    rangeY[j][0] = rangeY[j][0] + abs(dySum)
                    rangeY[j][1] = rangeY[j][1] + abs(dySum)
                resultCol = resultCol + abs(dySum)
                rangeY[i][1] = resultCol
                dySum = rangeY[i][0] = offsetList[i][1] = 0
            else:
                offsetList[i][1] = dySum
                resultCol = max(resultCol, dySum + tempImage.shape[1])
                rangeY[i][1] = resultCol

        self.writeSmallPic_surf_H(fileList, offsetList, originOffsetList,
                                  resultRow, resultCol, rangeX, rangeY, name,
                                  output_address)

    def get_stitch_pic(self, fileList, originOffsetList):
        '''
            功能：通过偏移量列表和文件列表得到最终的拼接结果,并写入到文件中
            :param fileList: 图像列表
            :param indexqueue: 计数队列
            :param originOffsetList: 偏移量列表
            :param output_address: 输出文件夹
            :param name: 文件名
            '''
        # 如果你不细心，不要碰这段代码
        # 已优化到根据指针来控制拼接，CPU下最快了

        # 合成图之前假设内存足够，初始化.假如最后一张图存的上，但还是拼接失败，那只初始化一遍？点击拼接线程
        # self.is_can_save = True

        dxSum = dySum = 0
        tempImage = fileList[0]
        # imageList.append(cv2.imread(fileList[0], 0))
        # if self.isColorMode:
        #     tempImage = cv2.imdecode(np.fromfile(fileList[0], dtype=np.uint8), cv2.IMREAD_COLOR)
        # else:
        #     tempImage = cv2.imdecode(np.fromfile(fileList[0], dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        resultRow = tempImage.shape[0]  # 拼接最终结果的横轴长度,先赋值第一个图像的横轴
        resultCol = tempImage.shape[1]  # 拼接最终结果的纵轴长度,先赋值第一个图像的纵轴
        originOffsetList.insert(0, [0, 0])  # 增加第一张图像相对于最终结果的原点的偏移量

        rangeX = [[0, 0] for x in range(len(originOffsetList))]  # 主要用于记录X方向最大最小边界
        rangeY = [[0, 0] for x in range(len(originOffsetList))]  # 主要用于记录Y方向最大最小边界
        # print("originOffsetList=",originOffsetList)
        offsetList = copy.deepcopy(originOffsetList)
        rangeX[0][1] = tempImage.shape[0]
        rangeY[0][1] = tempImage.shape[1]

        print('------------------------offsetList-----------------------\noffsetList=', offsetList)
        # offsetList= [[0, 0], [-35, -513], [-16, -565], [6, -543]]

        for i in range(1, len(offsetList)):
            # self.printAndWrite("  stitching " + str(fileList[i]))
            # 适用于流形拼接的校正,并更新最终图像大小
            # tempImage = cv2.imread(fileList[i], 0)
            # Stitcher.isColorMode修改为self.isColorMode【2021.12.21】，避免单独对Stitcher对象修改isCorlorMode不生效
            dxSum = dxSum + offsetList[i][0]
            dySum = dySum + offsetList[i][1]
            # self.printAndWrite("  The dxSum is " + str(dxSum) + " and the dySum is " + str(dySum))
            if dxSum < 0:
                for j in range(0, i):
                    offsetList[j][0] = offsetList[j][0] + abs(dxSum)
                    rangeX[j][0] = rangeX[j][0] + abs(dxSum)
                    rangeX[j][1] = rangeX[j][1] + abs(dxSum)
                resultRow = resultRow + abs(dxSum)
                rangeX[i][1] = resultRow
                dxSum = rangeX[i][0] = offsetList[i][0] = 0
            else:
                offsetList[i][0] = dxSum
                resultRow = max(resultRow, dxSum + tempImage.shape[0])
                rangeX[i][1] = resultRow
            if dySum < 0:
                for j in range(0, i):
                    offsetList[j][1] = offsetList[j][1] + abs(dySum)
                    rangeY[j][0] = rangeY[j][0] + abs(dySum)
                    rangeY[j][1] = rangeY[j][1] + abs(dySum)
                resultCol = resultCol + abs(dySum)
                rangeY[i][1] = resultCol
                dySum = rangeY[i][0] = offsetList[i][1] = 0
            else:
                offsetList[i][1] = dySum
                resultCol = max(resultCol, dySum + tempImage.shape[1])
                rangeY[i][1] = resultCol
                # 对于拼接结果是内存占比较小的图，采用内存矩阵赋值的方式

        stitchResult = None
        if self.isColorMode:
            stitchResult = np.zeros((resultRow, resultCol, 3), np.uint8)
        else:
            stitchResult = np.zeros((resultRow, resultCol), np.uint8)

        # mask = np.full((resultRow, resultCol), False, dtype=bool)  # 全 False
        mask = np.zeros((resultRow, resultCol), np.uint8)  # 全 False

        # 如上算出各个图像相对于原点偏移量，并最终计算出输出图像大小，并构造矩阵，如下开始赋值
        for i in range(len(offsetList)):
            # print("  fusing " + str(fileList[i]).split('/')[-1])
            print("  fusing ", i,self.fuseMethod)
            # if self.isColorMode:
            #     tempImage = cv2.imdecode(np.fromfile(fileList[i], dtype=np.uint8), cv2.IMREAD_COLOR)
            # else:
            #     tempImage = cv2.imdecode(np.fromfile(fileList[i], dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            tempImage = fileList[i]
            if i == 0:
                if self.isColorMode:
                    stitchResult[offsetList[0][0]: offsetList[0][0] + tempImage.shape[0],
                    offsetList[0][1]: offsetList[0][1] + tempImage.shape[1], :] = tempImage
                else:
                    stitchResult[offsetList[0][0]: offsetList[0][0] + tempImage.shape[0],
                    offsetList[0][1]: offsetList[0][1] + tempImage.shape[1]] = tempImage
                mask[offsetList[0][0]: offsetList[0][0] + tempImage.shape[0],
                offsetList[0][1]: offsetList[0][1] + tempImage.shape[1]] = 1
            else:
                if self.fuseMethod == "notFuse":
                    # 适用于无图像融合，直接覆盖
                    # self.printAndWrite("StitchUtil " + str(i+1) + "th, the roi_ltx is " + str(offsetList[i][0]) + " and the roi_lty is " + str(offsetList[i][1]))
                    if self.isColorMode:
                        stitchResult[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1], :] = tempImage
                    else:
                        stitchResult[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1]] = tempImage
                    mask[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                    offsetList[i][1]: offsetList[i][1] + tempImage.shape[1]] = 1
                else:
                    # 适用于图像融合算法，切出 roiA 和 roiB 供图像融合
                    minOccupyX = rangeX[i - 1][0]
                    maxOccupyX = rangeX[i - 1][1]
                    minOccupyY = rangeY[i - 1][0]
                    maxOccupyY = rangeY[i - 1][1]
                    # self.printAndWrite("StitchUtil " + str(i + 1) + "th, the offsetList[i][0] is " + str(
                    #     offsetList[i][0]) + " and the offsetList[i][1] is " + str(offsetList[i][1]))
                    # self.printAndWrite("StitchUtil " + str(i + 1) + "th, the minOccupyX is " + str(
                    #     minOccupyX) + " and the maxOccupyX is " + str(maxOccupyX) + " and the minOccupyY is " + str(
                    #     minOccupyY) + " and the maxOccupyY is " + str(maxOccupyY))
                    roi_ltx = max(offsetList[i][0], minOccupyX)
                    roi_lty = max(offsetList[i][1], minOccupyY)
                    roi_rbx = min(offsetList[i][0] + tempImage.shape[0], maxOccupyX)
                    roi_rby = min(offsetList[i][1] + tempImage.shape[1], maxOccupyY)
                    # self.printAndWrite("StitchUtil " + str(i + 1) + "th, the roi_ltx is " + str(
                    #     roi_ltx) + " and the roi_lty is " + str(roi_lty) + " and the roi_rbx is " + str(
                    #     roi_rbx) + " and the roi_rby is " + str(roi_rby))

                    if self.isColorMode:
                        maskA = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        roiImageRegionA = stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby, :].copy()
                        stitchResult[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1], :] = tempImage
                        mask[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1]] = 1
                        maskB = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        roiImageRegionB = stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby, :].copy()

                        stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby, :] = self.stitcher.fuseImageWithMask(
                            [roiImageRegionA, roiImageRegionB], [maskA, maskB], originOffsetList[i][0],
                            originOffsetList[i][1])
                    else:
                        maskA = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        roiImageRegionA = stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        stitchResult[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1]] = tempImage
                        mask[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1]] = 1

                        maskB = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        roiImageRegionB = stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()

                        stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby] = self.stitcher.fuseImageWithMask(
                            [roiImageRegionA, roiImageRegionB], [maskA, maskB], originOffsetList[i][0],
                            originOffsetList[i][1])
        return stitchResult


    def writeSmallPic(self, fileList, offsetList, originOffsetList, resultRow, resultCol, rangeX, rangeY,
                      name, output_address):
        # 对于拼接结果是内存占比较小的图，采用内存矩阵赋值的方式
        s = time.time()
        stitchResult = None
        if self.isColorMode:
            stitchResult = np.zeros((resultRow, resultCol, 3), np.uint8)
        else:
            stitchResult = np.zeros((resultRow, resultCol), np.uint8)

        # mask = np.full((resultRow, resultCol), False, dtype=bool)  # 全 False
        mask = np.zeros((resultRow, resultCol), np.uint8)  # 全 False

        # 如上算出各个图像相对于原点偏移量，并最终计算出输出图像大小，并构造矩阵，如下开始赋值
        for i in range(len(offsetList)):
            print("  fusing " + str(fileList[i]).split('/')[-1])
            if self.isColorMode:
                tempImage = cv2.imdecode(np.fromfile(fileList[i], dtype=np.uint8), cv2.IMREAD_COLOR)
            else:
                tempImage = cv2.imdecode(np.fromfile(fileList[i], dtype=np.uint8), cv2.IMREAD_GRAYSCALE)

            if i == 0:
                if self.isColorMode:
                    stitchResult[offsetList[0][0]: offsetList[0][0] + tempImage.shape[0],
                    offsetList[0][1]: offsetList[0][1] + tempImage.shape[1], :] = tempImage
                else:
                    stitchResult[offsetList[0][0]: offsetList[0][0] + tempImage.shape[0],
                    offsetList[0][1]: offsetList[0][1] + tempImage.shape[1]] = tempImage
                mask[offsetList[0][0]: offsetList[0][0] + tempImage.shape[0],
                offsetList[0][1]: offsetList[0][1] + tempImage.shape[1]] = 1
            else:
                if self.fuseMethod == "notFuse":
                    # 适用于无图像融合，直接覆盖
                    # self.printAndWrite("StitchUtil " + str(i+1) + "th, the roi_ltx is " + str(offsetList[i][0]) + " and the roi_lty is " + str(offsetList[i][1]))
                    if self.isColorMode:
                        stitchResult[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1], :] = tempImage
                    else:
                        stitchResult[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1]] = tempImage
                    mask[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                    offsetList[i][1]: offsetList[i][1] + tempImage.shape[1]] = 1
                else:
                    # 适用于图像融合算法，切出 roiA 和 roiB 供图像融合
                    minOccupyX = rangeX[i - 1][0]
                    maxOccupyX = rangeX[i - 1][1]
                    minOccupyY = rangeY[i - 1][0]
                    maxOccupyY = rangeY[i - 1][1]
                    # self.printAndWrite("StitchUtil " + str(i + 1) + "th, the offsetList[i][0] is " + str(
                    #     offsetList[i][0]) + " and the offsetList[i][1] is " + str(offsetList[i][1]))
                    # self.printAndWrite("StitchUtil " + str(i + 1) + "th, the minOccupyX is " + str(
                    #     minOccupyX) + " and the maxOccupyX is " + str(maxOccupyX) + " and the minOccupyY is " + str(
                    #     minOccupyY) + " and the maxOccupyY is " + str(maxOccupyY))
                    roi_ltx = max(offsetList[i][0], minOccupyX)
                    roi_lty = max(offsetList[i][1], minOccupyY)
                    roi_rbx = min(offsetList[i][0] + tempImage.shape[0], maxOccupyX)
                    roi_rby = min(offsetList[i][1] + tempImage.shape[1], maxOccupyY)
                    # self.printAndWrite("StitchUtil " + str(i + 1) + "th, the roi_ltx is " + str(
                    #     roi_ltx) + " and the roi_lty is " + str(roi_lty) + " and the roi_rbx is " + str(
                    #     roi_rbx) + " and the roi_rby is " + str(roi_rby))

                    if self.isColorMode:
                        maskA = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        roiImageRegionA = stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby, :].copy()
                        stitchResult[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1], :] = tempImage
                        mask[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1]] = 1
                        maskB = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        roiImageRegionB = stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby, :].copy()
                        stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby, :] = self.stitcher.fuseImageWithMask(
                            [roiImageRegionA, roiImageRegionB], [maskA, maskB], originOffsetList[i][0],
                            originOffsetList[i][1])
                    else:
                        maskA = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        roiImageRegionA = stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        stitchResult[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1]] = tempImage
                        mask[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1]] = 1

                        maskB = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        roiImageRegionB = stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()

                        stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby] = self.stitcher.fuseImageWithMask(
                            [roiImageRegionA, roiImageRegionB], [maskA, maskB], originOffsetList[i][0],
                            originOffsetList[i][1])

        # cv2.imencode("." + file_extension, stitchResult)[1].tofile(output_address + "/" + name)

        path = os.path.join(self.output_address, name)
        cv2.imencode(self.extension, stitchResult)[1].tofile(path)

        e = time.time()
        print('内存存储所耗时间：', e - s)

    def writeSmallPic_surf_H(self, fileList, offsetList, originOffsetList, resultRow, resultCol, rangeX, rangeY,
                             name, output_address):
        # 对于拼接结果是内存占比较小的图，采用内存矩阵赋值的方式
        s = time.time()
        stitchResult = None
        if self.isColorMode:
            stitchResult = np.zeros((resultRow, resultCol, 3), np.uint8)
        else:
            stitchResult = np.zeros((resultRow, resultCol), np.uint8)

        # mask = np.full((resultRow, resultCol), False, dtype=bool)  # 全 False
        mask = np.zeros((resultRow, resultCol), np.uint8)  # 全 False

        # 如上算出各个图像相对于原点偏移量，并最终计算出输出图像大小，并构造矩阵，如下开始赋值
        for i in range(len(offsetList)):
            # print("  fusing " + str(fileList[i]).split('/')[-1])
            print("  fusing ", i)
            # if self.isColorMode:
            #     tempImage = cv2.imdecode(np.fromfile(fileList[i], dtype=np.uint8), cv2.IMREAD_COLOR)
            # else:
            #     tempImage = cv2.imdecode(np.fromfile(fileList[i], dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            tempImage = fileList[i]
            if i == 0:
                if self.isColorMode:
                    stitchResult[offsetList[0][0]: offsetList[0][0] + tempImage.shape[0],
                    offsetList[0][1]: offsetList[0][1] + tempImage.shape[1], :] = tempImage
                else:
                    stitchResult[offsetList[0][0]: offsetList[0][0] + tempImage.shape[0],
                    offsetList[0][1]: offsetList[0][1] + tempImage.shape[1]] = tempImage
                mask[offsetList[0][0]: offsetList[0][0] + tempImage.shape[0],
                offsetList[0][1]: offsetList[0][1] + tempImage.shape[1]] = 1
            else:
                if self.fuseMethod == "notFuse":
                    # 适用于无图像融合，直接覆盖
                    # self.printAndWrite("StitchUtil " + str(i+1) + "th, the roi_ltx is " + str(offsetList[i][0]) + " and the roi_lty is " + str(offsetList[i][1]))
                    if self.isColorMode:
                        stitchResult[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1], :] = tempImage
                    else:
                        stitchResult[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1]] = tempImage
                    mask[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                    offsetList[i][1]: offsetList[i][1] + tempImage.shape[1]] = 1
                else:
                    # 适用于图像融合算法，切出 roiA 和 roiB 供图像融合
                    minOccupyX = rangeX[i - 1][0]
                    maxOccupyX = rangeX[i - 1][1]
                    minOccupyY = rangeY[i - 1][0]
                    maxOccupyY = rangeY[i - 1][1]
                    # self.printAndWrite("StitchUtil " + str(i + 1) + "th, the offsetList[i][0] is " + str(
                    #     offsetList[i][0]) + " and the offsetList[i][1] is " + str(offsetList[i][1]))
                    # self.printAndWrite("StitchUtil " + str(i + 1) + "th, the minOccupyX is " + str(
                    #     minOccupyX) + " and the maxOccupyX is " + str(maxOccupyX) + " and the minOccupyY is " + str(
                    #     minOccupyY) + " and the maxOccupyY is " + str(maxOccupyY))
                    roi_ltx = max(offsetList[i][0], minOccupyX)
                    roi_lty = max(offsetList[i][1], minOccupyY)
                    roi_rbx = min(offsetList[i][0] + tempImage.shape[0], maxOccupyX)
                    roi_rby = min(offsetList[i][1] + tempImage.shape[1], maxOccupyY)
                    # self.printAndWrite("StitchUtil " + str(i + 1) + "th, the roi_ltx is " + str(
                    #     roi_ltx) + " and the roi_lty is " + str(roi_lty) + " and the roi_rbx is " + str(
                    #     roi_rbx) + " and the roi_rby is " + str(roi_rby))

                    if self.isColorMode:
                        maskA = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        roiImageRegionA = stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby, :].copy()
                        stitchResult[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1], :] = tempImage
                        mask[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1]] = 1
                        maskB = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        roiImageRegionB = stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby, :].copy()
                        stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby, :] = self.stitcher.fuseImageWithMask(
                            [roiImageRegionA, roiImageRegionB], [maskA, maskB], originOffsetList[i][0],
                            originOffsetList[i][1])
                    else:
                        maskA = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        roiImageRegionA = stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        stitchResult[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1]] = tempImage
                        mask[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        offsetList[i][1]: offsetList[i][1] + tempImage.shape[1]] = 1

                        maskB = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        roiImageRegionB = stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()

                        stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby] = self.stitcher.fuseImageWithMask(
                            [roiImageRegionA, roiImageRegionB], [maskA, maskB], originOffsetList[i][0],
                            originOffsetList[i][1])
        path = os.path.join(output_address, name)
        cv2.imencode(self.extension, stitchResult)[1].tofile(path)
        e = time.time()
        print('内存存储所耗时间：', e - s)

    def prepareSolve(self):
        picNum = len(self.fileList) // 3
        for fileIndex in range(len(self.fileList)):
            image = cv2.imdecode(np.fromfile(self.fileList[fileIndex], dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            if fileIndex < picNum:
                image = image[372:, 1325:]
            elif fileIndex < 2 * picNum:  # 中列 下上拼
                image = image[600:, :]
            elif fileIndex < 3 * picNum:
                image = image[452:, :1227]
            cv2.imencode(".jpg", image)[1].tofile(self.fileList[fileIndex])
            print(self.fileList[fileIndex])

    def getPic_left_and_center(self, left, right):
        left_center_H = [[9.46797246e-01, -1.39636599e-02, 4.29466404e+02],
                         [1.91974355e-02, 9.54452738e-01, - 1.27915792e+01],
                         [-6.83090402e-07, 6.22173851e-06, 1.00000000e+00]]
        left_center_H = np.array(left_center_H)
        # left = cv2.imdecode(np.fromfile(left, dtype=np.uint8), cv2.IMREAD_COLOR)
        # right = cv2.imdecode(np.fromfile(right, dtype=np.uint8), cv2.IMREAD_COLOR)

        # 求出右图像的透视变化顶点
        warp_point = self.warp_corner(left_center_H, right)
        # 求出右图像的透视变化图像
        imagewarp = cv2.warpPerspective(right, left_center_H, (left.shape[1] + right.shape[1], left.shape[0]))

        # 对左右图像进行拼接，返回最后的拼接图像
        image_seam_optim = self.Seam_Left_Right(left, imagewarp, left_center_H, warp_point, with_optim_mask=True)

        return image_seam_optim

    def getPic_center_and_right(self, left, right):
        center_and_right_H = [[1.07467881e+00, 2.62489194e-02, 1.87687302e+03],
                              [-4.41714009e-02, 1.07996133e+00, 1.24210737e+01],
                              [-8.41273539e-06, -7.95052263e-06, 1.00000000e+00]]
        center_and_right_H = np.array(center_and_right_H)
        # left = cv2.imdecode(np.fromfile(path1, dtype=np.uint8), cv2.IMREAD_COLOR)
        # right = cv2.imdecode(np.fromfile(path2, dtype=np.uint8), cv2.IMREAD_COLOR)

        # 求出右图像的透视变化顶点
        warp_point = self.warp_corner(center_and_right_H, right)
        # 求出右图像的透视变化图像
        imagewarp = cv2.warpPerspective(right, center_and_right_H, (left.shape[1] + right.shape[1], left.shape[0]))

        # 对左右图像进行拼接，返回最后的拼接图像
        image_seam_optim = self.Seam_Left_Right(left, imagewarp, center_and_right_H, warp_point, with_optim_mask=True)

        return image_seam_optim

    def warp_corner(self, H, src):
        '''
        :param H: 单应矩阵
        :param src: 透视变化的图像
        :return: 透视变化后的四个角，左上角开始，逆时钟
        '''

        warp_points = []
        # 图像左上角，左下角
        src_left_up = np.array([0, 0, 1])
        src_left_down = np.array([0, src.shape[0], 1])

        # 图像右上角，右下角
        src_right_up = np.array([src.shape[1], 0, 1])
        src_right_down = np.array([src.shape[1], src.shape[0], 1])

        # 透视变化后的左上角，左下角
        warp_left_up = H.dot(src_left_up)
        left_up = warp_left_up[0:2] / warp_left_up[2]
        warp_points.append(left_up)
        warp_left_down = H.dot(src_left_down)
        left_down = warp_left_down[0:2] / warp_left_down[2]
        warp_points.append(left_down)

        # 透视变化后的右上角，右下角
        warp_right_up = H.dot(src_right_up)
        right_up = warp_right_up[0:2] / warp_right_up[2]
        warp_points.append(right_up)
        warp_right_down = H.dot(src_right_down)
        right_down = warp_right_down[0:2] / warp_right_down[2]
        warp_points.append(right_down)
        return warp_points

    def optim_mask(self, mask, warp_point):
        min_left_x = min(warp_point[0][0], warp_point[1][0])
        left_margin = mask.shape[1] - min_left_x
        points_zeros = np.where(mask == 0)
        x_indexs = points_zeros[1]
        alpha = (left_margin - (x_indexs - min_left_x)) / left_margin
        mask[points_zeros] = alpha
        return mask

    def Seam_Left_Right(self, left, imagewarp, H, warp_point, with_optim_mask=True):
        '''
        :param left: 拼接的左图像
        :param imagewarp: 透视变化后的右图像
        :param H: 单应矩阵
        :param warp_point: 透视变化后的四个顶点
        :param with_optim_mask: 是否需要对拼接后的图像进行优化
        :return:
        '''
        w = left.shape[1]
        mask = imagewarp[:, 0:w]
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        mask[mask != 0] = 1
        mask[mask == 0] = 0
        mask = 1 - mask
        mask = np.float32(mask)

        if with_optim_mask == True:
            mask = self.optim_mask(mask, warp_point)
        mask_rgb = np.stack([mask, mask, mask], axis=2)
        tt = np.uint8((1 - mask_rgb) * 255)
        left = left * mask_rgb + imagewarp[:, 0:w] * (1 - mask_rgb)
        imagewarp[:, 0:w] = left
        return np.uint8(imagewarp)

    def get_row_stitch_pic(self, fileIndex):
        image_left = cv2.imdecode(np.fromfile(self.fileList[fileIndex], dtype=np.uint8), cv2.IMREAD_COLOR)
        image_center = cv2.imdecode(np.fromfile(self.fileList[fileIndex + 1], dtype=np.uint8), cv2.IMREAD_COLOR)
        image_right = cv2.imdecode(np.fromfile(self.fileList[fileIndex + 2], dtype=np.uint8), cv2.IMREAD_COLOR)
        # 获得左列预处理图
        image_left = image_left[372:, 1325:]
        # 获得中列预处理图
        image_center = image_center[600:, :]
        # 获得右列预处理图
        image_right = image_right[452:, :1234]
        # 中右拼接
        image_center_right = self.getPic_center_and_right(image_center, image_right)
        # 左-中右拼接
        image_left_center_right = self.getPic_left_and_center(image_left, image_center_right)
        # 左-中右拼接由于偏移会出现很多黑色区域
        image_left_center_right = image_left_center_right[:, :3561]
        image_left_center_right = cv2.cvtColor(image_left_center_right, cv2.COLOR_BGR2GRAY)
        return image_left_center_right

    def futhing_optimization(self, pic_up, pic_down):
        # 融合方法不会改 只好改区域，黑色区域填充
        fileList = [pic_up, pic_down]
        offsetList = self.get_relative_offset_surf_H(fileList)
        # 手动测试黑色区域在pic_up的位置 （1120,1370）
        pic_fuse = pic_up[1200:, 1040:]
        (h, w) = pic_fuse.shape[:2]

        down_pos_h = 1200 - offsetList[0][0]
        down_pos_w = 1040 - offsetList[0][1]

        pic_fuse_target = pic_down[down_pos_h:down_pos_h + h, down_pos_w:down_pos_w + w]
        (h, w) = pic_fuse_target.shape[:2]
        # cv2.imshow('up',pic_fuse)
        # cv2.imshow('down',pic_fuse_target)
        # cv2.waitKey(0)
        pic_up[1200:1200 + h, 1040:1040 + w] = pic_fuse_target
        # 返回上下偏移量和优化好的pic_up
        return offsetList[0], pic_up

    def surf_Homography_method(self):
        # 获取所有图片
        self.get_all_file(self.input_address)
        pic_list_l_c_r = []
        # 循环操作预处理
        image1_left_center_right = None
        image2_left_center_right = None
        offsetList = []
        for fileIndex in range(0, len(self.fileList), 3):
            if fileIndex == 0:
                image1_left_center_right = self.get_row_stitch_pic(fileIndex)
            if len(self.fileList) - fileIndex > 3:
                image2_left_center_right = self.get_row_stitch_pic(fileIndex + 3)
                up_down_offset, image1_left_center_right = self.futhing_optimization(image1_left_center_right,
                                                                                     image2_left_center_right)
                pic_list_l_c_r.append(image1_left_center_right)
                offsetList.append(up_down_offset)
                image1_left_center_right = image2_left_center_right
            else:
                pic_list_l_c_r.append(image1_left_center_right)

            # image_left_center_right = self.resizeImg(image_left_center_right, 0.3)
            # cv2.imshow('image_left_center_right', image_left_center_right)
            # cv2.waitKey(0)

        # 逐列拼接
        self.initStitcher(1)
        # tempOffsetList, tempErrorPosList = self.get_relative_offset_group_surf_H(pic_list_l_c_r)
        tempOffsetList, tempErrorPosList = self.get_temp_offsetList_surf_H(offsetList)

        # 写大图
        self.write_all_pic_surf_H(tempOffsetList, pic_list_l_c_r, tempErrorPosList)

    def test(self, image_list):
        self.initStitcher(2)
        exp = [48, 201]#发的test数据的经验值
        offsetList = self.get_relative_offset_has_exp(image_list, exp)
        tempOffsetList, tempErrorPosList = self.get_temp_offsetList_surf_H(offsetList)
        image = self.get_stitch_pic(image_list[tempErrorPosList[0]:tempErrorPosList[1] + 1],
                              tempOffsetList[0],)
        cv2.imwrite("abc.jpg",image)
        print(image.shape)
        # tempOffsetList, tempErrorPosList = self.get_relative_offset_group_surf_H(image_list)
        # str(fileIndex) + " and " + str(fileIndex + 1) + " can not be stitched"


if __name__ == '__main__':
    input_address = r"C:\Users\12247\Desktop\马钢\2330102134\2330102134 - 改"
    output_address = r"C:\Users\12247\Desktop"
    a = cv2.imdecode(np.fromfile('0_00000370.jpg', dtype=np.uint8), cv2.IMREAD_COLOR)
    b = cv2.imdecode(np.fromfile('1_00000370.jpg', dtype=np.uint8), cv2.IMREAD_COLOR)
    # c = cv2.imdecode(np.fromfile('arrayscan00-BSE_1_3.tif', dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    # d = cv2.imdecode(np.fromfile('arrayscan00-BSE_1_4.tif', dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    list_image =[a,b]
    tool = mainTool(input_address, output_address)
    # 通道设置
    tool.isColorMode = True
    tool.test(list_image)
