import time

import numpy as np
import cv2
import math
from functools import partial

from scipy.fft import fftn, ifftn, next_fast_len


class Method():
    # 关于打印信息的设置
    outputAddress = "result/"
    isEvaluate = False  # 是否输出到检验txt文件
    evaluateFile = "evaluate.txt"
    isPrintLog = True  # 是否在屏幕打印过程信息

    # 关于特征搜索的设置
    featureMethod = "surf"  # "sift","surf" or "orb"
    roiRatio = 0.24 # roi length for stitching in first direction
    # roiRatio = 0.1  # roi length for stitching in first direction
    searchRatio = 0.75  # 0.75 is common value for matches

    # 关于 GPU 加速的设置
    isGPUAvailable = False  # 判断GPU目前是否可用
    gpuSiftDll = None  # 当需要GPU时，提前将gupSiftDll加载到内存中
    gpuSurfDLL = None  # 当需要GPU时，提前将gpuSurfDLL加载到内存中
    gpuMatchDLL = None  # 当需要GPU时，提前将gpuMatchDLL加载到内存中
    gpuNum = None  # 如有多个GPU，支持选择某个GPU来工作
    meminfo = None

    # 关于 GPU-SURF 的设置
    surfHessianThreshold = 100.0
    surfNOctaves = 4
    surfNOctaveLayers = 3
    surfIsExtended = False
    surfKeypointsRatio = 0.01
    surfIsUpright = False

    # 关于 GPU-ORB 的设置
    orbNfeatures = 5000
    orbScaleFactor = 1.2
    orbNlevels = 8
    orbEdgeThreshold = 31
    orbFirstLevel = 0
    orbWTA_K = 2
    orbPatchSize = 31
    orbFastThreshold = 20
    orbBlurForDescriptor = False
    orbMaxDistance = 30

    # 关于特征配准的设置
    offsetCaculate = "mode"  # "mode" or "ransac"
    offsetEvaluate = 3  # 40 menas nums of matches for mode, 3.0 menas  of matches for ransac

    # 关于图像增强的操作
    isEnhance = False
    isClahe = False
    clipLimit = 20
    tileSize = 5

    def printAndWrite(self, content):
        """
        功能：向屏幕和文件打印输出内容
        :param content: 打印内容
        :return:
        """
        if self.isPrintLog:
            print(content)
        if self.isEvaluate:
            f = open(self.outputAddress + self.evaluateFile, "a")  # 在文件末尾追加
            f.write(content)
            f.write("\n")
            f.close()

    def getROIRegionForIncreMethod(self, image, direction=1, order="first", searchRatio=0.1):
        """
        功能：对于搜索增长方法，根据比例获得其搜索区域
        :param image: 原始图像
        :param direction: 搜索方向
        :param order: ‘first’or'second'判断属于第几张图像
        :param searchRatio: 裁剪搜素区域的比例，默认搜索方向上的长度的0.1
        :return: 搜索区域
        """
        row, col = image.shape[:2]
        roiRegion = np.zeros(image.shape, np.uint8)
        if direction == 1:
            searchLength = np.floor(row * searchRatio).astype(int)
            if order == "first":
                roiRegion = image[row - searchLength:row, :]
            elif order == "second":
                roiRegion = image[0: searchLength, :]
        elif direction == 2:
            searchLength = np.floor(col * searchRatio).astype(int)
            if order == "first":
                roiRegion = image[:, col - searchLength:col]
            elif order == "second":
                roiRegion = image[:, 0: searchLength]
        elif direction == 3:
            searchLength = np.floor(row * searchRatio).astype(int)
            if order == "first":
                roiRegion = image[0: searchLength, :]
            elif order == "second":
                roiRegion = image[row - searchLength:row, :]
        elif direction == 4:
            searchLength = np.floor(col * searchRatio).astype(int)
            if order == "first":
                roiRegion = image[:, 0: searchLength]
            elif order == "second":
                roiRegion = image[:, col - searchLength:col]
        return roiRegion

    def getROIRegion(self, image, direction="horizontal", order="first", searchLength=150, searchLengthForLarge=-1):
        '''
        功能：对于搜索增长方法，根据固定长度获得其搜索区域（已弃用）
        :param originalImage:需要裁剪的原始图像
        :param direction:拼接的方向
        :param order:该图片的顺序，是属于第一还是第二张图像
        :param searchLength:搜索区域大小
        :param searchLengthForLarge:对于行拼接和列拼接的搜索区域大小
        :return:返回感兴趣区域图像
        :type searchLength: np.int
        '''
        row, col = image.shape[:2]
        if direction == "horizontal" or direction == 2:
            if order == "first":
                if searchLengthForLarge == -1:
                    roiRegion = image[:, col - searchLength:col]
                elif searchLengthForLarge > 0:
                    roiRegion = image[row - searchLengthForLarge:row, col - searchLength:col]
            elif order == "second":
                if searchLengthForLarge == -1:
                    roiRegion = image[:, 0: searchLength]
                elif searchLengthForLarge > 0:
                    roiRegion = image[0:searchLengthForLarge, 0: searchLength]
        elif direction == "vertical" or direction == 1:
            if order == "first":
                if searchLengthForLarge == -1:
                    roiRegion = image[row - searchLength:row, :]
                elif searchLengthForLarge > 0:
                    roiRegion = image[row - searchLength:row, col - searchLengthForLarge:col]
            elif order == "second":
                if searchLengthForLarge == -1:
                    roiRegion = image[0: searchLength, :]
                elif searchLengthForLarge > 0:
                    roiRegion = image[0: searchLength, 0:searchLengthForLarge]
        return roiRegion

    def getOffsetByMode(self, kpsA, kpsB, matches, offsetEvaluate=10):
        """
        功能：通过求众数的方法获得偏移量
        :param kpsA: 第一张图像的特征
        :param kpsB: 第二张图像的特征
        :param matches: 配准列表
        :param offsetEvaluate: 如果众数的个数大于本阈值，则配准正确，默认为10
        :return: 返回(totalStatus, [dx, dy]), totalStatus 是否正确，[dx, dy]默认[0, 0]
        """
        totalStatus = True
        if len(matches) == 0:
            totalStatus = False
            return (totalStatus, [0, 0])
        dxList = []
        dyList = []
        for trainIdx, queryIdx in matches:
            ptA = (kpsA[queryIdx][1], kpsA[queryIdx][0])
            ptB = (kpsB[trainIdx][1], kpsB[trainIdx][0])
            # dxList.append(int(round(ptA[0] - ptB[0])))
            # dyList.append(int(round(ptA[1] - ptB[1])))
            if int(ptA[0] - ptB[0]) == 0 and int(ptA[1] - ptB[1]) == 0:
                continue
            dxList.append(int(ptA[0] - ptB[0]))
            dyList.append(int(ptA[1] - ptB[1]))
        if len(dxList) == 0:
            dxList.append(0);
            dyList.append(0)
        # Get Mode offset in [dxList, dyList], thanks for clovermini
        zipped = zip(dxList, dyList)
        zip_list = list(zipped)
        zip_dict = dict((a, zip_list.count(a)) for a in zip_list)
        zip_dict_sorted = dict(sorted(zip_dict.items(), key=lambda x: x[1], reverse=True))

        dx = list(zip_dict_sorted)[0][0]
        dy = list(zip_dict_sorted)[0][1]
        num = zip_dict_sorted[list(zip_dict_sorted)[0]]
        # print("dx = " + str(dx) + ", dy = " + str(dy) + ", num = " + str(num))

        if num < offsetEvaluate:
            totalStatus = False
        # self.printAndWrite("  In Mode, The number of num is " + str(num) + " and the number of offsetEvaluate is "+str(offsetEvaluate))
        return (totalStatus, [dx, dy])

    def getOffsetByRansac(self, kpsA, kpsB, matches, offsetEvaluate=100):
        """
        功能：通过求Ransac的方法获得偏移量（不完善）
        :param kpsA: 第一张图像的特征
        :param kpsB: 第二张图像的特征
        :param matches: 配准列表
        :param offsetEvaluate:对于Ransac求属于最小范围的个数，大于本阈值，则正确
        :return:返回(totalStatus, [dx, dy]), totalStatus 是否正确，[dx, dy]默认[0, 0]
        """
        totalStatus = False
        ptsA = np.float32([kpsA[i] for (_, i) in matches])
        ptsB = np.float32([kpsB[i] for (i, _) in matches])
        if len(matches) == 0:
            return (totalStatus, [0, 0], 0)
        # 计算视角变换矩阵
        H1 = cv2.getAffineTransform(ptsA, ptsB)
        # print("H1")
        # print(H1)
        (H, status) = cv2.findHomography(ptsA, ptsB, cv2.RANSAC, 3, 0.9)
        trueCount = 0
        for i in range(0, len(status)):
            if status[i] == True:
                trueCount = trueCount + 1
        if trueCount >= offsetEvaluate:
            totalStatus = True
            adjustH = H.copy()
            adjustH[0, 2] = 0;
            adjustH[1, 2] = 0
            adjustH[2, 0] = 0;
            adjustH[2, 1] = 0
            return (totalStatus, [np.round(np.array(H).astype(np.int)[1, 2]) * (-1),
                                  np.round(np.array(H).astype(np.int)[0, 2]) * (-1)], adjustH)
        else:
            return (totalStatus, [0, 0], 0)

    def npToListForKeypoints(self, array):
        '''
        功能：Convert array to List, used for keypoints from GPUDLL to python List
        :param array: array from GPUDLL
        :return:
        '''
        kps = []
        row, col = array.shape
        for i in range(row):
            kps.append([array[i, 0], array[i, 1]])
        return kps

    def npToListForMatches(self, array):
        '''
        功能：Convert array to List, used for DMatches from GPUDLL to python List
        :param array: array from GPUDLL
        :return:
        '''
        descritpors = []
        row, col = array.shape
        for i in range(row):
            descritpors.append((array[i, 0], array[i, 1]))
        return descritpors

    def npToKpsAndDescriptors(self, array):
        """
        功能:？
        :param array:
        :return:
        """
        kps = []
        descriptors = array[:, :, 1]
        for i in range(array.shape[0]):
            kps.append([array[i, 0, 0], array[i, 1, 0]])
        return (kps, descriptors)

    def detectAndDescribe(self, image, featureMethod):
        '''
    	功能：计算图像的特征点集合，并返回该点集＆描述特征
    	:param image:需要分析的图像
    	:return:返回特征点集，及对应的描述特征(kps, features)
    	'''
        print('ImageUtility: self.isGPUAvailable=', self.isGPUAvailable)
        print('ImageUtility: image.shape=', image.shape)
        # 设置一个标志用于判断当前图片是否太小
        flag = 0
        if image.shape[0] < 190 or image.shape[1] < 190:
            flag = 1
        if self.isGPUAvailable is False or flag == 1:  # CPU mode
            print('ImageUtility: flag=', flag)
            if featureMethod == "sift":
                print('ImageUtility: Sift-CPU')
                descriptor = cv2.xfeatures2d.SIFT_create()
            elif featureMethod == "surf":
                print('ImageUtility: Surf-CPU')
                descriptor = cv2.xfeatures2d.SURF_create()
            elif featureMethod == "orb":
                print('ImageUtility: ORB-CPU')
                descriptor = cv2.ORB_create(self.orbNfeatures, self.orbScaleFactor, self.orbNlevels,
                                            self.orbEdgeThreshold, self.orbFirstLevel, self.orbWTA_K, 0,
                                            self.orbPatchSize, self.orbFastThreshold)
            # 检测SIFT特征点，并计算描述子
            kps, features = descriptor.detectAndCompute(image, None)
            # 将结果转换成NumPy数组
            kps = np.float32([kp.pt for kp in kps])
        else:  # GPU mode
           pass
        return (kps, features)

    def matchDescriptors(self, featuresA, featuresB):
        '''
        功能：匹配特征点
        :param featuresA: 第一张图像的特征点描述符
        :param featuresB: 第二张图像的特征点描述符
        :return:返回匹配的对数matches
        '''
        flag = 0
        if featuresA.shape[0] > 30000:
            flag = 1
        if self.isGPUAvailable == False or flag == 1:  # CPU Mode
            print("featuresA.shape = ", featuresA.shape)
            print("featuresB.shape = ", featuresB.shape)
            # 建立暴力匹配器
            if self.featureMethod == "surf" or self.featureMethod == "sift":
                matcher = cv2.DescriptorMatcher_create("BruteForce")
                # 使用KNN检测来自A、B图的SIFT特征匹配对，K=2，返回一个列表
                rawMatches = matcher.knnMatch(featuresA, featuresB, 2)
                matches = []
                for m in rawMatches:
                    # 当最近距离跟次近距离的比值小于ratio值时，保留此匹配对
                    if len(m) == 2 and m[0].distance < m[1].distance * self.searchRatio:
                        # 存储两个点在featuresA, featuresB中的索引值
                        matches.append((m[0].trainIdx, m[0].queryIdx))
            elif self.featureMethod == "orb":
                matcher = cv2.DescriptorMatcher_create("BruteForce-Hamming")
                rawMatches = matcher.match(featuresA, featuresB)
                matches = []
                for m in rawMatches:
                    matches.append((m.trainIdx, m.queryIdx))
            # self.printAndWrite("  The number of matches is " + str(len(matches)))

        return matches

    def resizeImg(self, image, resizeTimes, interMethod=cv2.INTER_AREA):
        """
        功能：缩放图像
        :param image:原图像
        :param resizeTimes:缩放比例
        :param interMethod: 插值方法，默认cv2.INTER_AREA
        :return:
        """
        (h, w) = image.shape
        resizeH = int(h * resizeTimes)
        resizeW = int(w * resizeTimes)
        # cv2.INTER_AREA是测试后最好的方法
        return cv2.resize(image, (resizeW, resizeH), interpolation=interMethod)

    def rectifyFinalImg(self, image, regionLength=10):
        """
        功能：测试用，尚不完善
        :param image:
        :param regionLength:
        :return:
        """
        (h, w) = image.shape
        print("h:" + str(h))
        print("w:" + str(w))
        upperLeft = np.sum(image[0: regionLength, 0: regionLength])
        upperRight = np.sum(image[0: regionLength, w - regionLength: w])
        bottomLeft = np.sum(image[h - regionLength: h, 0: regionLength])
        bottomRight = np.sum(image[h - regionLength: h, w - regionLength: w])

        # 预处理
        zeroCol = image[:, 0]
        noneZeroNum = np.count_nonzero(zeroCol)
        zeroNum = h - noneZeroNum
        print("noneZeroNum:" + str(noneZeroNum))
        print("zeroNum:" + str(zeroNum))
        print("division:" + str(noneZeroNum / h))
        if (noneZeroNum / h) < 0.3:
            resultImage = image
        elif upperLeft == 0 and bottomRight == 0 and upperRight != 0 and bottomLeft != 0:  # 左边低，右边高
            print(1)
            center = (w // 2, h // 2)
            print(w)
            print(h)
            angle = math.atan(center[1] / center[0] * 180 / math.pi)
            print(str(angle))
            M = cv2.getRotationMatrix2D(center, -1 * angle, 1.0)
            print(M)
            resultImage = cv2.warpAffine(image, M, (w, h))
        elif upperLeft != 0 and bottomRight != 0 and upperRight == 0 and bottomLeft == 0:  # 左边高，右边低
            print(2)
            center = (w // 2, h // 2)
            angle = math.atan(center[1] / center[0] * 180 / math.pi)
            print(str(angle))
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            resultImage = cv2.warpAffine(image, M, (w, h))
        else:
            resultImage = image
        return resultImage

    def _masked_phase_cross_correlation(self, reference_image, moving_image,
                                        reference_mask, moving_mask=None,
                                        overlap_ratio=0.3):
        """Masked image translation registration by masked normalized
        cross-correlation.

        Parameters
        ----------
        reference_image : ndarray
            Reference image.
        moving_image : ndarray
            Image to register. Must be same dimensionality as ``reference_image``,
            but not necessarily the same size.
        reference_mask : ndarray
            Boolean mask for ``reference_image``. The mask should evaluate
            to ``True`` (or 1) on valid pixels. ``reference_mask`` should
            have the same shape as ``reference_image``.
        moving_mask : ndarray or None, optional
            Boolean mask for ``moving_image``. The mask should evaluate to ``True``
            (or 1) on valid pixels. ``moving_mask`` should have the same shape
            as ``moving_image``. If ``None``, ``reference_mask`` will be used.
        overlap_ratio : float, optional
            Minimum allowed overlap ratio between images. The correlation for
            translations corresponding with an overlap ratio lower than this
            threshold will be ignored. A lower `overlap_ratio` leads to smaller
            maximum translation, while a higher `overlap_ratio` leads to greater
            robustness against spurious matches due to small overlap between
            masked images.

        Returns
        -------
        shifts : ndarray
            Shift vector (in pixels) required to register ``moving_image``
            with ``reference_image``. Axis ordering is consistent with
            numpy (e.g. Z, Y, X)

        References
        ----------
        .. [1] Dirk Padfield. Masked Object Registration in the Fourier Domain.
               IEEE Transactions on Image Processing, vol. 21(5),
               pp. 2706-2718 (2012). :DOI:`10.1109/TIP.2011.2181402`
        .. [2] D. Padfield. "Masked FFT registration". In Proc. Computer Vision and
               Pattern Recognition, pp. 2918-2925 (2010).
               :DOI:`10.1109/CVPR.2010.5540032`

        """
        if moving_mask is None:
            if reference_image.shape != moving_image.shape:
                raise ValueError(
                    "Input images have different shapes, moving_mask must "
                    "be explicitely set.")
            moving_mask = reference_mask.astype(bool)

        # We need masks to be of the same size as their respective images
        for (im, mask) in [(reference_image, reference_mask),
                           (moving_image, moving_mask)]:
            if im.shape != mask.shape:
                raise ValueError(
                    "Image sizes must match their respective mask sizes.")
        if not self.isGPUAvailable:
            xcorr = self.cross_correlate_masked(moving_image, reference_image, moving_mask,
                                                reference_mask, axes=(0, 1), mode='full',
                                                overlap_ratio=overlap_ratio)
            max_pointvalue = xcorr.max()
            print(max_pointvalue)

            maxima = np.transpose(np.nonzero(xcorr == xcorr.max()))
            center = np.mean(maxima, axis=0)
            shifts = center - np.array(reference_image.shape) + 1

            # The mismatch in size will impact the center location of the
            # cross-correlation
            size_mismatch = (np.array(moving_image.shape)
                             - np.array(reference_image.shape))
            return (-shifts + (size_mismatch / 2), max_pointvalue.real)


    def cross_correlate_masked(self, arr1, arr2, m1, m2, mode='full', axes=(-2, -1),
                               overlap_ratio=0.3):
        """
        Masked normalized cross-correlation between arrays.

        Parameters
        ----------
        arr1 : ndarray
            First array.
        arr2 : ndarray
            Seconds array. The dimensions of `arr2` along axes that are not
            transformed should be equal to that of `arr1`.
        m1 : ndarray
            Mask of `arr1`. The mask should evaluate to `True`
            (or 1) on valid pixels. `m1` should have the same shape as `arr1`.
        m2 : ndarray
            Mask of `arr2`. The mask should evaluate to `True`
            (or 1) on valid pixels. `m2` should have the same shape as `arr2`.
        mode : {'full', 'same'}, optional
            'full':
                This returns the convolution at each point of overlap. At
                the end-points of the convolution, the signals do not overlap
                completely, and boundary effects may be seen.
            'same':
                The output is the same size as `arr1`, centered with respect
                to the `‘full’` output. Boundary effects are less prominent.
        axes : tuple of ints, optional
            Axes along which to compute the cross-correlation.
        overlap_ratio : float, optional
            Minimum allowed overlap ratio between images. The correlation for
            translations corresponding with an overlap ratio lower than this
            threshold will be ignored. A lower `overlap_ratio` leads to smaller
            maximum translation, while a higher `overlap_ratio` leads to greater
            robustness against spurious matches due to small overlap between
            masked images.

        Returns
        -------
        out : ndarray
            Masked normalized cross-correlation.

        Raises
        ------
        ValueError : if correlation `mode` is not valid, or array dimensions along
            non-transformation axes are not equal.

        References
        ----------
        .. [1] Dirk Padfield. Masked Object Registration in the Fourier Domain.
               IEEE Transactions on Image Processing, vol. 21(5),
               pp. 2706-2718 (2012). :DOI:`10.1109/TIP.2011.2181402`
        .. [2] D. Padfield. "Masked FFT registration". In Proc. Computer Vision and
               Pattern Recognition, pp. 2918-2925 (2010).
               :DOI:`10.1109/CVPR.2010.5540032`
        """
        if mode not in {'full', 'same'}:
            raise ValueError("Correlation mode '{}' is not valid.".format(mode))

        # GPU mode
        if self.isGPUAvailable:
          pass
        else:
            fixed_image = np.array(arr1, dtype=np.float)
            fixed_mask = np.array(m1, dtype=np.bool)
            moving_image = np.array(arr2, dtype=np.float)
            moving_mask = np.array(m2, dtype=np.bool)
            eps = np.finfo(np.float).eps

            # Array dimensions along non-transformation axes should be equal.
            all_axes = set(range(fixed_image.ndim))
            for axis in (all_axes - set(axes)):
                if fixed_image.shape[axis] != moving_image.shape[axis]:
                    raise ValueError(
                        "Array shapes along non-transformation axes should be "
                        "equal, but dimensions along axis {a} are not".format(a=axis))

            # Determine final size along transformation axes
            # Note that it might be faster to compute Fourier transform in a slightly
            # larger shape (`fast_shape`). Then, after all fourier transforms are done,
            # we slice back to`final_shape` using `final_slice`.
            final_shape = list(arr1.shape)
            for axis in axes:
                final_shape[axis] = fixed_image.shape[axis] + \
                                    moving_image.shape[axis] - 1
            final_shape = tuple(final_shape)
            final_slice = tuple([slice(0, int(sz)) for sz in final_shape])

            # Extent transform axes to the next fast length (i.e. multiple of 3, 5, or
            # 7)
            fast_shape = tuple([next_fast_len(final_shape[ax]) for ax in axes])

            # We use numpy.fft or the new scipy.fft because they allow leaving the
            # transform axes unchanged which was not possible with scipy.fftpack's
            # fftn/ifftn in older versions of SciPy.
            # E.g. arr shape (2, 3, 7), transform along axes (0, 1) with shape (4, 4)
            # results in arr_fft shape (4, 4, 7)
            fft = partial(fftn, s=fast_shape, axes=axes)
            ifft = partial(ifftn, s=fast_shape, axes=axes)

            fixed_image[np.logical_not(fixed_mask)] = 0.0
            moving_image[np.logical_not(moving_mask)] = 0.0

            # N-dimensional analog to rotation by 180deg is flip over all relevant axes.
            # See [1] for discussion.
            rotated_moving_image = self._flip(moving_image, axes=axes)
            rotated_moving_mask = self._flip(moving_mask, axes=axes)

            fixed_fft = fft(fixed_image)
            rotated_moving_fft = fft(rotated_moving_image)
            fixed_mask_fft = fft(fixed_mask)
            rotated_moving_mask_fft = fft(rotated_moving_mask)

            # Calculate overlap of masks at every point in the convolution.
            # Locations with high overlap should not be taken into account.
            number_overlap_masked_px = np.real(
                ifft(rotated_moving_mask_fft * fixed_mask_fft))
            number_overlap_masked_px[:] = np.round(number_overlap_masked_px)
            number_overlap_masked_px[:] = np.fmax(number_overlap_masked_px, eps)
            masked_correlated_fixed_fft = ifft(rotated_moving_mask_fft * fixed_fft)
            masked_correlated_rotated_moving_fft = ifft(
                fixed_mask_fft * rotated_moving_fft)

            numerator = ifft(rotated_moving_fft * fixed_fft)
            numerator -= masked_correlated_fixed_fft * \
                         masked_correlated_rotated_moving_fft / number_overlap_masked_px

            fixed_squared_fft = fft(np.square(fixed_image))
            fixed_denom = ifft(rotated_moving_mask_fft * fixed_squared_fft)
            fixed_denom -= np.square(masked_correlated_fixed_fft) / \
                           number_overlap_masked_px
            fixed_denom[:] = np.fmax(fixed_denom, 0.0)

            rotated_moving_squared_fft = fft(np.square(rotated_moving_image))
            moving_denom = ifft(fixed_mask_fft * rotated_moving_squared_fft)
            moving_denom -= np.square(masked_correlated_rotated_moving_fft) / \
                            number_overlap_masked_px
            moving_denom[:] = np.fmax(moving_denom, 0.0)

            denom = np.sqrt(fixed_denom * moving_denom)

            # Slice back to expected convolution shape.
            numerator = numerator[final_slice]
            denom = denom[final_slice]
            number_overlap_masked_px = number_overlap_masked_px[final_slice]

            # Pixels where `denom` is very small will introduce large
            # numbers after division. To get around this problem,
            # we zero-out problematic pixels.
            tol = 1e3 * eps * np.max(np.abs(denom), axis=axes, keepdims=True)
            nonzero_indices = denom > tol

            out = np.zeros_like(denom)
            out[nonzero_indices] = numerator[nonzero_indices] / denom[nonzero_indices]
            np.clip(out, a_min=-1, a_max=1, out=out)

            # Apply overlap ratio threshold
            number_px_threshold = overlap_ratio * np.max(number_overlap_masked_px,
                                                         axis=axes, keepdims=True)
            out[number_overlap_masked_px < number_px_threshold] = 0.0
            return out


    def _flip(self, arr, axes=None):
        """ Reverse array over many axes. Generalization of arr[::-1] for many
        dimensions. If `axes` is `None`, flip along all axes. """
        if axes is None:
            reverse = [slice(None, None, -1)] * arr.ndim
        else:
            reverse = [slice(None, None, None)] * arr.ndim
            for axis in axes:
                reverse[axis] = slice(None, None, -1)

        return arr[tuple(reverse)]

