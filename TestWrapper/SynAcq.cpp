//外触发同步多线程采集程序
//程序入口main函数定义在这个文件
//

#include "stdafx.h"
#include "http.h"
#include "main_acquisition.h"
#include "define.h"
using namespace FHJD_3D;

SYSTEMTIME stCurTime;// 当前时间
std::string  head;

int main()
{
	int Number_Of_IpArray_Elements=0;//需要开始采集的设备的数量，之后如果连接的设备数量定下的话可以为固定值
	int i;
	//获取当前连接的设备数量
	FHDevicesInterface* pcon = CreateFHDevices();
	std::vector<std::shared_ptr<DeviceControlInterface>> deviceList = pcon->getDeviceList();
	uint16_t n = (uint16_t)deviceList.size();
	
	if (n == 0)
	{
		std::cout << "error:未找到设备" << std::endl;
		std::cout << "程序5s后退出" << std::endl;
		std::this_thread::sleep_for(std::chrono::seconds(5));
		return -1;
	
	}

	////存放用户输入的IP
	//std::string ip[10] = {"","","","","","","","","",""};
	//std::cout << "请输入" << n << "个设备的IP" << std::endl;
	//std::cout << "输入q结束" << std::endl;
	//for (i = 1; i < n + 1; i++)
	//{
	//	std::cout << "\n设备" << i << "的IP:" << std::endl;  
	//	std::cin >> ip[i];
	//	Number_Of_IpArray_Elements++;
	//	//用于用户自定义采集设备数量的情况
	//	if (ip[i] == "q") 
	//	{
	//		ip[i] = "";
	//		Number_Of_IpArray_Elements = Number_Of_IpArray_Elements-1;
	//		i = n + 1;
	//	}
	//	
	//}

	std::cout << "find" << n << "个设备" << std::endl;
	std::string ip[10] = { "","","","","","","","","","" };
	ip[0] = "192.168.8.2";
	ip[1] = "192.168.9.2";
	ip[2] = "192.168.10.2";
	ip[3] = "192.168.13.2";

	//
	//遍历获取非空元素个数
	for (i = 0; ip[i] != "";i++) 
	{
		Number_Of_IpArray_Elements++;
	}
	
	//创建文件夹，每次采集运行创建一个，日期命名
	GetLocalTime(&stCurTime); // 获取当前时间
	std::string path = "md D:\\img\\"+ std::to_string(stCurTime.wYear) + "_" + std::to_string(stCurTime.wMonth) + "_" + std::to_string(stCurTime.wDay) + "_" + std::to_string(stCurTime.wHour) + "_" + std::to_string(stCurTime.wMinute);
	head= "D:\\img\\"+ std::to_string(stCurTime.wYear) + "_" + std::to_string(stCurTime.wMonth) + "_" + std::to_string(stCurTime.wDay) + "_" + std::to_string(stCurTime.wHour) + "_" + std::to_string(stCurTime.wMinute)+"\\date_";
	system(path.c_str());


	//多线程采集
	std::vector<std::thread> thrs{};
	for (i = 0; i < Number_Of_IpArray_Elements; ++i)
	{
		thrs.emplace_back(main_acquisition, ip[i]);//多台设备相应的主程序
	}
	
	
	for (auto& t : thrs) {
		t.join();
	}

	DestroyFHDevices(pcon);
	return 0;
}