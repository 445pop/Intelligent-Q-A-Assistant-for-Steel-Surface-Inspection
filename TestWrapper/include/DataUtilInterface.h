#ifndef FHJD_3D_DATAUTIL_INTERFACE_H
#define FHJD_3D_DATAUTIL_INTERFACE_H

#include <memory>
#include <vector>
#include "DeviceControlInterface.h"

namespace FHJD_3D
{
	class DataUtilInterface
	{
	public:
		//*************************************************
		//说 明： 获取设备列表
		//参 数：
		//      [in] : update : bool , 为true时重新搜索，否则直接获取SDK初始化时候获取到的相机列表
		//返回值：
		//备注： 
		//*************************************************
		virtual std::vector<std::shared_ptr<DeviceControlInterface>> getDeviceList(/*bool update*/) = 0;
	};
	extern "C" __declspec(dllexport) DataUtilInterface* __cdecl CreateDataUtiI();
	extern "C" __declspec(dllexport) void __cdecl DestroyDataUtiI(void *handle);

}


#endif

