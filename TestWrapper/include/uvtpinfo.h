#ifndef _3D_LASER_UVTPINFO_H
#define _3D_LASER_UVTPINFO_H

#include "BaseDefine.h"

#include <vector>

/*
	Company : www.gaosuxiangji.com

	Mind the World,unremitting self-improvement!!!

	Description : concrete command info of Universal Vision Transport Protocol

	Author : shensm@gaosuxiangji.com/sanmingshen@whu.edu.cn
	Date : 2019/10/17
	TODO :

	Modified Info :
*/

#pragma warning(disable:4200)


namespace FHJD_3D
{

#pragma pack(1)
	/*
		header
	*/
	enum AuthorizationStatus {
		AUTHNORMAL = 0, //授权正常
	    AUTHTIMEOUT = 1,  //授权超期
		AUTHEXCEPTION = 2//当前时间小于arm记录的上次连接时间
	};
	enum DeviceConnectedStatus 
	{
		 DISCONNECT = 0,       // 0 - 离线状态；
		 ONLINE = 1            // 1- 在线状态；
	};
	struct CommandHeader_t
	{
		uint32_t dataLen;
		uint16_t id;
	};

	struct CommonRetInfo_t : CommandHeader_t
	{
		int32_t    status;
		CommonRetInfo_t()
		{
			dataLen = sizeof(*this);
		}
	};


	//Discover Command , source port 2016 ,destinatio port 3220
	//Control Command
	//1. Get Protocol version
	struct ReqProtocolVer_t : CommandHeader_t
	{
		ReqProtocolVer_t()
		{
			id = 0x4511;
			dataLen = sizeof(*this);
		}
	};

	//1. Protocol Version Info
	struct RetProtocolVer_t : CommonRetInfo_t
	{
		uint8_t  majorVersion;  //major version number
		uint8_t  minorVersion;  //minor version number
	};


	struct ReqSystemStatus_t : CommandHeader_t
	{
		ReqSystemStatus_t()
		{
			id = 0x4525;
			dataLen = sizeof(*this);
		}
	};

	struct RetSystemStatus_t : CommonRetInfo_t
	{
		uint32_t   count;
		int32_t    sensorState;
		int32_t    loginState;
		int32_t    alignmentReference;
		int32_t    alignmentState;
		int32_t    recordingEnable;
		int32_t    playbackSource;
		int32_t    uptimeSec;
		int32_t    uptimeMicrosec;
		int32_t    playbackPos;
		int32_t    playbackCount;
		int32_t    autoStartEnable;
	};


	//////////////////////////////////////////////////////////////////////////////
	struct ReqSensorAddress_t : CommandHeader_t
	{
		ReqSensorAddress_t()
		{
			id = 0x3012;
			dataLen = sizeof(*this);
		}
	};


	struct RetSensorAddress_t : CommonRetInfo_t
	{
		uint8_t dhcpEnabled;
		uint8_t address[4];
		uint8_t subnetMask[4];
		uint8_t gateway[4];
	};


	struct SetSensorAddress_t : CommandHeader_t
	{
		uint8_t dhcpEnabled;
		uint8_t address[4];
		uint8_t subnetMask[4];
		uint8_t gateway[4];
		SetSensorAddress_t()
		{
			id = 0x3013;
			dhcpEnabled = 0;//0-disable dhcp , 1-enable dhcp
			dataLen = sizeof(*this);
		}
	};
	//////////////////////////////////////////////////////////////////////////////////////////////////

	struct ResetFactory_t : CommandHeader_t
	{
		uint8_t resetIp;
		ResetFactory_t()
		{
			id = 0x4301;
			resetIp = 0;
			dataLen = sizeof(*this);
		}
	};



	//read config file
	struct ReqConfigFile_t : CommandHeader_t
	{
		char name[64];
		ReqConfigFile_t()
		{
			id = 0x1007;
			strcpy(name, "./config/config.xml");
			dataLen = sizeof(*this);
		}
	};

	struct ConfigFileInfo_t : CommonRetInfo_t
	{
		uint32_t length_file;
		char data[1024];
	};

	//write config file
	struct FileInfo_t : CommandHeader_t
	{
		char name[64];
		uint32_t fileLength;
		char data[0];
		FileInfo_t()
		{
			id = 0x1006;
			strcpy(name, "/config/config.xml");
			dataLen = sizeof(*this);
		}
	};

	//清除校准
	struct ReqCalibration_t : CommandHeader_t
	{
		ReqCalibration_t()
		{
			id = 0x4102;
			dataLen = sizeof(*this);
		}
	};

	//获取时间戳
	struct ReqTimestamp_t : CommandHeader_t
	{
		ReqTimestamp_t()
		{
			id = 0x100A;
			dataLen = sizeof(*this);
		}
	};


	struct RetTimeStamp_t : CommonRetInfo_t
	{
		uint64_t   timestamp;
	};

	//获取编码器
	struct ReqEncoderVal_t : CommandHeader_t
	{
		ReqEncoderVal_t()
		{
			id = 0x101C;
			dataLen = sizeof(*this);
		}
	};

	struct RetEncoderVal_t : CommonRetInfo_t
	{
		int64_t   encoderValue;
	};

	//复位编码器
	struct ResetEncoder_t : CommandHeader_t
	{
		ResetEncoder_t()
		{
			id = 0x101E;
			dataLen = sizeof(*this);
		}
	};


	struct ReqBackup_t : CommandHeader_t
	{
		ReqBackup_t()
		{
			id = 0x1013;
			dataLen = sizeof(*this);
		}
	};


	struct BackupInfo_t : CommonRetInfo_t
	{
		uint32_t   length;
		char       data[0];
	};

	//获取自动启动启用命令用于返回上电后系统是否自动启动
	struct ReqAutoStart_t : CommandHeader_t               //设置输出数据内容命令
	{
		ReqAutoStart_t()
		{
			id = 0x452C;
			dataLen = sizeof(*this);
		}
	};


	struct RetAutoStart_t : CommonRetInfo_t
	{
		uint8_t    enable;
	};



	////////////////////////////////////trigger  begin
	enum SampleType
	{
		TrigByTime = 0,
		TrigByDist = 1,
		TrigByExternal = 2
	};

	enum TriggerType
	{
		TrigIn = 0,
		TrigIntelligent = 1,
		TrigOut = 2

	};

	/**************************************************************************************************/
		//get trigger type from device
	struct ReqSampleType_t : CommandHeader_t      //获取采样类型
	{
		ReqSampleType_t()
		{
			id = 0x6001;
			dataLen = sizeof(*this);
		}
	};

	//trigger type
	struct RetSampleType_t : CommonRetInfo_t
	{
		uint8_t    triggerType; // triggertype : 0 - by time, 1 - by distance , 2 - by external trigger
	};

	//set trigger type to device
	struct SetSampleType_t : CommandHeader_t		//设置采样类型
	{
		uint8_t    triggerType; //
		SetSampleType_t()
		{
			id = 0X6002;
			triggerType = TrigByTime;
			dataLen = sizeof(*this);
		}
	};
	/**************************************************************************************************/


	struct ReqSampleDistance_t : CommandHeader_t      //获取采样类型
	{
		ReqSampleDistance_t()
		{
			id = 0x6068;
			dataLen = sizeof(*this);
		}
	};

	struct RetSampleDistance_t : CommonRetInfo_t
	{
		double sampleDistance;
	};

	//set trigger type to device
	struct SetSampleDistance_t : CommandHeader_t		//设置采样类型
	{
		double sampleDistance; //
		SetSampleDistance_t()
		{
			id = 0X6069;
			sampleDistance = 0.0;
			dataLen = sizeof(*this);
		}
	};


	//////////////////////////frequence begin
	struct ReqFrequency_t : CommandHeader_t                //获取采样频率命令
	{
		ReqFrequency_t()
		{
			id = 0x6003;
			dataLen = sizeof(*this);
		}
	};


	struct RetFrequencyInfo_t : CommonRetInfo_t               //回复获取采样频率命令
	{
		uint32_t triggerfrequency;            //采样频率
	};


	struct SetFrequency_t : CommandHeader_t               //设置采样频率命令
	{
		uint32_t triggerfrequency;         //采样频率
		SetFrequency_t()
		{
			id = 0x6004;
			triggerfrequency = 2000;
			dataLen = sizeof(*this);
		}
	};
	/////////////////////////frequence end



////////////////////////////////////////////////////////////////////////////////////////////////conveyer belt  start

	struct ReqConveyerBelt_t : CommandHeader_t                //获取采样频率命令
	{
		ReqConveyerBelt_t()
		{
			id = 0x6005;
			dataLen = sizeof(*this);
		}
	};


	struct RetConveyerBelt_t : CommonRetInfo_t               //回复获取采样频率命令
	{
		double conveyorSpeed;            //conveyor speed ,mm/s
	};


	struct SetConveyerBelt_t : CommandHeader_t               //设置采样频率命令
	{
		double conveyorSpeed;         //采样频率
		SetConveyerBelt_t()
		{
			id = 0x6006;
			dataLen = sizeof(*this);
		}
	};

	////////////////////////////conveyer belt end




/************************************************ENCODER BEGIN*****************************************************/
	struct ReqEncoderResol_t : CommandHeader_t                //获取采样频率命令
	{
		ReqEncoderResol_t()
		{
			id = 0x6007;
			dataLen = sizeof(*this);
		}
	};


	struct RetEncoderResol_t : CommonRetInfo_t               //回复获取采样频率命令
	{
		double encoderResol;            //conveyor speed ,mm/pulse
	};


	struct SetEncoderResol_t : CommandHeader_t               //设置采样频率命令
	{
		double encoderResol;         //采样频率
		SetEncoderResol_t()
		{
			id = 0x6008;
			dataLen = sizeof(*this);
		}
	};

	///////////////////////////////////////////////////////////////////////////////////////////////////////////////
	struct ReqEncoderFreq_t : CommandHeader_t                //获取采样频率命令
	{
		ReqEncoderFreq_t()
		{
			id = 0x6009;
			dataLen = sizeof(*this);
		}
	};


	struct RetEncoderFreq_t : CommonRetInfo_t               //回复获取采样频率命令
	{
		uint32_t encoderFreq;            //conveyor speed ,mm/pulse
	};

	struct SetEncoderFreq_t : CommandHeader_t               //设置采样频率命令
	{
		uint32_t encoderFreq;         //采样频率
		SetEncoderFreq_t()
		{
			id = 0x6010;
			dataLen = sizeof(*this);
		}
	};
	/*************************************************ENCODER END*********************************************************/




	/************************************************X RANGE BEGIN*****************************************************/
	struct ReqXRange_t : CommandHeader_t               //设置采样频率命令
	{
		ReqXRange_t()
		{
			id = 0x6011;
			dataLen = sizeof(*this);
		}
	};

	struct RetXRange_t : CommonRetInfo_t
	{
		uint8_t mode;         //0--full , 1-middle, 2-small ,3 - user defined
		uint16_t x1;         //left position of X
		uint16_t x2;         // right position of X
	};


	struct SetXRange_t : CommandHeader_t               //设置采样频率命令
	{
		uint8_t mode;         //0--full , 1-middle, 2-small ,3 - user defined
		uint16_t x1;         //left position of X
		uint16_t x2;         // right position of X
		SetXRange_t()
		{
			id = 0x6012;
			dataLen = sizeof(*this);
		}
	};


	struct SetSensorType_t : CommandHeader_t
	{
		char scannerType[32];
		SetSensorType_t()
		{
			id = 0x6080;
			dataLen = sizeof(*this);
		}
	};


	struct SetSerial_t : CommandHeader_t
	{
		uint64_t serialNo;
		SetSerial_t()
		{
			id = 0x6079;
			dataLen = sizeof(*this);
		}
	};

	struct ReqDeviceInfo_t : CommandHeader_t
	{
		ReqDeviceInfo_t()
		{
			id = 0x6078;
			dataLen = sizeof(*this);
		}
	};


	struct RetDeviceInfo_t : CommonRetInfo_t
	{
		uint64_t serialNo;
		char scannerType[32];
		char company[32];
		char macAddress[17];
		RetDeviceInfo_t()
		{
			id = 0x6078;
			dataLen = sizeof(*this);
		}
	};


	/************************************************X RANGE END********************************************************/




	/************************************************Z RANGE BEGIN*****************************************************/
	struct ReqZRange_t : CommandHeader_t               //设置采样频率命令
	{
		ReqZRange_t()
		{
			id = 0x6013;
			dataLen = sizeof(*this);
		}
	};

	struct RetZRange_t : CommonRetInfo_t
	{
		uint8_t mode;         //0--full , 1-middle, 2-small ,3 - user defined
		uint16_t z1;         //left position of X
		uint16_t z2;         // right position of X
	};


	struct SetZRange_t : CommandHeader_t               //设置采样频率命令
	{
		uint8_t mode;         //0--full , 1-middle, 2-small ,3 - user defined
		uint16_t z1;         //left position of X
		uint16_t z2;         // right position of X
		SetZRange_t()
		{
			id = 0x6014;
			dataLen = sizeof(*this);
		}
	};
	/************************************************Z RANGE END********************************************************/




	/************************************************TARGET MODE BEGIN********************************************************/
	struct ReqTargetMode_t : CommandHeader_t               //设置采样频率命令
	{
		ReqTargetMode_t()
		{
			id = 0x6015;
			dataLen = sizeof(*this);
		}
	};

	struct RetTargetMode_t : CommonRetInfo_t
	{
		uint8_t targetMode;         //0--auto  1- expert
	};


	struct SetTargetMode_t : CommandHeader_t               //
	{
		uint8_t targetMode;         //0--auto  1- expert
		SetTargetMode_t()
		{
			id = 0x6016;
			dataLen = sizeof(*this);
		}
	};
	/************************************************TARGET MODE END***********************************************************/



	/************************************************HDR MODE START***********************************************************/
	struct ReqHDRMode_t : CommandHeader_t               //设置采样频率命令
	{
		ReqHDRMode_t()
		{
			id = 0x6017;
			dataLen = sizeof(*this);
		}
	};

	struct RetHDRMode_t : CommonRetInfo_t
	{
		uint8_t HDRMode;         //0-高精度(对应gamma=1) 1 - 高动态范围1(对应gamma = 0.7) 2 - 高动态范围2(对应gamma = 0.5) 3 - 高动态范围2(对应gamma = 0.3)

	};


	struct SetHDRMode_t : CommandHeader_t               //
	{
		uint8_t HDRMode;         //0--auto  1- expert
		SetHDRMode_t()
		{
			id = 0x6018;
			dataLen = sizeof(*this);
		}
	};
	/************************************************HDR MODE END***********************************************************/




	/************************************************EXPOSURE TYPE START***********************************************************/
	struct ReqExposureMode_t : CommandHeader_t               //获取曝光类型
	{
		ReqExposureMode_t()
		{
			id = 0x6019;
			dataLen = sizeof(*this);
		}
	};

	struct RetExposureMode_t : CommonRetInfo_t
	{
		uint8_t ExposureMode;         //0--manual exposure ,  1-- recommend exposure , 2--Intelligent Exposure
	};


	struct SetExposureMode_t : CommandHeader_t               //
	{
		uint8_t ExposureMode;         //
		SetExposureMode_t()
		{
			id = 0x6020;
			dataLen = sizeof(*this);
		}
	};
	/************************************************EXPOSURE TYPE END***********************************************************/




	/************************************************EXPOSURE TIME START***********************************************************/
	struct ReqExposureTime_t : CommandHeader_t               //获取曝光时间
	{
		ReqExposureTime_t()
		{
			id = 0x6021;
			dataLen = sizeof(*this);
		}
	};

	struct RetExposureTime_t : CommonRetInfo_t
	{
		uint32_t exposureTime;         //0--manual exposure ,  1-- recommend exposure , 2--Intelligent Exposure
	};


	struct SetExposureTime_t : CommandHeader_t               //
	{
		uint32_t exposureTime;         //
		SetExposureTime_t()
		{
			id = 0x6022;
			dataLen = sizeof(*this);
		}
	};
	/************************************************EXPOSURE TIME END***********************************************************/







	/************************************************LASER POWER START***********************************************************/
	struct ReqLaserPower_t : CommandHeader_t               //设置采样频率命令
	{
		ReqLaserPower_t()
		{
			id = 0x6023;
			dataLen = sizeof(*this);
		}
	};

	struct RetLaserPower_t : CommonRetInfo_t
	{
		uint8_t laserPower;         //0--manual exposure ,  1-- recommend exposure , 2--Intelligent Exposure
	};


	struct SetLaserPower_t : CommandHeader_t               //
	{
		uint8_t laserPower;
		SetLaserPower_t()
		{
			id = 0x6024;
			dataLen = sizeof(*this);
		}
	};
	/************************************************LASER POWER END***********************************************************/





	/************************************************PEAK SENSITIVITY START***********************************************************/
	struct ReqPeakSensitivity_t : CommandHeader_t               //设置采样频率命令
	{
		ReqPeakSensitivity_t()
		{
			id = 0x6025;
			dataLen = sizeof(*this);
		}
	};

	struct RetPeakSensitivity_t : CommonRetInfo_t
	{
		uint8_t peakSensitivity;
	};


	struct SetPeakSensitivity_t : CommandHeader_t               //
	{
		uint8_t peakSensitivity;
		SetPeakSensitivity_t()
		{
			id = 0x6026;
			dataLen = sizeof(*this);
		}
	};
	/************************************************PEAK SENSITIVITY END***********************************************************/

	/*
		struct SystemInfo_t : CommandHeader_t
		{
			int32_t   status;
			uint16_t  localInfoSize;
			DeviceInfo localInfo;
			uint32_t     remoteCount;
			uint16_t     remoteInfoSize;

		};
		*/


		/************************************************INVALID INTERPOLATION POINTS START***********************************************************/
	struct ReqInvalidPoints_t : CommandHeader_t               //获取无效数据插值点数
	{
		ReqInvalidPoints_t()
		{
			id = 0x6054;
			dataLen = sizeof(*this);
		}
	};

	struct RetInvalidPoints_t : CommonRetInfo_t
	{
		uint16_t invalidInterPoints;    //无效数据插值点数
	};


	struct SetInvalidPoints_t : CommandHeader_t               //
	{
		uint16_t invalidInterPoints;
		SetInvalidPoints_t()
		{
			id = 0x6055;//////////////////////////????????????????????????????????????????????????????????????????????????????????????
			dataLen = sizeof(*this);
		}
	};
	/************************************************INVALID INTERPOLATION POINTS END***********************************************************/




	/************************************************GET PEAK MODE START***********************************************************/
	struct ReqPeakMode_t : CommandHeader_t               //获取峰值选择模式
	{
		ReqPeakMode_t()
		{
			id = 0x6027;
			dataLen = sizeof(*this);
		}
	};

	struct RetPeakMode_t : CommonRetInfo_t
	{
		uint8_t peakMode;
	};


	struct SetPeakMode_t : CommandHeader_t               //
	{
		uint8_t peakMode;
		SetPeakMode_t()
		{
			id = 0x6028;
			dataLen = sizeof(*this);
		}
	};
	/************************************************GET PEAK MODE END***********************************************************/





	/************************************************Get Install Theta START***********************************************************/
	struct ReqExposureNum_t : CommandHeader_t               //获取曝光次数
	{
		ReqExposureNum_t()
		{
			id = 0x6029;
			dataLen = sizeof(*this);
		}
	};

	struct RetExposureNum_t : CommonRetInfo_t
	{
		uint8_t exposureTimes;
	};


	struct SetExposureNum_t : CommandHeader_t               //
	{
		uint8_t exposureTimes;
		SetExposureNum_t()
		{
			id = 0x6030;
			dataLen = sizeof(*this);
		}
	};
	/************************************************Get Install Theta  END***********************************************************/

/************************************************Get Install Theta START***********************************************************/
	struct ReqInstallTheta_t : CommandHeader_t               //设置采样频率命令
	{
		ReqInstallTheta_t()
		{
			id = 0x6031;
			dataLen = sizeof(*this);
		}
	};

	struct RetInstallTheta_t : CommonRetInfo_t
	{
		double theta;    //0--manual exposure ,  1-- recommend exposure , 2--Intelligent Exposure
	};


	struct SetInstallTheta_t : CommandHeader_t               //
	{
		double theta;
		SetInstallTheta_t()
		{
			id = 0x6032;
			dataLen = sizeof(*this);
		}
	};
	/************************************************Get Install Theta  END***********************************************************/






	/************************************************Get Install Z Coefficient START***********************************************************/
	struct ReqInstallZCoeff_t : CommandHeader_t               //设置采样频率命令
	{
		ReqInstallZCoeff_t()
		{
			id = 0x6033;
			dataLen = sizeof(*this);
		}
	};

	struct RetInstallZCoeff_t : CommonRetInfo_t
	{
		double zCoeff;    //0--manual exposure ,  1-- recommend exposure , 2--Intelligent Exposure
	};


	struct SetInstallZCoeff_t : CommandHeader_t               //
	{
		double zCoeff;
		SetInstallZCoeff_t()
		{
			id = 0x6034;
			dataLen = sizeof(*this);
		}
	};
	/************************************************Get Install Z Coefficient  END***********************************************************/





	/************************************************Get Output Type Start***********************************************************/
	struct SetOutputType_t : CommandHeader_t               //设置输出数据内容命令
	{
		uint32_t outDataType;               //输出数据内容，为以下值组合：0x01——时间戳，0x02——图像，0x04——轮廓
		SetOutputType_t()
		{
			id = 0x6036;
			outDataType = 0x04;
			dataLen = sizeof(*this);
		}
	};
	/************************************************Get Output Type End***********************************************************/


	/************************************************Get Output Type Start***********************************************************/
	struct SetIndicatorType_t : CommandHeader_t               //设置输出数据内容命令
	{
		uint32_t outIndicatorTypes;               //输出数据内容，为以下值组合：0x01——时间戳，0x02——图像，0x04——轮廓
		SetIndicatorType_t()
		{
			id = 0x6038;
			outIndicatorTypes = 0x04;
			dataLen = sizeof(*this);
		}
	};
	/************************************************Get Output Type End***********************************************************/




/************************************************Get X Calibration Parameter Start***********************************************************/
	struct ReqXCaliParam_t : CommandHeader_t               //设置输出数据内容命令
	{
		ReqXCaliParam_t()
		{
			dataLen = 10;
			id = 0x6039;
		}
	};


	struct RetXCaliParam_t : CommonRetInfo_t
	{
		uint32_t   count;
		double     calibCoeff[0];
	};


	struct SetXCaliParam_t : CommandHeader_t               //
	{
		uint32_t   count;
		double     calibCoeff[0];
		SetXCaliParam_t()
		{
			id = 0x6040;
			dataLen = sizeof(*this);
		}
	};
	/************************************************Get X Calibration Parameter End***********************************************************/





	/************************************************Get Z Calibration Parameter Start***********************************************************/
	struct ReqZCaliParam_t : CommandHeader_t               //设置输出数据内容命令
	{
		ReqZCaliParam_t()
		{
			dataLen = 10;
			id = 0x6041;
		}
	};


	struct RetZCaliParam_t : CommonRetInfo_t
	{
		uint32_t   count;
		double     calibCoeff[0];
	};


	struct SetZCaliParam_t : CommandHeader_t               //
	{
		uint32_t   count;
		double     calibCoeff[0];
		SetZCaliParam_t()
		{
			id = 0x6042;
			dataLen = sizeof(*this);
		}
	};
	/************************************************Get Z Calibration Parameter End***********************************************************/






	/************************************************Get Image Shielding Parameter Start***********************************************************/
	struct ReqImgShieldParam_t : CommandHeader_t               //设置输出数据内容命令
	{
		ReqImgShieldParam_t()
		{
			dataLen = 10;
			id = 0x6043;
		}
	};

	struct Mask_t
	{
		uint8_t count;
		Point16s pts[0];
	};


	struct RetImgShieldParam_t : CommonRetInfo_t
	{
		uint32_t   count;
		//Mask_t     mask[0];
	};


	struct SetImgShieldParam_t : CommandHeader_t               //
	{
		uint32_t   count;
		//Mask_t     mask[0];
		SetImgShieldParam_t()
		{
			id = 0x6044;
			dataLen = sizeof(*this);
		}
	};
	/************************************************Get Image Shielding Parameter End***********************************************************/





	/************************************************Set Time Sync Start***********************************************************/
	struct SetTimeSync_t : CommandHeader_t               //设置输出数据内容命令
	{
		char timeStr[26]; // format : YYYY-MM-DD-hh:mm:ss:ms  
		SetTimeSync_t()
		{
			id = 0x6045;
			dataLen = sizeof(*this);
		}
	};
	/************************************************Set Time Sync End***********************************************************/





	/************************************************Set Black Field  Start***********************************************************/
	struct SetEnableBlack_t : CommandHeader_t               //触发暗场
	{
		SetEnableBlack_t()
		{
			dataLen = 10;
			id = 0x6046;
			dataLen = sizeof(*this);
		}
	};

	struct SetClearBlack_t : CommandHeader_t               //清除暗场
	{
		SetClearBlack_t()
		{
			dataLen = 10;
			id = 0x6047;
			dataLen = sizeof(*this);
		}
	};
	/************************************************Set Black Field End***********************************************************/






	/************************************************Upgrade FPGA fireware Start***********************************************************/
	struct ReqFirewareStatus_t : CommandHeader_t               //设置输出数据内容命令
	{
		ReqFirewareStatus_t()
		{
			id = 0x6049;
			dataLen = sizeof(*this);
		}
	};


	struct RetFirewareStatus_t : CommonRetInfo_t
	{
		int64_t    state;
		int64_t    progress;
	};


	struct SetUpgradeFireware_t : CommandHeader_t
	{
		int64_t    length;
		uint8_t    data[0];
		SetUpgradeFireware_t()
		{
			id = 0x6048;
			dataLen = sizeof(*this);
		}
	};
	/************************************************Upgrade FPGA fireware End***********************************************************/





	/************************************************Upgrade ARM fireware Start***********************************************************/
	struct ReqArmStatus_t : CommandHeader_t               //设置输出数据内容命令
	{
		ReqArmStatus_t()
		{
			id = 0x6052;
			dataLen = sizeof(*this);
		}
	};


	struct RetArmStatus_t : CommonRetInfo_t
	{
		int64_t    state;
		int64_t    progress;
	};


	struct SetUpgradeArm_t : CommandHeader_t
	{
		int64_t    length;
		uint8_t    data[0];
		SetUpgradeArm_t()
		{
			id = 0x6051;
			dataLen = sizeof(*this);
		}
	};
	/************************************************Upgrade ARM fireware End***********************************************************/




	/***********************************************Set Capture Frame Interval Start*******************************************************/
	struct ReqCaptureInterval_t : CommandHeader_t               //设置输出数据内容命令
	{
		ReqCaptureInterval_t()
		{
			id = 0x6056;
			dataLen = sizeof(*this);
		}
	};


	struct RetCaptureInterval_t : CommonRetInfo_t
	{

		uint8_t    enable;
		uint16_t   extractInterval;
	};
	struct SetCaptureInterval_t : CommandHeader_t
	{
		uint8_t  enable;//set capture interval enable, 0-disable,1-enable
		uint16_t extractInterval;
		SetCaptureInterval_t()
		{
			id = 0x6057;
			dataLen = sizeof(*this);
		}
	};


	/***********************************************Set Capture Frame Interval End*******************************************************/



	//启动传感器
	struct StartSensor_t : CommandHeader_t
	{
		StartSensor_t()
		{
			id = 0x100D;
			dataLen = sizeof(*this);
		}
	};

	//停止传感器
	struct StopSensor_t : CommandHeader_t
	{
		StopSensor_t()
		{
			id = 0x1001;
			dataLen = sizeof(*this);
		}
	};


	/***********************************************ThreshSelect*******************************************************/
	struct ReqThreshSelect_t : CommandHeader_t               //获取激光中心线提取方式
	{
		ReqThreshSelect_t()
		{
			id = 0x6058;
			dataLen = sizeof(*this);
		}
	};

	struct RetThreshSelect_t : CommonRetInfo_t               //获取激光中心线提取方式
	{
		uint8_t Type;
	};

	struct SetThreshSelect_t : CommandHeader_t				//设置激光中心线提取方式
	{
		uint8_t  Type;
		SetThreshSelect_t()
		{
			id = 0x6059;
			dataLen = sizeof(*this);
		}
	};

	/***********************************************ThreshSelect*******************************************************/
	struct ReqFilterParam_t : CommandHeader_t               //获取滤波核大小
	{
		ReqFilterParam_t()
		{
			id = 0x6060;
			dataLen = sizeof(*this);
		}
	};
	struct RetFilterParam_t : CommonRetInfo_t               //获取滤波核大小
	{
		uint8_t filterType;
		uint8_t filterLength;
		uint16_t paramCount;
	};

	struct SetFilterParam_t : CommandHeader_t				//设置滤波核大小
	{
		uint8_t  filtertype;
		uint8_t  size;
		SetFilterParam_t()
		{
			id = 0x6061;
			dataLen = sizeof(*this);
		}
	};


	struct TriggerRecommend_t : CommandHeader_t		//触发推荐曝光
	{
		TriggerRecommend_t()
		{
			id = 0X6062;
			dataLen = sizeof(*this);
		}
	};

	struct SetTriggerType_t : CommandHeader_t		//触发推荐曝光
	{
		uint8_t  triggerType;

		SetTriggerType_t()
		{
			id = 0X6065;
			triggerType = TrigIn;
			dataLen = sizeof(*this);
		}
	};


	struct ReqTemperature_t : CommandHeader_t               //获取滤波核大小
	{
		ReqTemperature_t()
		{
			id = 0x6075;
			dataLen = sizeof(*this);
		}
	};
	struct RetTemperature_t : CommonRetInfo_t               //获取滤波核大小
	{
		int16_t temperature;
	};

	// 获取中心坐标命令
	struct ReqCenterCaliParam_t : CommandHeader_t
	{
		ReqCenterCaliParam_t()
		{
			id = 0x6076;
			dataLen = sizeof(*this);
		}
	};

	// 获取中心坐标回复
	struct RetCenterCaliParam_t : CommonRetInfo_t
	{
		uint16_t centerX;
		uint16_t centerZ;
	};

	// 设置中心坐标命令
	struct SetCenterCaliParam_t : CommandHeader_t
	{
		uint16_t centerX;
		uint16_t centerZ;
		SetCenterCaliParam_t()
		{
			id = 0x6077;
			dataLen = sizeof(*this);
			centerX = 0;
			centerZ = 0;
		}
	};
	struct ReqHeartBeat_t : CommandHeader_t                //设置心跳
	{
		int64_t serialNo;
		ReqHeartBeat_t()
		{
			id = 0x6081;
			dataLen = sizeof(*this);
		}
	};


	struct RetHeartBeat_t : CommonRetInfo_t
	{
		char ipAddress[4];
		uint64_t serialNo;
		char scannerType[32];
	};


	struct ReqStatus_t : CommandHeader_t                    //获取设备状态
	{
		int64_t serialNo;
		ReqStatus_t()
		{
			id = 0x6082;
			dataLen = sizeof(*this);
		}
	};

	struct ReqReset_t : CommandHeader_t                    //通知下位机复位帧计数
	{
		ReqReset_t()
		{
			id = 0x6083;
			dataLen = sizeof(*this);
		}
	};
	struct ReqAuthorizationStatus_t : CommandHeader_t                    //获取授权状态
	{
		ReqAuthorizationStatus_t()
		{
			id = 0x6084;
			dataLen = sizeof(*this);
		}
	};
	struct RetAuthorizationStatus_t : CommonRetInfo_t
	{
		char authStatus;     //0 授权正常；1 授权超期；2 当前时间小于arm记录的上次连接时间
		char lastConnectTime[19]; //ARM记录的上次连接时间，例如“2021-06-17  11:24:00”
	};

	struct ReqFPGAStatus_t :CommandHeader_t                               //获取FPGA工作状态
	{
		ReqFPGAStatus_t()
		{
			id = 0x6085;
			dataLen = sizeof(*this);
		}
	};

	struct RetFPGAStatus_t :CommonRetInfo_t 
	{
		uint32_t fpgaStatus;  //FPGA工作状态，按位表示    Bit0-CMOS有无数据 0-有 1-无   Bit1-DDR有无数据 0-有 1-无   Bit2-有无外同步  0-有 1-无                                                
	};

	struct ReqGetActualFrequency_t :CommandHeader_t         //获取真实采样频率
	{
		ReqGetActualFrequency_t()
		{
			id = 0X6086;
			dataLen = sizeof(*this);
		}
	};

	struct RetGetActualFrequency_t :CommonRetInfo_t
	{
		uint32_t triggerFrequency;
	};

	struct ReqGetXZProportionality_t :CommandHeader_t         //获取XZ比例系数
	{
		ReqGetXZProportionality_t()
		{
			id = 0X6087;
			dataLen = sizeof(*this);
		}
	};

	struct RetGetXZProportionality_t :CommonRetInfo_t
	{
		uint32_t xScale;
		uint32_t zScale;
		int32_t xOffset;
		int32_t zoffset;
	};
	struct SetXZProportionality_t :CommandHeader_t         //设置XZ比例系数
	{
		uint32_t xScale;
		uint32_t zScale;
		int32_t xOffset;
		int32_t zoffset;
		SetXZProportionality_t()
		{
			id = 0X6088;
			dataLen = sizeof(*this);
		}
	};

	/// \brief 获取坐标转换参数请求
	struct ReqGetCoordTransformParam_t :CommandHeader_t
	{
		ReqGetCoordTransformParam_t()
		{
			id = 0X6104;
			dataLen = sizeof(*this);
		}
	};

	/// \brief 获取坐标转换参数应答
	struct RetGetCoordTransformParam_t :CommonRetInfo_t
	{
		float params[3];
	};

	/// \brief 设置坐标转换参数
	struct SetCoordTransformParam_t : CommandHeader_t
	{
		float params[3];
		SetCoordTransformParam_t()
		{
			id = 0x6105;
			dataLen = sizeof(*this);
		}
	};

	struct RetStatus_t : CommonRetInfo_t                    //返回设备状态
	{
		char connectStatus; //0---離綫,1---在綫
		RetStatus_t()
		{
			dataLen = sizeof(*this);
		}
	};


#define MAX_FILE_PAYLOAD 1024*254
	struct SerializeFileHead
	{
		uint32_t mark;//标识 'F'<<24 | 'H'<<16 |'J'<<8 |'D'
		uint64_t size;//当前包大小
		uint64_t total_size;//文件总大小
		uint64_t remain_size;//剩余文件大小
		char file_name[16];//文件名
		uint16_t pkgCnt;//当前包号，从0开始
		uint16_t pkgNum;//总包数
		uint8_t status;//0:success 1:error
		uint8_t reserved[15];
	};

	struct SerializeFile
	{
		SerializeFileHead head;
		char payLoad[MAX_FILE_PAYLOAD - sizeof(SerializeFileHead) - 8];
	};

	struct SetMask_t : CommandHeader_t
	{
		uint16_t count;
		SerializeFile serializeFile;
		SetMask_t()
		{
			id = 0X6074;
		}
	};

	///////////////////////////////////////////////////////////////////////////////////////////////////////////////////
	/*********************************************PORT=3196************************************************************/
	/**************************Used to receive image 、 Profile and Timestamp Data!!***********************************/

	enum DataType
	{
		STAMP_DATA = 1,
		IMAGE_DATA = 2,
		PROFILE_DATA = 5,
		RESAMPLE_PROFILE_DATA = 6,
		AVGLUNINANCE_DATA = 7
	};

#pragma pack(push)
#pragma pack(1)
	struct DataHeader
	{
		uint32_t dataLen;
		uint16_t control;// data type , 1--timestamp data , 2--image data , 5--profile data
	};

	struct StampInfo : DataHeader       //时间戳
	{
		uint64_t frameIndex;       //帧索引（从零开始计数）
		uint64_t timestamp;        //时间戳 (微秒)
		int64_t encoder;                   //当前编码器值（信号值）
		int64_t encoderAtZ;                //将编码器值锁定在 z/索引标记（信号值）
		uint64_t status;           //位字段包含多种帧信息：位 0：传感器数字输入状态，位 4：主机数字输入状态，
										   //位 8 - 9：帧间数字脉冲触发（若主机已连接，则为主机数字输入，否则为传感器数字输入。
										   //如果接收到的脉冲超过 3 个，会在每个帧之后清除值，并将值钳位在 3）
		uint32_t serialNumber;             //传感器序列号（在双传感器系统中，为主传感器的序列号）
		uint32_t reserved[2];              //保留
	};


	struct StampData_t : DataHeader
	{
		uint32_t count;
		uint16_t stampSize;
		uint8_t   source;
		uint8_t   reserved;
		StampInfo  stamps[0];
	};


	struct ImageData_t : DataHeader
	{
		uint16_t  attributesize;           //attribute size，byte（minimum size：20，current：20）
		uint32_t  height;            //图像高度，单位为像素
		uint32_t  width;             //图像宽度，单位为像素
		uint8_t   pixelSize;          //像素大小，单位为字节
		uint8_t   pixelFormat;        //像素格式：1 - 8位灰度，2 - 8位滤色器，3 - 8位每通道色彩（B、G、R、X）
		uint8_t   colorFilter;        //滤色器数组对齐：0 - 无，1 - 拜尔BG/GR，2 - 拜尔GB/RG，3 - 拜尔RG/GB，4 - 拜尔GR/BG
		uint8_t   source;             //源：0 - 上，1 - 下，2 - 左上，3 - 右上
		uint8_t   cameraIndex;        //相机索引
		uint8_t   exposureIndex;      //曝光索引
		uint32_t  exposure;          //曝光（纳秒）
		uint8_t   flippedX;           //指示影像数据是否必须水平翻转以匹配轮廓数据
		uint8_t   flippedY;           //指示影像数据是否必须垂直翻转以匹配轮廓数据
		//uint8_t   reserved[4];
		uint32_t	framid;
		uint8_t   data[0];            //dynamic alloc , according image width and height , alloc size = width * height
	};


	struct ProfileData_t : DataHeader
	{
		uint16_t    attributesize;            //属性的大小，单位为字节（最小：32，当前：32）
		uint32_t    count;             //轮廓数组数
		uint32_t    width;             //每个轮廓数组的点数
		uint32_t    xScale;            //X比例（纳米）
		uint32_t    zScale;            //Z比例（纳米）
		int32_t         xOffset;                //X偏移（微米）
		int32_t         zOffset;                //Z偏移（微米）
		uint8_t     source;             //源：0 - 上，1 - 下，2 - 左上，3 - 右上
		uint32_t    exposure;          //曝光（纳秒）
		uint8_t     cameraIndex;        //相机索引
		//uint64_t	profileIndex;		//中车同步编号
		uint64_t	frameId;				//帧编号
		//uint8_t		isExternal;			//是否外触发
		uint32_t     time_us_cnt;
		uint32_t     time_s_cnt;
		uint16_t     merg_trig_id;			//随外同步清零的帧id号
		uint8_t     reserved[8];			//保留
		Point16f    points[0];         //dynamic size, according profile count and profile width, alloc size = count * width
	};

	struct ResampleProfileData_t : DataHeader
	{
		uint16_t    attributesize;            //属性的大小，单位为字节（最小：32，当前：32）
		uint32_t    count;             //轮廓数组数
		uint32_t    width;             //每个轮廓数组的点数
		uint32_t    xScale;            //X比例（纳米）
		uint32_t    zScale;            //Z比例（纳米）
		int32_t     xOffset;                //X偏移（微米）
		int32_t     zOffset;                //Z偏移（微米）
		uint8_t     source;             //源：0 - 上，1 - 下，2 - 左上，3 - 右上
		uint32_t    exposure;          //曝光（纳秒）
		uint8_t     cameraIndex;        //相机索引
										//uint64_t	profileIndex;		//中车同步编号
		uint64_t	frameId;				//帧编号
											//uint8_t		isExternal;			//是否外触发
		uint32_t     time_us_cnt;
		uint32_t     time_s_cnt;
		uint16_t     merg_trig_id;			//随外同步清零的帧id号
		uint8_t      reserved[8];			//保留
		Point16si    points[0];         //dynamic size, according profile count and profile width, alloc size = count * width
	};

#pragma pack(pop)
	//平均亮度数据
	struct AvgLuminanceData_t : DataHeader
	{
		uint16_t    attributesize;            //属性的大小，单位为字节（最小：32，当前：32）
		uint32_t    count;             //轮廓数组数
		uint32_t    width;             //每个轮廓数组的点数
		uint32_t    xScale;            //X比例（纳米）
		//uint32_t    zScale;            //Z比例（纳米）
		int32_t         xOffset;                //X偏移（微米）
		//int         zOffset;                //Z偏移（微米）
		uint8_t     source;             //源：0 - 上，1 - 下，2 - 左上，3 - 右上
		uint32_t    exposure;          //曝光（纳秒）
		uint8_t     cameraIndex;        //相机索引
		//uint32_t	framid;				//帧编号
		uint8_t     reserved[2];        //保留
		uint8_t    points[0];         //dynamic size, according profile count and profile width, alloc size = count * width
	};

	struct Indicator
	{
		uint32_t id;
		uint32_t instance;//实例
		uint64_t value;//值
	};

	struct StateHeader : DataHeader
	{
		uint32_t    count; //指示器计数
		uint8_t		source;//源
		uint8_t     reserved[3];        //保留
	};

	struct StateData_t : StateHeader
	{
		std::vector<Indicator> indicators;
	};

	struct CameraWindowRect3D  //相机
	{
		uint16_t x;
		uint16_t y;
		uint16_t height;
		uint16_t width;
	};

	struct CameraInfo  //相机信息
	{
		uint32_t camera_model;                //待定，4字节
		uint32_t sensor_width;                 //传感器宽度，即图像最大宽度，4字节
		uint32_t sensor_hight;                 //传感器高度，即图像最大高度，4字节
		uint32_t fps;                         //图像帧率，4字节
		CameraWindowRect3D rect;               //相机窗口
	};

	struct smoothsNumInfo
	{
		//过滤器点数smoothPoint设置,x轴
		unsigned int SPCnt_MEANX = 1;       //1,2,4,...64    4字节
		unsigned int SPCnt_MEDIANX = 0;     //off(0),3,5,7,9  4字节

											//过滤器次数smoothFrame设置,时间轴
		unsigned int SFCnt_MEANY = 1;       //1,2,4,...256    4字节
		unsigned int SFCnt_MEDIANY = 0;     //off(0),3,5,7,9   4字节
	};

	struct AlgorithmInfo
	{
		smoothsNumInfo  smooth;         //轮廓设置参数
		bool isCorrectEnable;             //安装校准是否使能  1 字节
		float correctAngle;                //安装校准的角度   4 字节
		bool isZScaleEnable;            //Z方向校准是否使能  1字节
		float ZScaleFactor;               //Z方向校准因子     4 字节
	};


	struct FILE_HEADER   //文件头
	{
		uint32_t mark;                        //待定，4字节
		uint32_t version;                      //版本号，4字节
		CameraInfo camera_info;               //相机信息
		AlgorithmInfo algorithm_Info;           //算法信息
		__int64 create_time;                   //创建时间，8字节时间戳
		uint8_t sensor_count;                 //传感器数量
		uint16_t sensorids[8];                 //传感器编号
		uint32_t frame_count;                 //总帧数，4字节
		uint32_t frame_size;                   //一帧数据大小，4字节
		uint32_t frame_pitch;                  //一帧数据的偏移量，4字节
		uint32_t first_frame_offset;             //起始帧位置， 4字节
		uint8_t  reserved[925];                  //保留
	};

#pragma pack()
}


#endif