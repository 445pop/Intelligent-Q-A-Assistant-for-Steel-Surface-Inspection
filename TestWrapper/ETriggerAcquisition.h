// 相机的采集设置（不需要改）
#pragma once
#ifndef ETRIGGERACQUISITION__H
#define ETRIGGERACQUISITION__H

#include "stdafx.h"
#include "buffIO.h"
#include "define.h"
#include  "plc.h"
#include "save_img.h"

using namespace FHJD_3D;

int ETAcquisition(std::string &filename, std::string& ip, int cameraid)
{
	//如果IP为空 结束
	if (ip == "")
	{
		return -1;
	}

	FHDevicesInterface* pImp = CreateFHDevices();
	std::vector<std::shared_ptr<DeviceControlInterface>> deviceList = pImp->getDeviceList();
	//测试使用的设备 IP 地址
	std::string ipAddress = ip;
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
	std::this_thread::sleep_for(std::chrono::milliseconds(30));

	do
	{

		if (ipAddress == "")
		{
			return -1;
		}

		if (!deviceControllor)
		{
			break;
		}

		if (!deviceControllor->Open(ipAddress.c_str()))//c_str() 以 char* 形式传回 string 内含字符串
		{
			std::cout << "设备打开失败" << std::endl;
			break;
		}


		//设置时间触发
		bool ok = deviceControllor->TrigByTime();
		if (!ok)
		{
			std::cout << "时间触发失败" << std::endl;
			break;
		}
		else {
			std::this_thread::sleep_for(std::chrono::milliseconds(30));
		}

		//设置成像光亮控制参数
		ok = deviceControllor->SetLaserPower(0);
		if (!ok)
		{
			std::cout << "光亮控制" << std::endl;
			break;
		}
		std::this_thread::sleep_for(std::chrono::milliseconds(30));

		//设置曝光时间
		ok = deviceControllor->SetExposureTime(250);
		if (!ok)
		{
			std::cout << "曝光时间" << std::endl;
			break;
		}
		std::this_thread::sleep_for(std::chrono::milliseconds(30));

		//设置采样频率
		ok = deviceControllor->SetCapFrequency(2700);
		 
		if (!ok)
		{
			std::cout << "采样频率设置失败" << std::endl;
			break;
		}
		std::this_thread::sleep_for(std::chrono::milliseconds(30));


		//获取相机温度
		float temp;
		ok = deviceControllor->GetTemperature(temp);
		if (!ok)
		{
			std::cout << "相机温度获取失败" << std::endl;
			break;
		}
		std::cout << ipAddress << "   :  " << temp << std::endl;
		std::this_thread::sleep_for(std::chrono::milliseconds(30));

		// 设置Z方向画幅范围
		uint8_t z_mode = 1;
		uint16_t z_offset = 540;
		ok = deviceControllor->SetZRange(z_mode, z_offset);
		if (!ok)
		{
			std::cout << "画幅设置失败" << std::endl;
			break;
		}
		std::this_thread::sleep_for(std::chrono::milliseconds(30));

		std::cout << ipAddress << "： 开始采集！！！！！" << std::endl;

		//初始化未过钢信息
		if (cameraid == 0)
			httpFinish();

		//获取点云数据和原图数据
		//uint32_t imglast = 0;
		uint64_t lastframe = 0;
		for (;;)//可以看做是回调函数的另一种形式，只不过回调的发起方从相机转变成了上位机
		{
			if (SlabArrived == true) {
				if (cameraid == 0)
					httpMysql();
				deviceControllor->SetLaserPower(100);
				while (SlabArrived == true) {
					auto data = deviceControllor->GetLatestFrame();
					//auto image_data = deviceControllor->GetLatestImage();
					if (data)
					{
						uint64_t nowframe = data->frameId;
						if (nowframe != lastframe) {
							callback(cameraid, data);//定义在buffIO.h里的callback函数，进行推入缓存操作!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
							lastframe = data->frameId;
						}
					}
					/*if (image_data)
					{
						uint32_t imgframe = image_data->frameId;
						if (imgframe != imglast) {
							imgback(cameraid, image_data, filename);
							imglast = image_data->frameId;
						}
					}*/
				}
				deviceControllor->SetLaserPower(0);
				if (cameraid == 0) {
					httpFinish();
					httpLinux();

				}				
			}
		}
		deviceControllor->Close();
	} while (0);
	DestroyFHDevices(pImp);
	return 0;
}
#endif