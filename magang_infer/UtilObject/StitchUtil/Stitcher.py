import threading

import imagesize
import cupy
import psutil
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from osgeo import gdal
import numpy as np
import cv2
# from scipy.stats import mode
import time
import os
import glob
import copy
# import skimage.measure
# from numba import jit
# from skimage.registration import phase_cross_correlation
import pynvml


from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import ImageUtility as Utility
import ImageFusion
import time

class Stitcher(Utility.Method):
    '''
	    图像拼接类，包括所有跟材料显微组织图像配准相关函数
	'''
    isColorMode = True
    direction = 1               # 1： 第一张图像在上，第二张图像在下；   2： 第一张图像在左，第二张图像在右；
                                # 3： 第一张图像在下，第二张图像在上；   4： 第一张图像在右，第二张图像在左；
    directIncre = 1             # 拼接增长方向，可以为1. 0， -1
    fuseMethod = "trigonometric"
    phaseResponseThreshold = 0.15


    imageFusion = ImageFusion.ImageFusion()
    maxDescriptor = 0  # 当特征点大于5万时，将该值设为1，以此通知裁剪更小区域的图片

    def directionIncrease(self, direction):
        """
        功能：改变拼接搜索方向，通过direction和directIncre控制，使得范围保持在[1,4]
        :param direction: 当前的方向
        :return: 返回更新后的方向
        """
        # direction += self.directIncre  # self.directIncre
        direction += self.directIncre
        if direction == 5:
            direction = 1
        if direction == 0:
            direction = 4
        return direction

    def calculateOffsetForFeatureSearch(self, images):
        '''
        功能：采用特征搜索计算偏移量
        :param images: [imageA, imageB]
        :return:(status, offset)
        '''
        (imageA, imageB) = images
        offset = [0, 0]
        status = False
        if self.isEnhance == True:
            if self.isClahe == True:
                clahe = cv2.createCLAHE(clipLimit=self.clipLimit, tileGridSize=(self.tileSize, self.tileSize))
                imageA = clahe.apply(imageA)
                imageB = clahe.apply(imageB)
            elif self.isClahe == False:
                imageA = cv2.equalizeHist(imageA)
                imageB = cv2.equalizeHist(imageB)
        # get the feature points
        (kpsA, featuresA) = self.detectAndDescribe(imageA, featureMethod=self.featureMethod)
        (kpsB, featuresB) = self.detectAndDescribe(imageB, featureMethod=self.featureMethod)

        if featuresA is not None and featuresB is not None:
            matches = self.matchDescriptors(featuresA, featuresB)
            # match all the feature points
            if self.offsetCaculate == "mode":
                (status, offset) = self.getOffsetByMode(kpsA, kpsB, matches, offsetEvaluate = self.offsetEvaluate)
            elif self.offsetCaculate == "ransac":
                (status, offset, adjustH) = self.getOffsetByRansac(kpsA, kpsB, matches, offsetEvaluate = self.offsetEvaluate)
        if status == False:
            return (status, "  The two images can not match")
        elif status == True:
            return (status, offset)

    def calculateOffsetForFeatureSearchIncre(self, images):
        '''
        功能：采用特征搜索计算偏移量-考虑增长搜索区域
        :param images: [imageA, imageB]
        :return:(status, offset)
        '''
        (imageA, imageB) = images
        offset = [0, 0]
        status = False
        maxI = (np.floor(0.5 / self.roiRatio) + 1).astype(int)+ 1
        iniDirection = self.direction
        localDirection = iniDirection
        for i in range(1, maxI):
            # self.printAndWrite("  i=" + str(i) + " and maxI="+str(maxI))
            while(True):
                # 如果是右向拼接，先从row方向开始，从1024逐步增大到4048，如果匹配都失败，再进行横向增量
                if imageA.shape[0] > 5000:
                    row_list = [k for k in range(1, 4)]
                    normal_images = False
                else:
                    row_list = [1]
                    # 如果发现是正常大小的图像，就不需要裁剪，下面的updownSwitch只进行一次
                    normal_images = True
                for j in row_list:
                    updownSwitch = 0
                    while updownSwitch < 2:
                        # 如果是正常大小图片无需裁剪，如果是大图则需裁剪
                        if normal_images:
                            imageA_1 = imageA
                            imageB_1 = imageB
                            updownSwitch = 2
                        else:
                            # updownSwitch为0时，裁剪图像上部分拼接，为1时，裁剪图片下部分拼接
                            if updownSwitch == 0:
                                imageA_1 = imageA[:int(1048 * j), :]
                                imageB_1 = imageB[:int(1048 * j), :]
                            else:
                                imageA_1 = imageA[imageA.shape[0] - int(1048 * j):, :]
                                imageB_1 = imageB[imageB.shape[0] - int(1048 * j):, :]
                        # get the roi region of images
                        # self.printAndWrite("  localDirection=" + str(localDirection))
                        roiImageA = self.getROIRegionForIncreMethod(imageA_1, direction=localDirection, order="first", searchRatio = i * self.roiRatio)
                        roiImageB = self.getROIRegionForIncreMethod(imageB_1, direction=localDirection, order="second", searchRatio = i * self.roiRatio)
                        if self.isEnhance == True:
                            if self.isClahe == True:
                                clahe = cv2.createCLAHE(clipLimit=self.clipLimit,tileGridSize=(self.tileSize, self.tileSize))
                                roiImageA = clahe.apply(roiImageA)
                                roiImageB = clahe.apply(roiImageB)
                            elif self.isClahe == False:
                                roiImageA = cv2.equalizeHist(roiImageA)
                                roiImageB = cv2.equalizeHist(roiImageB)
                        # get the feature points
                        kpsA, featuresA = self.detectAndDescribe(roiImageA, featureMethod=self.featureMethod)
                        kpsB, featuresB = self.detectAndDescribe(roiImageB, featureMethod=self.featureMethod)
                        if featuresA is not None and featuresB is not None:
                            matches = self.matchDescriptors(featuresA, featuresB)
                            # match all the feature points
                            if self.offsetCaculate == "mode":
                                (status, offset) = self.getOffsetByMode(kpsA, kpsB, matches, offsetEvaluate = self.offsetEvaluate)
                            elif self.offsetCaculate == "ransac":
                                (status, offset, adjustH) = self.getOffsetByRansac(kpsA, kpsB, matches, offsetEvaluate = self.offsetEvaluate)
                        if status:
                            break
                        else:
                            updownSwitch = updownSwitch + 1
                            if normal_images:
                                print("作为正常图拼接失败，变换裁剪区域或者加大裁剪区域")
                            else:
                                print("此次拼接失败，变换裁剪区域或者加大裁剪区域")
                    if status:
                        break
                if status:
                    break
                else:
                    localDirection = self.directionIncrease(localDirection)
                if localDirection == iniDirection:
                    break
            if status:
                if localDirection == 1:
                    offset[0] = offset[0] + imageA.shape[0] - int(i * self.roiRatio * imageA.shape[0])
                elif localDirection == 2:
                    offset[1] = offset[1] + imageA.shape[1] - int(i * self.roiRatio * imageA.shape[1])
                elif localDirection == 3:
                    offset[0] = offset[0] - (imageB.shape[0] - int(i * self.roiRatio * imageB.shape[0]))
                elif localDirection == 4:
                    offset[1] = offset[1] - (imageB.shape[1] - int(i * self.roiRatio * imageB.shape[1]))
                self.direction = localDirection
                break
        if status == False:
            return (status, "  The two images can not match")
        elif status == True:
            self.printAndWrite("  The offset of stitching: dx is " + str(offset[0]) + " dy is " + str(offset[1]))
            return (status, offset)



    def writeStitchResultForSmallPic(self,fileList,offsetList,originOffsetList,resultRow,resultCol,rangeX,rangeY,name,output_address):
        # 对于拼接结果是内存占比较小的图，采用内存矩阵赋值的方式
        s = time.time()
        stitchResult = None
        if self.isColorMode:
            stitchResult = np.zeros((resultRow, resultCol, 3), np.uint8)
        else:
            stitchResult = np.zeros((resultRow, resultCol), np.uint8)

        mask = np.zeros((resultRow, resultCol), np.uint8)

        # 如上算出各个图像相对于原点偏移量，并最终计算出输出图像大小，并构造矩阵，如下开始赋值
        for i in range(0, len(offsetList)):
            self.printAndWrite("  fusing " + str(fileList[i]).split('/')[-1])
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
                        stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby, :] = self.fuseImageWithMask(
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


                        stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby] = self.fuseImageWithMask(
                            [roiImageRegionA, roiImageRegionB], [maskA, maskB], originOffsetList[i][0],
                            originOffsetList[i][1])

        # 保存图片
        file_extension = name.split('.')[-1]
        # cv2.imencode("." + file_extension, stitchResult)[1].tofile(output_address + "/" + name)
        rowNum = int(stitchResult.shape[0])
        colNum = int(stitchResult.shape[1])

        if rowNum * colNum < pow(2, 30):
            cv2.imencode("." + file_extension, stitchResult)[1].tofile(output_address + "/" + name)
        else:
            self.writeForBigPic(output_address + "/" + name, rowNum, colNum, stitchResult)
        e = time.time()
        print('内存存储所耗时间：', e - s)
    def writeForBigPic(self,path, rowNum, colNum, stitchResult):
        poDriver = gdal.GetDriverByName("GTiff")
        poDataset = poDriver.Create(path, colNum, rowNum, 1, gdal.GDT_Byte, ['bigtiff=IF_NEEDED']
                                    )
        poDataset.SetGeoTransform((0.0, 1.0, 0.0, 0.0, 0.0, 1.0))


        poDataset.GetRasterBand(1).WriteRaster(0, 0,
                                               colNum, rowNum,
                                               stitchResult.tobytes(), colNum,
                                               rowNum)
    def writeStitchResultForBigPic(self, fileList, offsetList, originOffsetList, resultRow, resultCol,
                                   rangeX, rangeY, name, output_address):
        # 将自定义大图存储空间放在磁盘内
        '''
        以下提供一种直接将计算好的图像保存到磁盘上而不是先写入内存数组的方法，为了解决大图像保存时内存不够的问题，在图像超过一定大小空间时使用
        以下方法使用了gdal库，但是rasterio库应该也行
        但是这种方法由于直接将结果写在了磁盘上，无法返回拼好后的完整矩阵，所以后续的处理包括打开手动修改，以及中间有拼接失败的情况的话比较难实现，需要大改后续处理逻辑
        使用时需要传入完整保存路径，但大图像超过4G时保存为一般的格式不行，采用了bigtiff格式，文件扩展名也是tif
        以下这一段是从这个函数的stitchResult = None这一行（包括这一行）开始修改的
        如果以后要上线时，要先测试
        _________________________________________________________________________________
         '''
        s = time.time()
        poDriver = gdal.GetDriverByName("GTiff")
        name = name.rsplit(".", 1)[-2] + ".tif"  # 只能用tif格式保存
        mask_name = 'temp_mask.tif'
        tempOneArray = None
        if self.isColorMode:
            poDataset = poDriver.Create(output_address + "/" + name, int(resultCol), int(resultRow), 3, gdal.GDT_Byte,
                                        ['BIGTIFF=IF_NEEDED'])
        else:
            poDataset = poDriver.Create(output_address + "/" + name, int(resultCol), int(resultRow), 1, gdal.GDT_Byte,
                                        ['BIGTIFF=IF_NEEDED'])
        poDataset.SetGeoTransform((0.0, 1.0, 0.0, 0.0, 0.0, 1.0))
        # mask = np.full((resultRow, resultCol), False, dtype=bool)  # 全 False
        mask = poDriver.Create(output_address + "/" + mask_name,int(resultCol), int(resultRow), 1, gdal.GDT_Byte,
                                    ['BIGTIFF=IF_NEEDED'])

        # 如上算出各个图像相对于原点偏移量，并最终计算出输出图像大小，并构造矩阵，如下开始赋值
        for i in range(0, len(offsetList)):
            self.printAndWrite("  fusing " + str(fileList[i]).split('/')[-1])
            if self.isColorMode:
                tempImage = cv2.imdecode(np.fromfile(fileList[i], dtype=np.uint8), cv2.IMREAD_COLOR)
            else:
                tempImage = cv2.imdecode(np.fromfile(fileList[i], dtype=np.uint8), cv2
                                         .IMREAD_GRAYSCALE)
            if(i == 0):
                tempOneArray = (np.ones((tempImage.shape[0], tempImage.shape[1]), np.uint8)*250).tobytes()
            if i == 0:
                if self.isColorMode:
                    for k in range(3):

                        poDataset.GetRasterBand(k + 1).WriteRaster(int(offsetList[0][1]), int(offsetList[0][0]),
                                                                   int(tempImage.shape[1]),
                                                                   int(tempImage.shape[0]),
                                                                   tempImage[:, :, 2-k].tobytes(),
                                                                   int(tempImage.shape[1]),
                                                                   int(tempImage.shape[0]))
                else:
                    poDataset.GetRasterBand(1).WriteRaster(int(offsetList[0][1]), int(offsetList[0][0]),
                                                           int(tempImage.shape[1]), int(tempImage.shape[0]),
                                                           tempImage.tobytes(), int(tempImage.shape[1]),
                                                           int(tempImage.shape[0]))
                mask.GetRasterBand(1).WriteRaster(int(offsetList[0][1]), int(offsetList[0][0]),
                                                       int(tempImage.shape[1]), int(tempImage.shape[0]),
                                                       tempOneArray, int(tempImage.shape[1]),
                                                       int(tempImage.shape[0]))
            else:
                if self.fuseMethod == "notFuse":
                    # 适用于无图像融合，直接覆盖
                    # self.printAndWrite("StitchUtil " + str(i+1) + "th, the roi_ltx is " + str(offsetList[i][0]) + " and the roi_lty is " + str(offsetList[i][1]))
                    if self.isColorMode:
                        for k in range(3):
                            poDataset.GetRasterBand(k + 1).WriteRaster(int(offsetList[i][1]),int(offsetList[i][0]),
                                                                       int(tempImage.shape[1]),int(tempImage.shape[0]),
                                                                       tempImage[:, :, 2-k].tobytes(),
                                                                       int(tempImage.shape[1]),int(tempImage.shape[0]))
                    else:
                        poDataset.GetRasterBand(1).WriteRaster(int(offsetList[i][1]), int(offsetList[i][0]),
                                                                   int(tempImage.shape[1]), int(tempImage.shape[0]),
                                                                   tempImage.tobytes(),
                                                                   int(tempImage.shape[1]), int(tempImage.shape[0]))
                    mask.GetRasterBand(1).WriteRaster(int(offsetList[i][1]), int(offsetList[i][0]),
                                                           int(tempImage.shape[1]), int(tempImage.shape[0]),
                                                           tempOneArray,
                                                           int(tempImage.shape[1]), int(tempImage.shape[0]))
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
                    roi_ltx = int(max(offsetList[i][0], minOccupyX))
                    roi_lty = int(max(offsetList[i][1], minOccupyY))
                    roi_rbx = int(min(offsetList[i][0] + tempImage.shape[0], maxOccupyX))
                    roi_rby = int(min(offsetList[i][1] + tempImage.shape[1], maxOccupyY))
                    # self.printAndWrite("StitchUtil " + str(i + 1) + "th, the roi_ltx is " + str(
                    #     roi_ltx) + " and the roi_lty is " + str(roi_lty) + " and the roi_rbx is " + str(
                    #     roi_rbx) + " and the roi_rby is " + str(roi_rby)+"type="+str(type(roi_lty)))
                    if self.isColorMode:
                        maskA = mask.GetRasterBand(1).ReadAsArray(roi_lty, roi_ltx, roi_rby - roi_lty,
                                                                   roi_rbx - roi_ltx)
                        roiImageRegionA = np.zeros([roi_rbx - roi_ltx, roi_rby - roi_lty, 3])
                        roiImageRegionB = np.zeros([roi_rbx - roi_ltx, roi_rby - roi_lty, 3])
                        # print("dd",roiImageRegionB.shape)
                        # maskA = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        for k in range(3):
                            roiImageRegionA[:, :, k] = poDataset.GetRasterBand(k + 1).ReadAsArray(roi_lty, roi_ltx, roi_rby - roi_lty,
                                                                               roi_rbx - roi_ltx)

                        for k in range(3):
                            # 图像偏蓝 GDAL内band存储顺序为RGB，需要转换为我们一般的BGR存储，即低地址->高地址为:B G R
                            poDataset.GetRasterBand(k + 1).WriteRaster(int(offsetList[i][1]), int(offsetList[i][0]),
                                                                       int(tempImage.shape[1]), int(tempImage.shape[0]),
                                                                       tempImage[:, :, 2-k].tobytes(),
                                                                       int(tempImage.shape[1]), int(tempImage.shape[0]))
                        mask.GetRasterBand(1).WriteRaster(int(offsetList[i][1]), int(offsetList[i][0]),
                                                          int(tempImage.shape[1]), int(tempImage.shape[0]),
                                                          tempOneArray,
                                                          int(tempImage.shape[1]), int(tempImage.shape[0]))

                        maskB = mask.GetRasterBand(1).ReadAsArray(roi_lty, roi_ltx, roi_rby - roi_lty,
                                                                  roi_rbx - roi_ltx)
                        # mask[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        # offsetList[i][1]: offsetList[i][1] + tempImage.shape[1]] = True
                        # maskB = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        for k in range(3):
                            roiImageRegionB[:, :, k] = poDataset.GetRasterBand(k + 1).ReadAsArray(roi_lty, roi_ltx, roi_rby - roi_lty,
                                                                                    roi_rbx - roi_ltx)


                        fuseImageResult = self.fuseImageWithMask([roiImageRegionA, roiImageRegionB], [maskA, maskB],
                                                                 originOffsetList[i][0], originOffsetList[i][1])
                        for k in range(3):
                            poDataset.GetRasterBand(k + 1).WriteRaster(int(roi_lty) ,int(roi_ltx) ,int(roi_rby - roi_lty) ,
                                                                       int(roi_rbx - roi_ltx) ,
                                                                       fuseImageResult[:, :, k].tobytes())
                    else:
                        maskA = mask.GetRasterBand(1).ReadAsArray(roi_lty, roi_ltx, roi_rby - roi_lty,
                                                                  roi_rbx - roi_ltx)
                        roiImageRegionA = poDataset.GetRasterBand(1).ReadAsArray(roi_lty, roi_ltx, roi_rby - roi_lty,
                                                                                 roi_rbx - roi_ltx)

                        poDataset.GetRasterBand(1).WriteRaster(int(offsetList[i][1]), int(offsetList[i][0]),
                                                               int(tempImage.shape[1]), int(tempImage.shape[0]),
                                                               tempImage.tobytes(), int(tempImage.shape[1]) ,
                                                               int(tempImage.shape[0]))
                        mask.GetRasterBand(1).WriteRaster(int(offsetList[i][1]), int(offsetList[i][0]),
                                                               int(tempImage.shape[1]), int(tempImage.shape[0]),
                                                               tempOneArray, int(tempImage.shape[1]) ,
                                                               int(tempImage.shape[0]))

                        maskB = mask.GetRasterBand(1).ReadAsArray(roi_lty, roi_ltx, roi_rby - roi_lty,
                                                                  roi_rbx - roi_ltx)
                        roiImageRegionB = poDataset.GetRasterBand(1).ReadAsArray(roi_lty, roi_ltx, roi_rby - roi_lty,
                                                                        roi_rbx - roi_ltx)

                        fuseImageResult = self.fuseImageWithMask([roiImageRegionA, roiImageRegionB], [maskA, maskB],
                                                                 originOffsetList[i][0], originOffsetList[i][1])
                        poDataset.GetRasterBand(1).WriteRaster(int(roi_lty), int(roi_ltx), int(roi_rby - roi_lty),
                                                               int(roi_rbx - roi_ltx), fuseImageResult.tobytes())
        # 删除临时mask
        del mask
        del poDataset
        if os.path.exists(output_address + "/" + mask_name):
            os.remove(output_address + "/" + mask_name)
        e = time.time()
        print('磁盘存储所耗时间：', e - s)


    def get_free_space_mb(self,path):
        drive, rem = os.path.splitdrive(path)
        diskinfo = psutil.disk_usage(drive)

        free_mem_mb = round((float(diskinfo.free) / 1024 / 1024), 2)

        print("读取",drive,"磁盘,剩余空间大小为", free_mem_mb, 'Mib')
        return free_mem_mb

    def fuseImage(self, images, dx, dy):
        """
        功能：融合图像
        :param images: [imageA, imageB]
        :param dx: x方向偏移量
        :param dy: y方向偏移量
        :return:
        """
        self.imageFusion.isColorMode = self.isColorMode
        (imageA, imageB) = images
        if self.fuseMethod != "fadeInAndFadeOut" and self.fuseMethod != "trigonometric":
            # 将各自区域中为背景的部分用另一区域填充，目的是消除背景
            # 权值为-1是为了方便渐入渐出融合和三角融合计算
            imageA[imageA == -1] = 0
            imageB[imageB == -1] = 0
            imageA[imageA == 0] = imageB[imageA == 0]
            imageB[imageB == 0] = imageA[imageB == 0]

        fuseRegion = np.zeros(imageA.shape, np.uint8)
        if(imageA.size==0 or imageB.size==0):
            fuseRegion = imageB
        elif self.fuseMethod == "notFuse":
            fuseRegion = imageB
        elif self.fuseMethod == "average":
            fuseRegion = self.imageFusion.fuseByAverage([imageA, imageB])
        elif self.fuseMethod == "maximum":
            fuseRegion = self.imageFusion.fuseByMaximum([imageA, imageB])
        elif self.fuseMethod == "minimum":
            fuseRegion = self.imageFusion.fuseByMinimum([imageA, imageB])
        elif self.fuseMethod == "fadeInAndFadeOut":
            fuseRegion = self.imageFusion.fuseByFadeInAndFadeOut(images, dx, dy)
        elif self.fuseMethod == "trigonometric":
            fuseRegion = self.imageFusion.fuseByTrigonometric(images, dx, dy)
        elif self.fuseMethod == "multiBandBlending":
            assert self.isColorMode is False, "The multi Band Blending is not support for color mode in this code"
            fuseRegion = self.imageFusion.fuseByMultiBandBlending([imageA, imageB])
        elif self.fuseMethod == "optimalSeamLine":
            assert self.isColorMode is False, "The optimal seam line is not support for color mode in this code"
            fuseRegion = self.imageFusion.fuseByOptimalSeamLine(images, self.direction)
        return fuseRegion
    def fuseImageWithMask(self, images,masks, dx, dy):
        """
        功能：融合图像
        :param images: [imageA, imageB]
        :param dx: x方向偏移量
        :param dy: y方向偏移量


        :return:
        """
        self.imageFusion.isColorMode = self.isColorMode
        (imageA, imageB) = images
        # cv2.imshow("imageA", imageA)
        # cv2.imshow("imageB", imageB)
        # cv2.waitKey(0)
        print(self.fuseMethod)
        if(imageA.size==0 or imageB.size==0):
            fuseRegion = imageB
        elif self.fuseMethod == "notFuse":
            fuseRegion = imageB
        elif self.fuseMethod == "average":
            fuseRegion = self.imageFusion.fuseByAverage([imageA, imageB])
        elif self.fuseMethod == "maximum":
            fuseRegion = self.imageFusion.fuseByMaximum([imageA, imageB])
        elif self.fuseMethod == "minimum":
            fuseRegion = self.imageFusion.fuseByMinimum([imageA, imageB])
        elif self.fuseMethod == "fadeInAndFadeOut":
            fuseRegion = self.imageFusion.fuseByFadeInAndFadeOutWithMask(images,masks, dx, dy)
        elif self.fuseMethod == "trigonometric":
            fuseRegion = self.imageFusion.fuseByTrigonometricWithMask(images,masks, dx, dy)
        elif self.fuseMethod == "multiBandBlending":
            assert self.isColorMode is False, "The multi Band Blending is not support for color mode in this code"
            fuseRegion = self.imageFusion.fuseByMultiBandBlending([imageA, imageB])
        elif self.fuseMethod == "optimalSeamLine":
            assert self.isColorMode is False, "The optimal seam line is not support for color mode in this code"
            fuseRegion = self.imageFusion.fuseByOptimalSeamLine(images, self.direction)
        return fuseRegion

class WriteStitchResultForSmallPic_thread(QThread):
    signal_update_pb = pyqtSignal(int,int)
    signal_process = pyqtSignal(list)

    signal_run_over = pyqtSignal()
    signal_time_show = pyqtSignal(float)

    def __init__(self,parentStitch, fileList, offsetList, originOffsetList, resultRow, resultCol, rangeX, rangeY,
                                     name, output_address):
        super().__init__()
        self.fileList = fileList
        self.offsetList = offsetList
        self.originOffsetList = originOffsetList
        self.resultRow = resultRow
        self.resultCol = resultCol
        self.rangeX = rangeX
        self.rangeY = rangeY
        self.name = name
        self.output_address = output_address
        self.parentStitcher = parentStitch
    def run(self):
        s = time.time()
        stitchResult = None
        if self.parentStitcher.isColorMode:
            stitchResult = np.zeros((self.resultRow, self.resultCol, 3), np.uint8)
        else:
            stitchResult = np.zeros((self.resultRow, self.resultCol), np.uint8)

        mask = np.zeros((self.resultRow, self.resultCol), np.uint8)
        self.signal_update_pb.emit(0, 100)
        # 如上算出各个图像相对于原点偏移量，并最终计算出输出图像大小，并构造矩阵，如下开始赋值
        for i in range(0, len(self.offsetList)):
            self.parentStitcher.printAndWrite("  fusing " + str(self.fileList[i]).split('/')[-1])

            if self.parentStitcher.isColorMode:
                tempImage = cv2.imdecode(np.fromfile(self.fileList[i], dtype=np.uint8), cv2.IMREAD_COLOR)
            else:
                tempImage = cv2.imdecode(np.fromfile(self.fileList[i], dtype=np.uint8), cv2.IMREAD_GRAYSCALE)

            if i == 0:
                if self.parentStitcher.isColorMode:
                    stitchResult[self.offsetList[0][0]: self.offsetList[0][0] + tempImage.shape[0],
                    self.offsetList[0][1]: self.offsetList[0][1] + tempImage.shape[1], :] = tempImage
                else:
                    stitchResult[self.offsetList[0][0]: self.offsetList[0][0] + tempImage.shape[0],
                    self.offsetList[0][1]: self.offsetList[0][1] + tempImage.shape[1]] = tempImage
                mask[self.offsetList[0][0]: self.offsetList[0][0] + tempImage.shape[0],
                self.offsetList[0][1]: self.offsetList[0][1] + tempImage.shape[1]] = 1
            else:
                if self.parentStitcher.fuseMethod == "notFuse":
                    # 适用于无图像融合，直接覆盖
                    # self.printAndWrite("StitchUtil " + str(i+1) + "th, the roi_ltx is " + str(offsetList[i][0]) + " and the roi_lty is " + str(offsetList[i][1]))
                    if self.parentStitcher.isColorMode:
                        stitchResult[self.offsetList[i][0]: self.offsetList[i][0] + tempImage.shape[0],
                        self.offsetList[i][1]: self.offsetList[i][1] + tempImage.shape[1], :] = tempImage
                    else:
                        stitchResult[self.offsetList[i][0]: self.offsetList[i][0] + tempImage.shape[0],
                        self.offsetList[i][1]: self.offsetList[i][1] + tempImage.shape[1]] = tempImage
                    mask[self.offsetList[i][0]: self.offsetList[i][0] + tempImage.shape[0],
                    self.offsetList[i][1]: self.offsetList[i][1] + tempImage.shape[1]] = 1
                else:
                    # 适用于图像融合算法，切出 roiA 和 roiB 供图像融合
                    minOccupyX = self.rangeX[i - 1][0]
                    maxOccupyX = self.rangeX[i - 1][1]
                    minOccupyY = self.rangeY[i - 1][0]
                    maxOccupyY = self.rangeY[i - 1][1]
                    # self.printAndWrite("StitchUtil " + str(i + 1) + "th, the offsetList[i][0] is " + str(
                    #     offsetList[i][0]) + " and the offsetList[i][1] is " + str(offsetList[i][1]))
                    # self.printAndWrite("StitchUtil " + str(i + 1) + "th, the minOccupyX is " + str(
                    #     minOccupyX) + " and the maxOccupyX is " + str(maxOccupyX) + " and the minOccupyY is " + str(
                    #     minOccupyY) + " and the maxOccupyY is " + str(maxOccupyY))
                    roi_ltx = max(self.offsetList[i][0], minOccupyX)
                    roi_lty = max(self.offsetList[i][1], minOccupyY)
                    roi_rbx = min(self.offsetList[i][0] + tempImage.shape[0], maxOccupyX)
                    roi_rby = min(self.offsetList[i][1] + tempImage.shape[1], maxOccupyY)
                    # self.printAndWrite("StitchUtil " + str(i + 1) + "th, the roi_ltx is " + str(
                    #     roi_ltx) + " and the roi_lty is " + str(roi_lty) + " and the roi_rbx is " + str(
                    #     roi_rbx) + " and the roi_rby is " + str(roi_rby))

                    if self.parentStitcher.isColorMode:
                        maskA = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        roiImageRegionA = stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby, :].copy()
                        stitchResult[self.offsetList[i][0]: self.offsetList[i][0] + tempImage.shape[0],
                        self.offsetList[i][1]: self.offsetList[i][1] + tempImage.shape[1], :] = tempImage
                        mask[self.offsetList[i][0]: self.offsetList[i][0] + tempImage.shape[0],
                        self.offsetList[i][1]: self.offsetList[i][1] + tempImage.shape[1]] = 1
                        maskB = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        roiImageRegionB = stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby, :].copy()
                        stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby, :] = self.parentStitcher.fuseImageWithMask(
                            [roiImageRegionA, roiImageRegionB], [maskA, maskB], self.originOffsetList[i][0],
                            self.originOffsetList[i][1])
                    else:
                        maskA = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        roiImageRegionA = stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        stitchResult[self.offsetList[i][0]: self.offsetList[i][0] + tempImage.shape[0],
                        self.offsetList[i][1]: self.offsetList[i][1] + tempImage.shape[1]] = tempImage
                        mask[self.offsetList[i][0]: self.offsetList[i][0] + tempImage.shape[0],
                        self.offsetList[i][1]: self.offsetList[i][1] + tempImage.shape[1]] = 1

                        maskB = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        roiImageRegionB = stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()

                        stitchResult[roi_ltx:roi_rbx, roi_lty:roi_rby] = self.parentStitcher.fuseImageWithMask(
                            [roiImageRegionA, roiImageRegionB], [maskA, maskB], self.originOffsetList[i][0],
                            self.originOffsetList[i][1])

            self.signal_update_pb.emit(int((i + 1) / len(self.offsetList) * 99), 100)
        # 保存图片
        file_extension = self.name.split('.')[-1]
        # cv2.imencode("." + file_extension, stitchResult)[1].tofile(output_address + "/" + name)
        rowNum = int(stitchResult.shape[0])
        colNum = int(stitchResult.shape[1])
        e1 = time.time()
        if rowNum * colNum < pow(2, 30):
            cv2.imencode("." + file_extension, stitchResult)[1].tofile(self.output_address + "/" + self.name)
        else:
            self.parentStitcher.writeForBigPic(self.output_address + "/" + self.name, rowNum, colNum, stitchResult)
        self.signal_update_pb.emit(100, 100)
        self.signal_run_over.emit()
        e = time.time()
        print('内存存储所耗时间：', e - s,e1-s,e-e1)

class WriteStitchResultForBigPic_thread(QThread):
    signal_update_pb = pyqtSignal(int, int)
    signal_process = pyqtSignal(list)

    signal_run_over = pyqtSignal()
    signal_time_show = pyqtSignal(float)

    def __init__(self,parentStitch, fileList, offsetList, originOffsetList, resultRow, resultCol, rangeX, rangeY,
                                     name, output_address):
        super().__init__()
        self.fileList = fileList
        self.offsetList = offsetList
        self.originOffsetList = originOffsetList
        self.resultRow = resultRow
        self.resultCol = resultCol
        self.rangeX = rangeX
        self.rangeY = rangeY
        self.name = name
        self.output_address = output_address
        self.parentStitcher = parentStitch

    def run(self):
        fileList = self.fileList
        offsetList = self.offsetList
        originOffsetList = self.originOffsetList
        resultRow = self.resultRow
        resultCol = self.resultCol
        rangeX = self.rangeX
        rangeY = self.rangeY
        name = self.name
        output_address = self.output_address

        s = time.time()
        poDriver = gdal.GetDriverByName("GTiff")
        name = name.rsplit(".", 1)[-2] + ".tif"  # 只能用tif格式保存
        mask_name = 'temp_mask.tif'
        i = 0
        while os.path.isfile(output_address + "/" + mask_name):
            mask_name = 'temp_mask'+str(i)+'.tif'
            i += 1



        tempOneArray = None
        if self.parentStitcher.isColorMode:
            poDataset = poDriver.Create(output_address + "/" + name, int(resultCol), int(resultRow), 3, gdal.GDT_Byte,
                                        ['BIGTIFF=IF_NEEDED'])
        else:
            poDataset = poDriver.Create(output_address + "/" + name, int(resultCol), int(resultRow), 1, gdal.GDT_Byte,
                                        ['BIGTIFF=IF_NEEDED'])
        poDataset.SetGeoTransform((0.0, 1.0, 0.0, 0.0, 0.0, 1.0))
        # mask = np.full((resultRow, resultCol), False, dtype=bool)  # 全 False
        mask = poDriver.Create(output_address + "/" + mask_name,int(resultCol), int(resultRow), 1, gdal.GDT_Byte,
                                    ['BIGTIFF=IF_NEEDED'])
        self.signal_update_pb.emit(0, 100)
        # 如上算出各个图像相对于原点偏移量，并最终计算出输出图像大小，并构造矩阵，如下开始赋值
        for i in range(0, len(offsetList)):
            self.parentStitcher.printAndWrite("  fusing " + str(fileList[i]).split('/')[-1])


            if self.parentStitcher.isColorMode:
                tempImage = cv2.imdecode(np.fromfile(fileList[i], dtype=np.uint8), cv2.IMREAD_COLOR)
            else:
                tempImage = cv2.imdecode(np.fromfile(fileList[i], dtype=np.uint8), cv2
                                         .IMREAD_GRAYSCALE)
            if(i == 0):
                tempOneArray = (np.ones((tempImage.shape[0], tempImage.shape[1]), np.uint8)*250).tobytes()
            if i == 0:
                if self.parentStitcher.isColorMode:
                    for k in range(3):

                        poDataset.GetRasterBand(k + 1).WriteRaster(int(offsetList[0][1]), int(offsetList[0][0]),
                                                                   int(tempImage.shape[1]),
                                                                   int(tempImage.shape[0]),
                                                                   tempImage[:, :, 2-k].tobytes(),
                                                                   int(tempImage.shape[1]),
                                                                   int(tempImage.shape[0]))
                else:
                    poDataset.GetRasterBand(1).WriteRaster(int(offsetList[0][1]), int(offsetList[0][0]),
                                                           int(tempImage.shape[1]), int(tempImage.shape[0]),
                                                           tempImage.tobytes(), int(tempImage.shape[1]),
                                                           int(tempImage.shape[0]))
                mask.GetRasterBand(1).WriteRaster(int(offsetList[0][1]), int(offsetList[0][0]),
                                                       int(tempImage.shape[1]), int(tempImage.shape[0]),
                                                       tempOneArray, int(tempImage.shape[1]),
                                                       int(tempImage.shape[0]))
            else:
                if self.parentStitcher.fuseMethod == "notFuse":
                    # 适用于无图像融合，直接覆盖
                    # self.printAndWrite("StitchUtil " + str(i+1) + "th, the roi_ltx is " + str(offsetList[i][0]) + " and the roi_lty is " + str(offsetList[i][1]))
                    if self.parentStitcher.isColorMode:
                        for k in range(3):
                            poDataset.GetRasterBand(k + 1).WriteRaster(int(offsetList[i][1]),int(offsetList[i][0]),
                                                                       int(tempImage.shape[1]),int(tempImage.shape[0]),
                                                                       tempImage[:, :, 2-k].tobytes(),
                                                                       int(tempImage.shape[1]),int(tempImage.shape[0]))
                    else:
                        poDataset.GetRasterBand(1).WriteRaster(int(offsetList[i][1]), int(offsetList[i][0]),
                                                                   int(tempImage.shape[1]), int(tempImage.shape[0]),
                                                                   tempImage.tobytes(),
                                                                   int(tempImage.shape[1]), int(tempImage.shape[0]))
                    mask.GetRasterBand(1).WriteRaster(int(offsetList[i][1]), int(offsetList[i][0]),
                                                           int(tempImage.shape[1]), int(tempImage.shape[0]),
                                                           tempOneArray,
                                                           int(tempImage.shape[1]), int(tempImage.shape[0]))
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
                    roi_ltx = int(max(offsetList[i][0], minOccupyX))
                    roi_lty = int(max(offsetList[i][1], minOccupyY))
                    roi_rbx = int(min(offsetList[i][0] + tempImage.shape[0], maxOccupyX))
                    roi_rby = int(min(offsetList[i][1] + tempImage.shape[1], maxOccupyY))
                    # self.printAndWrite("StitchUtil " + str(i + 1) + "th, the roi_ltx is " + str(
                    #     roi_ltx) + " and the roi_lty is " + str(roi_lty) + " and the roi_rbx is " + str(
                    #     roi_rbx) + " and the roi_rby is " + str(roi_rby)+"type="+str(type(roi_lty)))
                    if self.parentStitcher.isColorMode:
                        maskA = mask.GetRasterBand(1).ReadAsArray(roi_lty, roi_ltx, roi_rby - roi_lty,
                                                                   roi_rbx - roi_ltx)
                        roiImageRegionA = np.zeros([roi_rbx - roi_ltx, roi_rby - roi_lty, 3])
                        roiImageRegionB = np.zeros([roi_rbx - roi_ltx, roi_rby - roi_lty, 3])
                        # print("dd",roiImageRegionB.shape)
                        # maskA = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        for k in range(3):
                            roiImageRegionA[:, :, k] = poDataset.GetRasterBand(k + 1).ReadAsArray(roi_lty, roi_ltx, roi_rby - roi_lty,
                                                                               roi_rbx - roi_ltx)

                        for k in range(3):
                            # 图像偏蓝 GDAL内band存储顺序为RGB，需要转换为我们一般的BGR存储，即低地址->高地址为:B G R
                            poDataset.GetRasterBand(k + 1).WriteRaster(int(offsetList[i][1]), int(offsetList[i][0]),
                                                                       int(tempImage.shape[1]), int(tempImage.shape[0]),
                                                                       tempImage[:, :, 2-k].tobytes(),
                                                                       int(tempImage.shape[1]), int(tempImage.shape[0]))
                        mask.GetRasterBand(1).WriteRaster(int(offsetList[i][1]), int(offsetList[i][0]),
                                                          int(tempImage.shape[1]), int(tempImage.shape[0]),
                                                          tempOneArray,
                                                          int(tempImage.shape[1]), int(tempImage.shape[0]))

                        maskB = mask.GetRasterBand(1).ReadAsArray(roi_lty, roi_ltx, roi_rby - roi_lty,
                                                                  roi_rbx - roi_ltx)
                        # mask[offsetList[i][0]: offsetList[i][0] + tempImage.shape[0],
                        # offsetList[i][1]: offsetList[i][1] + tempImage.shape[1]] = True
                        # maskB = mask[roi_ltx:roi_rbx, roi_lty:roi_rby].copy()
                        for k in range(3):
                            roiImageRegionB[:, :, k] = poDataset.GetRasterBand(k + 1).ReadAsArray(roi_lty, roi_ltx, roi_rby - roi_lty,
                                                                                    roi_rbx - roi_ltx)


                        fuseImageResult = self.parentStitcher.fuseImageWithMask([roiImageRegionA, roiImageRegionB], [maskA, maskB],
                                                                 originOffsetList[i][0], originOffsetList[i][1])
                        for k in range(3):
                            poDataset.GetRasterBand(k + 1).WriteRaster(int(roi_lty) ,int(roi_ltx) ,int(roi_rby - roi_lty) ,
                                                                       int(roi_rbx - roi_ltx) ,
                                                                       fuseImageResult[:, :, k].tobytes())
                    else:
                        maskA = mask.GetRasterBand(1).ReadAsArray(roi_lty, roi_ltx, roi_rby - roi_lty,
                                                                  roi_rbx - roi_ltx)
                        roiImageRegionA = poDataset.GetRasterBand(1).ReadAsArray(roi_lty, roi_ltx, roi_rby - roi_lty,
                                                                                 roi_rbx - roi_ltx)

                        poDataset.GetRasterBand(1).WriteRaster(int(offsetList[i][1]), int(offsetList[i][0]),
                                                               int(tempImage.shape[1]), int(tempImage.shape[0]),
                                                               tempImage.tobytes(), int(tempImage.shape[1]) ,
                                                               int(tempImage.shape[0]))
                        mask.GetRasterBand(1).WriteRaster(int(offsetList[i][1]), int(offsetList[i][0]),
                                                               int(tempImage.shape[1]), int(tempImage.shape[0]),
                                                               tempOneArray, int(tempImage.shape[1]) ,
                                                               int(tempImage.shape[0]))

                        maskB = mask.GetRasterBand(1).ReadAsArray(roi_lty, roi_ltx, roi_rby - roi_lty,
                                                                  roi_rbx - roi_ltx)
                        roiImageRegionB = poDataset.GetRasterBand(1).ReadAsArray(roi_lty, roi_ltx, roi_rby - roi_lty,
                                                                        roi_rbx - roi_ltx)

                        fuseImageResult = self.parentStitcher.fuseImageWithMask([roiImageRegionA, roiImageRegionB], [maskA, maskB],
                                                                 originOffsetList[i][0], originOffsetList[i][1])
                        poDataset.GetRasterBand(1).WriteRaster(int(roi_lty), int(roi_ltx), int(roi_rby - roi_lty),
                                                               int(roi_rbx - roi_ltx), fuseImageResult.tobytes())
            self.signal_update_pb.emit(int((i + 1) / len(self.offsetList) * 99), 100)
        # 删除临时mask
        del mask
        del poDataset
        if os.path.exists(output_address + "/" + mask_name):
            os.remove(output_address + "/" + mask_name)
        self.signal_update_pb.emit(100, 100)
        self.signal_run_over.emit()
        e = time.time()
        print('磁盘存储所耗时间：', e - s)








if __name__=="__main__":
    stitcher = Stitcher()
    imageA = cv2.imread(".\\images\\dendriticCrystal\\1\\1-044.jpg", 0)
    imageB = cv2.imread(".\\images\\dendriticCrystal\\1\\1-045.jpg", 0)
    offset = stitcher.calculateOffsetForFeatureSearchIncre([imageA, imageB])