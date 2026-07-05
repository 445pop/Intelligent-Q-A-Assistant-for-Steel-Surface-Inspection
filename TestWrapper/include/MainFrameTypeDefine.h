#pragma once

#include <vector>
#include "SpinnakerDefs.h"

//主窗口类型定义头文件

//子窗口类型
enum ChildDlgType
{
	DLG_TOOLBAR,              //工具栏窗口
	DLG_PLANARCONTOUR,        //平面轮廓窗口
	DLG_IMAGEMODE,            //图像模式窗口
	DLG_OUTMEASURE,           //OUT测量窗口
	DLG_HEIGHTMAP2D           //二维高度图窗口
};

//菜单状态控制
enum  MenuStateControl
{
	STACTRL_CLOSEDOCKPANE,            //当主菜单隐藏或显示时，更新“显示”菜单
	STACTRL_MEASURESTARTING,          //测量开始时置灰菜单
	STACTRL_3D_DISPLAY                //控制“显示”菜单中“三维显示的状态”
};

//当前系统工作模式
enum SysWorkMode
{
	WORKMODE_NORMAL,                 //无工作模式
	WORKMODE_MEASURESTARTING,        //测量开始模式
	//WORKMODE_MEASUREENDING,        //测量结束模式
	WORKMODE_PLAYBACK                //数据回放模式
};

//平面轮廓数据、二维高度图数据
struct ContourData
{
	double *dataX=nullptr,*dataZ=nullptr;//轮廓数据缓冲区指针
	size_t contourDataWritePtr, contourDataReadPtr;//轮廓数据写指针和读指针
	size_t unProcessedData;//未处理的数据量

	ContourData(size_t dataLength)
	{
		dataX = new double[dataLength]();
		dataZ = new double[dataLength]();
		contourDataWritePtr = contourDataReadPtr= unProcessedData = 0;
	}

	~ContourData()
	{
		delete[] dataX; dataX = nullptr;
		delete[] dataZ; dataZ = nullptr;
	}
};

//轮廓图像数据
struct ContourImage
{
	unsigned char* imageData = nullptr;//轮廓图像数据
	size_t contourImageWritePtr, contourImageReadPtr;//轮廓图像数据写指针和读指针
	size_t unProcessedData;//未处理的数据量

	int nBpp = 0;//通道数
	int width=0;//图像宽
	int  height=0;//图像高

	ContourImage(size_t dataLength)
	{
		imageData = new unsigned char[dataLength]();
		contourImageWritePtr = contourImageReadPtr =unProcessedData = 0;
	}

	~ContourImage()
	{
		delete[] imageData; imageData = nullptr;
	}
};

#if 0
struct profile_Point
{
	double x;
	double z;
};

#pragma pack(1)
struct Head_Countours
{
	uint16_t control;
	uint16_t attributeSize;
	uint32_t count;
	uint32_t width;
	uint32_t xScale;
	uint32_t zScale;
	int32_t xOffset;
	int32_t zOffset;
	uint8_t source;
	uint32_t exposure;
	uint8_t reserved;
	int32_t streamStep;
	int32_t streamStepld;
	std::vector<profile_Point> ranges;
	//std::vector<int16_t> ranges;
};
#pragma pack()
#endif

#if 0
//3维点
struct CPoint3D
{
private:
	float x,y,z;

public:
	CPoint3D()
	{
		x = y = z = 0.0;
	}

	CPoint3D(float _x,float _y,float _z)
	{
		x = _x;
		y = _y;
		z = _z;
	}

	CPoint3D(CPoint3D& other)
	{
		x = other.x;
		y = other.y;
		z = other.z;
	}

	void setX(float _x)
	{
		x = _x;
	}

	void setY(float _y)
	{
		y = _y;
	}

	void setZ(float _z)
	{
		z = _z;
	}

	float getX()
	{
		return x;
	}

	float getY()
	{
		return y;
	}

	float getZ()
	{
		return z;
	}
};
#endif

enum ColorType
{
	CLR_MONO,     //黑白
	CLR_COLOR     //彩色
};

struct OutMeasureInfo
{
	bool isValid;                   //是否已经设置
	bool isChecked;                 //是否被选中
	std::wstring OutMeasureName;	//OUT测量名称
	float OutMeasureValue;          //OUT测量值     

	OutMeasureInfo()
	{
		isValid = FALSE;
		isChecked = FALSE;
		OutMeasureName;
		OutMeasureValue = 0;
	}

	void setOutResult(FHJD_3D::OutResult/*&*/ outResult)
	{
		isValid = outResult.isvalid;
		//isChecked = FALSE;
		OutMeasureName = outResult.out_name.append(_T("-")).append(outResult.dif_name);
		OutMeasureValue = outResult.out_value;
	}
};

#ifndef PI
#define PI   3.1415926535897932384626433832795
#endif