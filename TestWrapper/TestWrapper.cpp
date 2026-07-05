// TestWrapper.cpp : 定义控制台应用程序的入口点。
//

#include "stdafx.h"

#include "DeviceControlInterface.h"
#include "FHDevicesInterface.h"
#include <thread>
#include <iostream>
using namespace FHJD_3D;
void usage() {
	printf("Please input the device ip address like 192.168.8.21");
}
int main(int argc, char* argv[])
{
	if (argc < 2)
	{
		usage();
		return 0;
	}
	FHDevicesInterface* pImp = CreateFHDevices();
	std::vector<std::shared_ptr<DeviceControlInterface>> deviceList = pImp->getDeviceList();
	//测试使用的设备 IP 地址
	std::string ipAddress = argv[argc - 1];
	std::shared_ptr<DeviceControlInterface> deviceControllor;
	for (int i = 0; i < deviceList.size(); i++)
	{
		std::string devIp = "";
		if (!deviceList[i]->GetSensorAddress(devIp))
		{
			continue; 
		}
		if (devIp == ipAddress)
		{
			deviceControllor = deviceList[i];
			break;
		}
	}

	do 
	{
		if (!deviceControllor)
		{
			break;
		}

		if (!deviceControllor->Open(ipAddress.c_str()))
		{
			break;
		}

		// 设置连续触发
		bool ok = deviceControllor->TrigByTime();
		if (!ok)
		{
			break;
		}

		//设置采样频率
		ok = deviceControllor->SetCapFrequency(5);
		if (!ok)
		{
			break;
		}
		
		//获取曝光时间
		uint32_t exposureTime = 0;
		ok = deviceControllor->GetExposureTime(exposureTime);
		if (!ok)
		{
			break;
		}
		std::cout << "ExposureTime:" << exposureTime;

		//获取最新帧轮廓数据
		for (;;)
		{
			auto data = deviceControllor->GetLatestFrame();
			if (data)
			{
				std::cout << "frameId:" << data->frameId << " y:" << data->time_s_cnt << std::endl;
			}
			std::this_thread::sleep_for(std::chrono::milliseconds(50));
		}
		deviceControllor->Close();
	} while (0);

	DestroyFHDevices(pImp);
    return 0;
}

