#pragma once

#include "ProfileInterface.h"

namespace FHJD_3D
{
	class HeightMapOutputInterface
	{
	public:
		//virtual bool Insert(ProfileInterface* frame) = 0;
		virtual bool Insert(uint8_t* avgLuminance, uint32_t profileWidth) = 0;
		virtual void getHeightMapSize(uint32_t&, uint32_t&)=0;
		virtual void GetLatestHeightMap(unsigned char*) = 0;
		virtual void InitHeightMap(uint32_t profileWidth) = 0;
		virtual uint32_t GetCurProfileCnt()=0;
		virtual ~HeightMapOutputInterface() {};
		virtual void ClearFrames() = 0;
	};
}
