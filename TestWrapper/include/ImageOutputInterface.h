#pragma once

#include "ImageInterface.h"


namespace FHJD_3D
{
	class ImageOutputInterface
	{
	public:
		virtual void Insert(ImageInterface* frame) = 0;
		virtual ImageInterface* GetLatestFrame() = 0;
		virtual ImageInterface* GetFirstFrame() = 0;
		virtual ~ImageOutputInterface() {};
		virtual void ClearFrames() = 0;
	};
}