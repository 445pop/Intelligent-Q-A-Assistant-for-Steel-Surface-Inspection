#pragma once
#include <vector>
#include "BaseDefine.h"

namespace FHJD_3D
{
	/// \brief 轮廓头
	struct ProfileHead
	{
		uint64_t	frameId; //< 帧编号
		uint32_t	sampleLen; //< 匹配下采样轮廓点长度
		uint32_t    time_s_cnt; //< 时间戳秒，值为1970年到当前时间的秒总数
		uint32_t 	time_us_cnt; //< 时间戳微秒
		uint16_t	synEncNum; //< 外触发同步编号
		bool        isLeft;//< 左右轮廓标志
		ProfileHead():frameId(0)
					  ,sampleLen(0)
					  ,time_s_cnt(0)
					  ,time_us_cnt(0)
					  ,synEncNum(0)
					  ,isLeft(false)
		{}
	};

	struct ProfileData :ProfileHead
	{
		float y; ///< Y值
		uint32_t    width;	///< 轮廓点数	
		Point16f	points[0]; ///< 轮廓点
	};

	/// \brief 图像数据
	struct ImageData
	{
		uint32_t frameId; ///< 帧编号
		uint32_t width; ///< 宽度
		uint32_t height; ///< 高度
		uint8_t res[52]; ///< 预留
		uint8_t bits[0]; ///< 图像数据流，size=width*height
	};
}