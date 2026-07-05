#ifndef FHJD_3D_DEVICE_INTERFACE_H
#define FHJD_3D_DEVICE_INTERFACE_H

#include "DeviceControlInterface.h"
#include <memory>

namespace FHJD_3D
{
	/// \brief 设备管理接口类
	class FHDevicesInterface
	{
	public:
		/// \brief 获取设备列表
		/// \return 设备列表
		virtual std::vector<std::shared_ptr<DeviceControlInterface>> getDeviceList() = 0;

		/// \brief 获取当前SDK版本信息
		/// \param [out] versionnumber 版本编码编号
		/// \param [out] builddate 编译日期
		/// \return true-成功，false-失败
		virtual bool GetCurrentVersion(std::string& versionnumber, std::string& builddate) = 0;
	};

	/// \brief 创建设备管理对象
	/// \return 设备管理接口指针
	extern "C" __declspec(dllexport) FHDevicesInterface* _cdecl CreateFHDevices();

	/// \brief 销毁设备管理对象
	/// \param [in] handle 设备管理接口指针
	extern "C" __declspec(dllexport) void __cdecl DestroyFHDevices(void *handle);
}
#endif
