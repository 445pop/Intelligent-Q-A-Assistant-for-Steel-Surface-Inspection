//缓存操作头文件，定义了帧数据推入缓存的callback函数,将相机数据存入缓存区(不需要改)
#pragma once
#ifndef BUFFIO123_H
#define BUFFIO123_H

#include "define.h"
#include<BaseDefine.h>

HANDLE sems_save0[BUFFER_SIZE]; //给保存线程的信号量
HANDLE sems_save1[BUFFER_SIZE];
HANDLE sems_save2[BUFFER_SIZE];
HANDLE sems_save3[BUFFER_SIZE];

using namespace FHJD_3D;

struct Buffer {
	FHJD_3D::Point16f points[MAX_SIZE][POINT_NUM];
};

Buffer* pBuf0[BUFFER_SIZE]; //声明缓存区个数，具体类型根据实际情况修改
Buffer* pBuf1[BUFFER_SIZE];
Buffer* pBuf2[BUFFER_SIZE];
Buffer* pBuf3[BUFFER_SIZE];

void callback(int cameraid, std::shared_ptr<ProfileData>data)
{
	//缓存区存在三种情况 1、缓存区空，2、缓存区非空，但是未满 3、缓存区满
	switch (cameraid) { //四台相机
	case 0:
	{
		static uint16_t cur0_buffer_id = 0;
		static uint16_t row0_num = 0;
		//数据拷贝到缓存区
		memcpy(pBuf0[cur0_buffer_id]->points[row0_num], data->points, BYTE_NUM);
		if (row0_num == MAX_SIZE - 1) {
			if (!ReleaseSemaphore(sems_save0[cur0_buffer_id], 1, NULL)) {
				std::cout << "相机0缓存区写入错误！" << std::endl;
			}
			cur0_buffer_id = (cur0_buffer_id + 1) % BUFFER_SIZE;
		}
		row0_num = (row0_num + 1) % MAX_SIZE;
		break;
	}
	case 1:
	{
		static uint16_t cur1_buffer_id = 0;
		static uint16_t row1_num = 0;
		memcpy(pBuf1[cur1_buffer_id]->points[row1_num], data->points, BYTE_NUM);
		if (row1_num == MAX_SIZE - 1) {
			if (!ReleaseSemaphore(sems_save1[cur1_buffer_id], 1, NULL)) {
				std::cout << "相机1缓存区错误！" << std::endl;
			}
			cur1_buffer_id = (cur1_buffer_id + 1) % BUFFER_SIZE;
		}
		row1_num = (row1_num + 1) % MAX_SIZE;
		break;
	}
	case 2:
	{
		static uint16_t cur2_buffer_id = 0;
		static uint16_t row2_num = 0;
		memcpy(pBuf2[cur2_buffer_id]->points[row2_num], data->points, BYTE_NUM);

		if (row2_num == MAX_SIZE - 1) {
			if (!ReleaseSemaphore(sems_save2[cur2_buffer_id], 1, NULL)) {
				std::cout << "相机2存缓存区错误！" << std::endl;
			}
			cur2_buffer_id = (cur2_buffer_id + 1) % BUFFER_SIZE;
		}
		row2_num = (row2_num + 1) % MAX_SIZE;
		break;
	}
	case 3:
	{
		static uint16_t cur3_buffer_id = 0;
		static uint16_t row3_num = 0;
		memcpy(pBuf3[cur3_buffer_id]->points[row3_num], data->points, BYTE_NUM);
		if (row3_num == MAX_SIZE - 1) {
			if (!ReleaseSemaphore(sems_save3[cur3_buffer_id], 1, NULL)) {
				std::cout << "相机3存缓冲区错误！" << std::endl;
			}
			cur3_buffer_id = (cur3_buffer_id + 1) % BUFFER_SIZE;
		}
		row3_num = (row3_num + 1) % MAX_SIZE;
		break;
	}
	}
}
#endif