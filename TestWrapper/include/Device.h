#ifndef FLIR_SPINNAKER_DEVICE_H
#define FLIR_SPINNAKER_DEVICE_H

#include "SpinnakerDefs.h"
#include <vector>
#include "ProfileOutputInterface.h"
#include "ImageOutputInterface.h"
#include "HeightMapOutputInterface.h"
#include <future>
#include <functional>

/*
Description : Output Manager class
According different type of output,we create corresponding output
The advantage of one consumer is we can ensure the synchronization of profile data and measurement result.


Author : sanmingshen@whu.edu.cn
Date : 2019/09/16

*/

namespace FHJD_3D
{
	/*
		Device *device = deviceList->GetByIndex(0);
		int devtype = device->GetType();

		//file:\\C:\test\test.rhvd
		//UDP:\\192.169.1.100:12345
		//rtsp:\\192.168.1.100:554
		char *url = "file:\\C:\\test\\test.rhvd";
		device->SetUrl(url);


		StreamType type = (StreamType)(StreamType::OUTPUT_IMAGE | StreamType::OUTPUT_PROFILE);

		Streams *streams = device->CreateStream(type);
		if (streams->nb_streams == 0)
		{
		return -1;
		}

		ProfileOutputInterface *profileOutput = (ProfileOutputInterface*)streams->profileOutput;


		ImageOutputInterface *imageOutput = (ImageOutputInterface*)streams->imgOutput;

		//	profileOutput->AddTransform();
		//	profileOutput->AddOutput();

		while (true)
		{
			if (profileOutput)
			{
				ProfileInterface *profile;
				profile = profileOutput->GetLatestFrame();
				if (profile)
				{
					std::cout << "receive profile!!" << std::endl;
				}
			}

			if (imageOutput)
			{
				ImageInterface *image;
				image = imageOutput->GetLatestFrame();
				if (image)
				{
					printf("image width = %d\n",image->GetWidth());
					//std::cout << "receive Image!! width = " << image->GetWidth() << std::endl;
				}
			}

		}

		device->DestroyStream();
	*/

    // Data structures
	template <typename T>
	struct GenNode
	{
		std::string	name;
		std::string	type;
		std::string	unit;
		std::string	description;
		T		value;
		T		min_value;
		T		max_value;
		bool	valid;
	};

	struct GenericNode
	{
		std::string	name;
		std::string	unit;
		std::string	description;
		double	value_d;
		double	min_value_d;
		double	max_value_d;
		int64_t	value_i;
		int64_t	min_value_i;
		int64_t	max_value_i;
		std::vector<std::string> enum_names;
		std::string	value_s;
		bool	valid;
	};

	enum DeviceState 
	{
		UNKNOWN_STATE,
		DISCONNECTED_STATE,
		INIT_STATE,
		IDLE_STATE,
		RUNNING_STATE,
		FAULT_STATE,
		NO_STATE
	};

	enum DeviceType
	{
		DEV_FAKE,   ///fake_device.xml
		DEV_UVPP,   //uvpp_device.xml
		DEV_JOIN
	};

	enum SaveDataType
	{
		TYPE_NONE_DATA = 0x0,
		TYPE_VIDEO = 0x1,
		TYPE_PROFILE = 0x2,
		TYPE_OUT = 0x4
	};

	struct OutputStreams
	{
		int nb_streams;
		ProfileOutputInterface *profileOutput;
		ImageOutputInterface *imgOutput;
		HeightMapOutputInterface* heightMapOutput;
		OutputStreams()
		{
			nb_streams = 0;
			profileOutput = NULL;
			imgOutput = NULL;
			heightMapOutput = NULL;
		}
		~OutputStreams()
		{
			if (profileOutput)
			{
				delete profileOutput;
				profileOutput = NULL;
			}
			if (imgOutput)
			{
				delete imgOutput;
				imgOutput = NULL;
			}	
			if (heightMapOutput)
			{
				delete heightMapOutput;
				heightMapOutput = NULL;
			}
		}
	};

    class Device
	{
        public:
			Device(DeviceType type) { }
          virtual ~Device(){}

		  virtual DeviceType GetType() = 0;
		//  virtual void SetUrl(char *url) = 0;

		/// \brief 设备是否在线
		/// \return true-在线，false-离线
		  virtual bool IsOnline() const = 0;

		  /// \brief 设置设备是否在线
		  /// \param [in] online true-在线，false-离线
		  virtual void SetOnline(bool online) = 0;

		  virtual bool Open(const char* url,char& errCode) = 0;
		  virtual bool IsOpened() = 0;
		  virtual void Close() = 0;

          virtual bool CreateStream(int streamType) = 0;


		  //add two interface
		  virtual void* GetOutput(int type) = 0;



		  virtual void DestroyStream() = 0;

	      virtual bool read_memory(uint64_t address, uint32_t size, void *buffer) = 0;
		  virtual bool write_memory(uint64_t address, uint32_t size, void *buffer) = 0;
		  virtual bool read_register(uint64_t address, uint32_t *value) = 0;
		  virtual bool write_register(uint64_t address, uint32_t value) = 0;
          virtual const char *GetDeviceId() = 0;
		  virtual int  GetStreamNums() = 0;

		  virtual bool Reboot() { return true; };
		  //Device Parameter Setting
		  //Get Sensor Address
		  virtual bool GetSensorAddress(RetSensorAddress_t &address) = 0;
		  //Set Sensor Address , After Set Address, app need to sleep 30s,then reconnect
		  virtual bool SetSensorAddress(const RetSensorAddress_t &address, bool update = true) = 0;
		//  virtual bool GetSystemInfoV2();

		  virtual bool GetSystemStatus(ReqSystemStatus_t &sysStatus) = 0;
		  virtual bool ReadConfigFile(ConfigFileInfo_t &fileInfo) = 0;
		  virtual bool WriteConfigFile(char *data, int datalen) = 0;

		  virtual bool SetSensorType(char *p, int size) = 0;


		  /*
		      Description : Used to clear all calibration in sensor
			  return : 
		  */
		  virtual bool ClearCalibration() = 0;
		  virtual bool GetTimestamp(uint64_t &stamp) = 0;
		  virtual bool GetEncoderVal(int64_t encoderVal) = 0;
		  virtual bool ResetEncoder() = 0;



		  //Set Device Parameter
		  virtual bool SetSoftTrig() = 0;
		  virtual bool ResetSensor() = 0;
		  virtual bool Backup() = 0;
		  virtual bool RestoreBackup() = 0;
		  virtual bool RestoreFactorySetting() = 0;
		  virtual bool Upgrade() = 0;


		  virtual bool GetSampleType(uint8_t &type) = 0;
		  virtual bool SetSampleType(SampleType type) = 0;

		  virtual bool SetTriggerType(TriggerType type) = 0;

		  virtual bool GetCapFrequency(uint32_t &frequency) = 0;
		  /*
			  @brif : Set Camera Capture period
			  @param : [in] frequency : us
			  @note :
			  @Sample usage :
		  */
		  virtual bool SetCapFrequency(uint32_t frequency) = 0;

		  /// \brief 获取传送带运动速度
		  /// \param [out] conveySpeed 传送带运动速度
		  /// \return true-成功，false-失败
		  virtual bool GetConveyerBeltSpeed(double &conveySpeed) = 0;

		  /// \brief 设置传送带运动速度
		  /// \param [in] conveySpeed 传送带运动速度
		  /// \return true-成功，false-失败
		  virtual bool SetConveyerBeltSpeed(double conveySpeed) = 0;

		  virtual bool GetEncoderResol(double &encoderResol) = 0;
		  virtual bool SetEncoderResol(double encoderResol) = 0;
		  virtual bool GetEncoderFreq(uint32_t &encoderResol) = 0;
		  virtual bool SetEncoderFreq(uint32_t encoderResol) = 0;
		  /*
			  @brif : Set X direction calibration Range
			  @param : [in] mode : 0-full , rect(0,0,width,height)
			                       1-middle, rect(width/4,height/4,width/2,height/2)
								   2-small , rect(width/8,height/8,width/4,height/4)
								   3-user defined
			                       middle indicates 
			           [in] xLeft : left position of calibration range
			           [in] xright : right position of calibration range
			  @note :
			  @Sample usage :
		  */
		  virtual bool SetXRange(uint8_t mode, uint16_t xleft, uint16_t xright) = 0;
		  virtual bool GetXRange(uint8_t &mode, uint16_t &xleft, uint16_t &xright) = 0;
		  /*
			  @brif : Set Z direction calibration Range
			  @param : [in] mode : 0-full , rect(0,0,width,height)
								   1-middle, rect(width/4,height/4,width/2,height/2)
			                       2-small , rect(width/8,height/8,width/4,height/4)
			                       3-user defined
         			   [in] zLeft : left position of calibration range
			           [in] zright : right position of calibration range
			  @note :
			  @Sample usage :
		  */
		  virtual bool SetZRange(uint8_t mode, uint16_t zleft, uint16_t zright) = 0;
		  virtual bool GetZRange(uint8_t &mode, uint16_t &zleft, uint16_t &zright) = 0;

		  virtual bool GetTargetMode(uint8_t& mode) = 0;
		  virtual bool SetTargetMode(uint8_t mode) = 0;
		  virtual bool GetHDRMode(uint8_t &mode) = 0;
		  virtual bool SetHDRMode(uint8_t mode) = 0;

		  /*
		      @brif : Set Camera Exposure mode
			  @param :
			  @note :
			  @Sample usage : 
		  */
		  virtual bool SetExposureMode(uint8_t exposureMode) = 0;
		  virtual bool GetExposureMode(uint8_t &exposureMode) = 0;

		  /*
			  @brif : Set Camera Exposure Time
			  @param : [in] exposureTime : us
			  @note :
			  @Sample usage :
		  */
		  virtual bool SetExposureTime(uint32_t exposureTime) = 0;
		  virtual bool SetExposureTimes(uint8_t exposureTimes) = 0;


		  /*
		       获取设备序列号
			   设置设备序列号
		  */
		  virtual bool GetDeviceInfo(uint64_t &serialNo,char *scannerType) = 0;
		  virtual bool SetSeriealNo(uint64_t serialNo) = 0;

		  //获取未连接设备的序列号和设备型号
		  virtual bool GetUnconnectedDeviceInfo(std::string &serialNo, std::string &scannerType) = 0;
		  //设置未连接设备的序列号和设备型号
		  virtual void SetUnconnectedDeviceInfo(std::string serialNo, std::string scannerType) = 0;

		  /*
			  @brif : Get Camera Exposure Time From Device
			  @param : [out] exposureTime : us
			  @note :
			  @Sample usage :
		  */
		  virtual bool GetExposureTime(uint32_t &exposureTime) = 0;
		  virtual bool SetLaserPower(uint8_t laserPower) = 0;
		  virtual bool GetLaserPower(uint8_t &laserPower) = 0;
		  virtual bool SetPeakSensitivity(uint8_t sensitivity) = 0;
		  virtual bool GetPeakSensitivity(uint8_t &sensitivity) = 0;
		  virtual bool GetThreshSelect(uint8_t &type) { return true; };
		  virtual bool SetInvalInterpolPts(uint16_t invalpts) = 0;
		  virtual bool GetInvalInterpolPts(uint16_t &invalpts) = 0;
		  virtual bool SetPeakMode(uint8_t peakMode) = 0;
		  virtual bool GetPeakMode(uint8_t &peakMode) = 0;
		  virtual bool GetExposureTimes(uint8_t &exposureTimes) { return true; };
		  virtual bool GetInstallTheta(double &theta) = 0;
		  virtual bool SetInstallTheta(double theta) = 0;
		  virtual bool GetInstallZCoeff(double &zCoeff) = 0;
		  virtual bool SetInstallZCoeff(double zCoeff) = 0;
		  virtual bool SetXCalibraParam(double *data, int datalen) = 0;
		  virtual bool GetXCalibraParam(double *data, int &datalen) = 0;
		  virtual bool SetZCalibraParam(double *data, int datalen) = 0;
		  virtual bool GetZCalibraParam(double *data, int &datalen) = 0;
		  virtual bool SetCenterCalibraParam(uint16_t centerX, uint16_t centerZ) = 0;
		  virtual bool GetCenterCalibraParam(uint16_t &centerX, uint16_t &centerZ) = 0;
		  virtual bool SetTimeSync(char *timeStr) = 0;	
		  virtual bool SetDarkCorrection(bool darkMode) = 0;                           //设置暗场校正
		  virtual bool SetThreshSelect(int threshSelect) = 0;						   //设置激光中心线提取方式
		  virtual bool SetFilterParam(int type, int size)=0;
		  virtual bool TriggerRecommend() { return true; };
		  virtual std::string GetIpAddress() { return ""; }                            //获取设备IP地址
		  virtual void SetDeviceVector(std::vector<Device *> *device_vector){};
		  virtual void Start() {};
		  virtual void Stop() {};
		  virtual bool GetCapInterval(uint16_t &interval, uint8_t &enable) { return true; };
		  virtual bool SetSampleDistance(double sampledistance) { return true; };
		  virtual bool GetSampleDistance(double &sampledistance) { return true; };

		  virtual bool SetMask(unsigned char *data, size_t size, const char* path) { return true; };
		  virtual bool SetCallback(std::function<void(StateData_t)>) { return true; };
		  virtual bool SetReconnectfailedFunc(std::function<void(std::string)>) { return true; };
		  virtual bool GetTemperature(float &temperature) /*{ return true; }*/=0;//获取设备温度
		  virtual bool GetConnectedStatus() const = 0;//获取设备连接状态
		  virtual bool SyncCurrentTimeToArm()  = 0;//时间同步
		  virtual bool GetActualFrequency(uint32_t &freq) = 0;//获取实际的采样频率
		  virtual bool GetXZProportionality(uint32_t &xScale, uint32_t &zScale, int32_t &xOffset, int32_t &zoffset) = 0;//获取xz的比例系数
		  virtual bool SetXZProportionality(uint32_t xScale, uint32_t zScale, int32_t xOffset, int32_t zoffset) = 0;//获取xz的比例系数

		  /// \brief 设置坐标转换参数
		  /// \param [in] theta 旋转角度
		  /// \param [in] dx	X平移
		  /// \param [in] dz	Z平移
		  /// \return true-成功，false-失败
		  virtual bool SetCoordTransformParam(float theta, float dx, float dz) = 0;

		  /// \brief 获取坐标转换参数
		  /// \param [out] theta 旋转角度
		  /// \param [out] dx	X平移
		  /// \param [out] dz	Z平移
		  /// \return true-成功，false-失败
		  virtual bool GetCoordTransformParam(float & theta, float & dx, float & dz) = 0;

		public:
		  virtual void StartSaveData(const std::string&, int/*, std::promise<size_t>**/)=0;
		  virtual void StopSaveData()=0;

		  virtual void StartRenderHeightMap()=0;//开始显示二维亮度图
		  virtual void StopRenderHeightMap() = 0;//结束显示二维亮度图
		  virtual bool Reset() = 0;//清空上位机数据缓冲，并通知下位机复位帧计数值
		 // virtual bool GetCurrentVersion(std::string& versionnumber, std::string& builddate) = 0;//获取当前SDK版本号和创建时间
		  
    };
}


#endif