//原始数据转成图像数据(可能要改）
#pragma once
#ifndef DEPTH123_H
#define DEPTH123_H

#include <iostream>
#include <string>
#include <opencv2/core/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/highgui.hpp>

#include"define.h"

using namespace cv;

//切边操作，去除边缘噪声，根据每列像素和切边，返回切边后的图像掩膜
Mat cutEdge(Mat mask1) {
	Mat mask2 = mask1 / 255;
	mask2.convertTo(mask2, CV_32FC1);
	Mat colsum(1, COLUMN, CV_32FC1);
	reduce(mask2, colsum, 0, REDUCE_SUM);
	Mat coll = colsum.colRange(0, COLUMN - 1);
	Mat colr = colsum.colRange(1, COLUMN);
	Mat sub = colr - coll;
	Mat subIdx;
	double smin, smax, idmin, idmax;
	Point smind, smaxd;
	sortIdx(sub, subIdx, SORT_ASCENDING);
	minMaxLoc(subIdx.colRange(0, CUTEDGE), NULL, &idmax, NULL, NULL);
	minMaxLoc(subIdx.colRange(COLUMN - 1 - CUTEDGE, COLUMN - 1), &idmin, NULL, NULL, NULL);
	mask1.colRange(0, idmin) = 0;
	mask1.colRange(idmax, COLUMN) = 0;
	return mask1;
}

//相机数据转深度图
bool toDepth(float pz[MAX_SIZE][COLUMN], std::string picPath, std::string grayPath, uint8_t pc[MAX_SIZE][COLUMN], std::string cPath, std::string orgPath) {
	bool isempty = true;
	Mat img(MAX_SIZE, COLUMN, CV_32FC1, pz); //获取z数据存成二维矩阵
	Mat cen(MAX_SIZE, COLUMN, CV_8UC1, pc); //获取c数据存成二维矩阵
	Mat zer = cv::Mat::zeros(MAX_SIZE, COLUMN, CV_8UC1);
	Mat intMat, mask1, mask,cmask, nmask, image,dst;
	double zmin, zmax, omin, omax, zmed;

	mask = cv::Mat(img == img); //获取非nan值掩膜
	cmask = cutEdge(mask);
	int row = 50;
	int tn = countNonZero(mask.rowRange(0, row));
	int bn = countNonZero(mask.rowRange(MAX_SIZE - row, MAX_SIZE));

	//过滤空图，即图像中无钢板的图像
	if (tn > ISEMPTY || bn > ISEMPTY) {
		isempty = false;
		int dz = 45, cz = 5;
		minMaxLoc(img, &zmin, &zmax, NULL, NULL, mask);
		if (zmax - zmin > 2 * cz) {
			zmax = zmax - cz;
			zmin = zmin + cz;
		}

		//计算分布密度
		int bins[] = { zmax - zmin };
		if (bins[0] == 0) {
			zmed = zmax;
		}
		else {
			Mat hist;
			float hranges[] = { zmin,zmax };
			const float* ranges[] = { hranges };
			const int channels[] = { 0 };
			calcHist(&img, 1, channels, mask, hist, 1, bins, ranges);
			double hmin, hmax;
			Point hind;

			//获取z值最多的bin
			minMaxLoc(hist, NULL, &hmax, NULL, &hind);
			zmed = zmin + hind.y + 0.5;
		}
		omin = zmed - dz;
		omax = zmed + dz;
		mask1 = cv::Mat(img > omin & img < omax); //根据z值粗糙过滤
		mask1 = cutEdge(mask1);
		bitwise_not(mask1, nmask);
		bitwise_not(cmask, cmask);
		image = (img - zmed) * 2.8 + 128;//z值转0-255
		zer.copyTo(intMat, nmask);//噪声位置像素值赋0
		image.convertTo(intMat, CV_8UC1);
		cv::imwrite(orgPath, intMat);

		//限制对比度的自适应直方图均衡化
	    //构建CLAHE 对象
		Ptr<CLAHE> clahe = createCLAHE(2.0, Size(8, 8));
		// 限制对比度的自适应直方图均衡化
		clahe->apply(intMat, dst);
		cv::imwrite(grayPath, dst);

		zer.copyTo(cen, cmask);//噪声位置像素值赋0
		cv::imwrite(cPath, cen);
	}
	return isempty;
}

#endif
