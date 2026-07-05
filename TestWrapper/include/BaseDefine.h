#ifndef FHJD_3D_BASE_DEFINE__H
#define FHJD_3D_BASE_DEFINE__H

#include <stdint.h>

namespace FHJD_3D
{

#pragma pack(push, 1)

	enum DEVICELOCATION
	{
		DEVICE_LEFT,			//左边传感头
		DEVICE_RIGHT,			//右边传感头
	};

	/// \brief 轮廓点
	struct Point16f
	{
		float z; ///< Z
		float x; ///< X
		uint8_t c; ///< C

		Point16f &operator = (const Point16f &src)
		{
			z = src.z;
			x = src.x;
			c = src.c;

			return *this;
		}
	};

	struct Point16c
	{
		int16_t z;
		int16_t x;
	};

	struct Point16s
	{
		uint16_t z;
		uint16_t x;
	};

	struct Point16si
	{
		uint16_t z;
		Point16si &operator = (const Point16si &rhs) {
			this->z = rhs.z;
			return *this;
		}

	};

	struct Point24f
	{
		float x;
		float z;
		float c;

		Point24f &operator = (const Point24f &src)
		{
			x = src.x;
			z = src.z;
			c = src.c;

			return *this;
		}
	};

#pragma pack(pop)

}

#endif
