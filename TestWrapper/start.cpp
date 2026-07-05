//程序入口main函数定义在这个文件，启动程序

#include "stdafx.h"
#include "http.h"
#include "main_acquisition.h"
#include "define.h"
#include "plc.h"

using namespace FHJD_3D;

SYSTEMTIME stCurTime;// 当前时间
std::string pdirectory; //定义时间文件夹

int main()
{
	//获取当前连接的设备数量
	FHDevicesInterface* pcon = CreateFHDevices();
	std::vector<std::shared_ptr<DeviceControlInterface>> deviceList = pcon->getDeviceList();
	uint16_t n = (uint16_t)deviceList.size();
	
	if (n == 0)
	{
		std::cout << "error:未找到设备,程序5s后退出" << std::endl;
		std::this_thread::sleep_for(std::chrono::seconds(5));
		return -1;	
	}
	std::cout << "find" << n << "个设备" << std::endl;

	std::string ip[Devices_num] = {""};
	ip[0] = "192.168.8.2";
	ip[1] = "192.168.9.2";
    ip[2] = "192.168.10.2";
    ip[3] = "192.168.13.2";
	
	//创建文件夹，每次采集运行创建一个，日期命名
	std::string gra = "\\gray";
	std::string dp = "\\3d_img";
	std::string cen = "\\c_img";
	std::string ori = "\\origin";
	GetLocalTime(&stCurTime); // 获取当前时间
	pdirectory = "md D:\\img\\" + std::to_string(stCurTime.wYear) + "_" + std::to_string(stCurTime.wMonth) + "_" + std::to_string(stCurTime.wDay) + "_" + std::to_string(stCurTime.wHour) + "_" + std::to_string(stCurTime.wMinute) + "\\";
	std::string file_path[Devices_num];
	std::string problem_path[Devices_num];
	std::string gray_path[Devices_num];
	std::string d_path[Devices_num];
	std::string c_path[Devices_num];
	std::string org_path[Devices_num];

	for (int i = 0; i < Devices_num; ++i) {
		file_path[i] = pdirectory + ip[i];
		gray_path[i] = file_path[i] + gra;
		c_path[i] = file_path[i] + cen;
		d_path[i] = file_path[i] + dp;
		org_path[i] = file_path[i] + ori;
		system(gray_path[i].c_str());
		system(c_path[i].c_str());
		system(d_path[i].c_str());
		system(org_path[i].c_str());
	}
	
	//多线程采集
	std::vector<std::thread> thrs{};

	//thrs.emplace_back(selfcolorMap);
	 
	thrs.emplace_back(plcData, std::ref(pdirectory));//顺序

	for (int i = 0; i < Devices_num ;++i)
	{ 
		thrs.emplace_back(main_acquisition, std::ref(file_path[i]), std::ref(ip[i]), i);//多台设备相应的主线程启动
	}	

	for (auto& t : thrs) {
		t.join();
	}
	DestroyFHDevices(pcon);
	return 0;
}