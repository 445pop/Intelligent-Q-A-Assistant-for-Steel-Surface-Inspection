//在此文件定义一些可能用到的宏
#pragma once
#ifndef DEFINE123_H
#define DEFINE123_H

#define MAX_SIZE 4096   //缓存区大小
#define POINT_NUM 4000  //每一帧取的点数
#define ADDITION 928  //切除一部分背景 
#define COLUMN POINT_NUM-ADDITION //最后获取的列数
#define BYTE_NUM  POINT_NUM*9//47760  //一帧的字节数
#define TOTAL_NUM  MAX_SIZE*(COLUMN) // 总的点数
#define BUFFER_SIZE 85  //缓存区个数，自定义
#define Devices_num 4   //当前服务器连接设备数量
#define CUTEDGE 15  //切边判断参数
#define ISEMPTY 7700

#endif // !DFINE123_H


