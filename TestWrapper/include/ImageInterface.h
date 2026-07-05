#pragma once

#include "SpinnakerDefs.h"

namespace FHJD_3D
{
	class ImageInterface
	{
	public:
		ImageInterface() {}
		virtual ~ImageInterface() {}

	public:
		virtual uint8_t* GetData() = 0;

		//virtual uint32_t GetBufferSize() = 0;

		virtual int GetWidth() = 0;

		virtual int GetHeight() = 0;

		virtual uint8_t GetBitsPerPixel() = 0;

		virtual uint8_t GetNumChannels() = 0;


		virtual void Release() = 0;

		virtual uint64_t GetID() = 0;

		virtual void* GetPrivateData() const = 0;

		//virtual size_t GetBufferSize() const = 0;

		virtual size_t GetWidth() const = 0;

		virtual size_t GetHeight() const = 0;

		virtual size_t GetStride() const = 0;

		virtual size_t GetBitsPerPixel() const = 0;

		virtual size_t GetNumChannels() const = 0;

		virtual size_t GetXOffset() const = 0;

		virtual size_t GetYOffset() const = 0;

		virtual size_t GetXPadding() const = 0;

		virtual size_t GetYPadding() const = 0;

		virtual uint64_t GetFrameID() const = 0;

		virtual size_t GetPayloadType() const = 0;

		virtual PixelFormatEnums GetPixelFormat() const = 0;

		virtual bool IsIncomplete() const = 0;

		virtual uint64_t GetTimeStamp() const = 0;

		virtual void Save(const char* pFilename, ImageFileFormat format = FROM_FILE_EXT) = 0;

		virtual void Save(const char* pFilename, BMPOption & pOption) = 0;

		virtual bool HasCRC() const = 0;

		virtual bool CheckCRC() const = 0;

		virtual size_t GetImageSize() const = 0;

		virtual void CopyTo(ImageInterface**)=0;
	};

}