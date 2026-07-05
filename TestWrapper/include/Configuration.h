#pragma once

//#define ReservedToolBar                  //保留工具栏

#define WarpUnusedMenu                     //隐藏不常用的菜单

//#ifndef BLOCK_MOUSE_ZOOM
//#define BLOCK_MOUSE_ZOOM                   //使能图表和图像显示控件的框选放大功能
//#endif

#define REFRESH_RATE   5                   //主界面数据每秒钟刷新的次数

//#define EnableMemoryLeakDetect             //使能内存泄漏检测

#ifdef EnableMemoryLeakDetect
#define EnableMemoryAllocBreak             //使能内存分配中断
#endif

#define OUT_MEASURE_CNT 8                  //OUT测量的数量

#define ENABLE_TERMINAL_OUTPUT            //使能终端打印信息输出

#define ENABLE_DEVELOPER_DEBUG              //开放内部调试功能，主要指保存图像的功能

const unsigned int SENSOR_IMAGE_WIDTH = 1920;     //图像宽度
const unsigned int SENSOR_IMAGE_HEIGHT = 1080;    //图像高度

const unsigned char WIDTH_ALIGN = 64;//横向对齐倍数
const unsigned char HEIGHT_ALIGN = 4;//纵向对齐倍数

const unsigned __int64 DISK_FREE_SPACE_THRESHOLD = 8* 1024 * 1024;//8M，磁盘剩余空间阈值
