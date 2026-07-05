#ifndef _MEASURE_MODE_DATA_H_
#define _MEASURE_MODE_DATA_H_

#include <string>
#include <vector>
#include <stdint.h>
#include "uvtpinfo.h"

enum MEASURE_MODE
{
	MEASURE_HEIGHT,			//高度
	MEASURE_HEIGHTDIFF,		//高度差
	MEASURE_WIDTH,			//宽度
	MEASURE_CENTRE,			//中心位置
	MEASURE_RADIUS,			//半径
	MEASURE_DISBETPOINTS,	//两点间距离
	MEASURE_DISBETPOINTLINE,//点和直线间距离
	MEASURE_ANGLE,			//从水平起的角度
	MEASURE_ANGLELINES,		//两直线间的角度
	MEASURE_DISBETLINES,	//平行线间距离
	MEASURE_NULL			//不测量
};
enum POSITION_MEASURE
{
	POSITION_AV,		//平均
	POSITION_HI,		//峰值
	POSITION_LO,		//谷值
	POSITION_ARC,		//弯曲点
	POSITION_CRO,		//交点
	POSITION_OUT,		//边缘
	POSITION_LINE,		//直线
	POSITION_LEFT,		//左端点
	POSITION_RIGHT		//右端点
};


typedef std::numeric_limits<float> nanInfo;
float const NaN_f = nanInfo::quiet_NaN();


enum MEASURE_DIRECTION		//检测方向
{
	LEFT_TO_RIGHT,		//从左往右
	RIGHT_TO_LEFT,		//从右往左
};

enum OUT_DIRECTION			//边缘方向
{
	DIRECTION_UP,		//上升
	DIRECTION_DOWN,		//下降
};

enum FILTER_TYPE
{
	FILTER_OFF,			//关闭
	FILTER_AVE,			//移动平均
	FILTER_HI,			//低通滤波器
	FILTER_LO,			//高通滤波器
};

struct DirectionXCorrect       //x方向轮廓位置校准
{
	float  left = 0;										//矩形框左边
	float  right = 0;										//矩形框右边
	float  ave = 0;											//边缘级别
	MEASURE_DIRECTION measureDirection = LEFT_TO_RIGHT;		//检测方向
	OUT_DIRECTION outDirection = DIRECTION_UP;				//边缘方向
	int index = 1;											//检测点
	bool isValid = false;									//是否有效
};



class BasePosition		//OUT测量目标对象基类
{
public:
	BasePosition() {};
	virtual ~BasePosition() {};

	void *device = nullptr;

	virtual bool ShowRect2()
	{
		return true;
	}

	virtual void setXCorrectFalg(bool flag)  //设置是否进行X方向轮廓位置校正
	{
		hasXCorrect = flag;
	}

	virtual bool getXCorrectFlag()			//获取是否进行X方向轮廓位置校正
	{
		return hasXCorrect;
	}

	void setValue(float value)
	{
		m_value = value;
	}

	float getValue()
	{
		return m_value;
	}

	std::wstring getPositionname()			//获取对象名称
	{ 
		return m_positionname; 
	};

	POSITION_MEASURE getPosition()			//获取对象模式
	{ 
		return  m_position; 
	};

	void setMode(POSITION_MEASURE position)	//设置对象模式
	{
		m_position = position;
		switch (position)
		{
		case POSITION_AV:
			m_positionname = L"平均";
			break;
		case POSITION_HI:
			m_positionname = L"峰值";
			break;
		case POSITION_LO:
			m_positionname = L"谷值";
			break;
		case POSITION_ARC:
			m_positionname = L"弯曲点";
			break;
		case POSITION_CRO:
			m_positionname = L"交点";
			break;
		case POSITION_OUT:
			m_positionname = L"边缘";
			break;
		case POSITION_LINE:
			m_positionname = L"直线";
			break;
		case POSITION_LEFT:
			m_positionname = L"左端点";
			break;
		case POSITION_RIGHT:
			m_positionname = L"右端点";
			break;
		default:
			break;
		}
	};

	void setLeft(float value)
	{
		left = value;
	}

	void setRight(float value)
	{
		right = value;
	}

	float getLeft()
	{
		return left;
	}
	float getRight()
	{
		return right;
	}

	virtual float getAve()
	{
		return 0.0;
	}
protected:

	POSITION_MEASURE m_position;		//对象类型
	std::wstring m_positionname;		//对象名称
	float m_value;						//对象值

	float left = NaN_f;						//对象左边值
	float right = NaN_f;					//对象右边值

	bool hasXCorrect = false;			//是否有X方向轮廓位置校正

};
class PositionAV :public BasePosition	//OUT测量	测量平均值
{
public:
	PositionAV() { setMode(POSITION_AV); };
	virtual ~PositionAV() {  };




};

class PositionLeft :public BasePosition	//OUT测量	测量左端点
{
public:
	PositionLeft() { setMode(POSITION_LEFT); };
	virtual ~PositionLeft() {  };

};

class PositionRight :public BasePosition	//OUT测量	测量右端点
{
public:
	PositionRight() { setMode(POSITION_RIGHT); };
	virtual ~PositionRight() {  };

};
class PositionHI :public BasePosition	//OUT测量	测量峰值
{
public:
	PositionHI() { setMode(POSITION_HI); };
	virtual ~PositionHI() {};

};
class PositionLO :public BasePosition	//OUT测量	测量谷值
{
public:
	PositionLO() { setMode(POSITION_LO); };
	virtual ~PositionLO() {};

};
class PositionArc :public BasePosition	//OUT测量	测量弯曲点
{
public:
	PositionArc() { setMode(POSITION_ARC); };
	virtual ~PositionArc() {};


};
class PositionCRO :public BasePosition	//OUT测量	测量交点
{
public:
	PositionCRO() { setMode(POSITION_CRO); };
	virtual ~PositionCRO() {};
	bool ShowRect2()
	{
		return isShowRect2;
	}

	bool isShowRect2 = false;

	float getLeft2()			//获取区域2的左边界
	{
		return left2;
	}
	void setLeft2(float value)	//设置区域2的左边界
	{
		left2 = value;
	}

	float getRight2()			//获取区域2的右边界
	{
		return right2;
	}

	void setRight2(float value)	//设置区域2的右边界
	{
		right2 = value;
	}

	float left2 = NaN_f;		//区域2的左边界
	float right2 = NaN_f;		//区域2的右边界


};
class PositionOUT :public BasePosition	//OUT测量	测量边缘
{
public:
	PositionOUT() { setMode(POSITION_OUT); };
	virtual ~PositionOUT() {};
	float getAve()
	{
		return ave;
	}
	float ave = 0.0;
	MEASURE_DIRECTION measureDir = LEFT_TO_RIGHT;
	OUT_DIRECTION   outDir = DIRECTION_UP;
	int index = 1;
};

class PositionLINE :public BasePosition	//OUT测量	测量直线间距离
{
public:
	PositionLINE() { setMode(POSITION_LINE); };
	virtual ~PositionLINE() {};

	bool ShowRect2()
	{
		return isShowRect2;
	}

	bool isShowRect2 = false;

	float getLeft2()			//获取区域2的左边界
	{
		return left2;
	}
	void setLeft2(float value)	//设置区域2的左边界
	{
		left2 = value;
	}

	float getRight2()			//获取区域2的右边界
	{
		return right2;
	}

	void setRight2(float value)	//设置区域2的右边界
	{
		right2 = value;
	}

	float left2 = NaN_f;		//区域2的左边界
	float right2 = NaN_f;		//区域2的右边界


};


class BaseMeasureModeData		//OUT测量	测量模式基类				
{
public:
	BaseMeasureModeData() {};
	virtual ~BaseMeasureModeData() 
	{
	};
	BasePosition * position = nullptr;				//基准对象
	BasePosition * m_measureposition = nullptr;		//测量对象
	virtual void setPosition(BasePosition* pos)		//设置基准对象
	{
		if (pos == position)
		{
			return;
		}
		if (position != nullptr)
		{
			delete position;
			position = nullptr;
		}
		/*if (position)
		{
			delete position;
		}
		if (m_measureposition)
		{
			delete m_measureposition;
		}*/
		position = pos;
	};
	

	void setMeasurePosition(BasePosition* pos)	//设置测量对象
	{
		if (pos == m_measureposition)
		{
			return;
		}
		if (m_measureposition != nullptr)
		{
			delete m_measureposition;
			m_measureposition = nullptr;
		}
		m_measureposition = pos;
	}

	std::wstring getModename() { return m_modename; };	//获取OUT测量模式名称

	MEASURE_MODE getMode() { return  m_mode; };			//获取OUT的测量模式

	void setMode(MEASURE_MODE mode)						//设置OUT的测量模式
	{ 
		m_mode = mode; 
	
		switch (mode)
		{
		case MEASURE_HEIGHT:
			m_modename = L"高度";
			break;
		case MEASURE_HEIGHTDIFF:
			m_modename = L"高度差";
			break;
		case MEASURE_WIDTH:
			m_modename = L"宽度";
			break;
		case MEASURE_CENTRE:
			m_modename = L"中心位置";
			break;
		case MEASURE_DISBETPOINTS:
			m_modename = L"距离(点-点)";
			break;
		case MEASURE_DISBETPOINTLINE:
			m_modename = L"距离(点-直线)";
			break;
		case MEASURE_ANGLE:
			m_modename = L"从水平起角度";
			break;
		case MEASURE_ANGLELINES:
			m_modename = L"两直线间角度";
			break;
		case MEASURE_DISBETLINES:
			m_modename = L"平行线间距离";
			break;
		case MEASURE_RADIUS:
			m_modename = L"半径";
			break;
		case MEASURE_NULL:
		{
			m_modename = L"未测量";
			PositionAV *pAV = new PositionAV;
			PositionAV *pAV1 = new PositionAV;
			if (position !=nullptr)
			{
				delete position;
				position = nullptr;
			}
			if (m_measureposition != nullptr)
			{
				delete m_measureposition;
				m_measureposition = nullptr;
			}
			position = pAV;
			m_measureposition = pAV1;
			break;
		}

		default:
			break;
		}
	};


protected:

	MEASURE_MODE m_mode;			//测量模式
	std::wstring m_modename;		//测量模式名称
	
	

};
class HeightModeData:public BaseMeasureModeData			//OUT测量	高度测量模式
{
public:
	HeightModeData() { setMode(MEASURE_HEIGHT); };
	virtual ~HeightModeData() {};
	virtual void setPosition(BasePosition *pos) { position = pos; };

	
};
class HeightDiffModeData :public BaseMeasureModeData	//OUT测量	高度差测量模式
{
public:
	HeightDiffModeData() {};
	virtual ~HeightDiffModeData() {};

};

class LinesDisModeData :public BaseMeasureModeData		//OUT测量	平行线间距离测量模式
{
public:
	LinesDisModeData() {};
	virtual ~LinesDisModeData() {};

};
class CentreModeData :public BaseMeasureModeData		//OUT测量	中心位置测量模式
{
public:
	CentreModeData() {};
	virtual ~CentreModeData() {};
};
class WidthModeData :public BaseMeasureModeData			//OUT测量	宽度测量模式
{
public:
	WidthModeData() {};
	virtual ~WidthModeData() {};
};
class RadiusModeData :public BaseMeasureModeData		//OUT测量	半径测量模式
{
public:
	RadiusModeData() {};
	virtual ~RadiusModeData() {};
};
class NullModeData :public BaseMeasureModeData			//OUT测量	空测量模式
{
public:
	NullModeData() {};
	virtual ~NullModeData() {};
};

struct OUT_HANDLE
{
	bool isValid = false;
	float high = 50.000;			//上限
	float low =-50.000;				//下限
	float lag = 0;					//滞后
	int keeptimes = 0;				//测量值保持次数
	float cutdownfrequence = 0;		//切断频率
	int avetimes = 0;				//平均次数
	float makeup = 0;				//补偿值
	FILTER_TYPE filter = FILTER_OFF;//震动过滤器
	int ZeroTerminal = 0;			//Zero端子
	int ResertTerminal = 0;			//Resert端子
};


struct OUT_MEASURE							//OUT测量数据
{
	std::wstring o_name;					//OUT测量名称
	std::wstring dif_name = L"自定义名称";	//OUT测量别名
	BaseMeasureModeData data;				//OUT测量设置数据
	OUT_HANDLE handle;						//OUT测量处理数据
	bool isRead = true;						//数据是否准备就绪
};


enum SETTING_TYPE				//端子存储器中 OUT设置关系类型
{
	TYPE_AND,
	TYPE_OR
};

enum OUT_LEVEL					//OUT测量结果等级
{
	LEVEL_NULL = 0X0,
	LEVEL_HI = 0x1,
	LEVEL_GO = 0x2,
	LEVEL_LO = 0x4
};

//OUT测量信息
struct OUT_INFO
{
	int o_id;//OUT测量id
	//bool ischeck;
	std::wstring o_name;//OUT测量名称
	//OUT_LEVEL o_level;
	unsigned long o_triggerCondition;//触发条件

	OUT_INFO& operator=(const OUT_INFO& other)
	{
		if (this != &other)
		{
			o_id = other.o_id;
			o_name = other.o_name;
			o_triggerCondition = other.o_triggerCondition;
		}

		return *this;
	}
};

//端子配置信息
struct TERMINAL_INFO
{
	//int t_id;
	std::wstring t_name;//端子名称
	SETTING_TYPE s_type;//端子逻辑类型，And或者Or
	std::vector<OUT_INFO> v_outinfo;//OUT测量信息

	TERMINAL_INFO& operator=(const TERMINAL_INFO& _Right)
	{
		if (this != &_Right)
		{
			t_name = _Right.t_name;
			s_type = _Right.s_type;
			v_outinfo = _Right.v_outinfo;
		}

		return *this;
	}
};

#endif
