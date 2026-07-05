#ifndef FHJD_DEVICE_JOIN_H
#define FHJD_DEVICE_JOIN_H

#include "Device.h"
#include <vector>
#include "Thread.h"
#include <fstream>

namespace FHJD_3D
{
	class DeviceJoin : public Device
	{
	public:
		DeviceJoin();
		~DeviceJoin();

		virtual DeviceType GetType()
		{
			return DeviceType::DEV_JOIN;
		}

		/// \brief 设备是否在线
		/// \return true-在线，false-离线
		virtual bool IsOnline() const override { return true; }

		/// \brief 设置设备是否在线
		/// \param [in] online true-在线，false-离线
		virtual void SetOnline(bool online) override { }

		virtual bool Open(const char* url, char& errCode);
		virtual bool IsOpened()
		{
			return true;
		}
		virtual void Close();


		bool SetSensorType(char *p, int size)
		{
			return true;
		}

		bool CreateStream(int streamType) ;
		void* GetOutput(int type) ;

		virtual void DestroyStream();
		virtual bool read_memory(uint64_t address, uint32_t size, void *buffer) {
			return true;
		};
		virtual bool write_memory(uint64_t address, uint32_t size, void *buffer) {
			return true;
		};
		virtual bool read_register(uint64_t address, uint32_t *value) {
			return true;
		};
		virtual bool write_register(uint64_t address, uint32_t value) {
			return true;
		};
		virtual const char *GetDeviceId() {
			return NULL;
		};


		virtual int  GetStreamNums()
		{
			return 2;
		}



		//Get Sensor Address
		virtual bool GetSensorAddress(RetSensorAddress_t &address) { return true; }
		//Set Sensor Address , After Set Address, app need to sleep 30s,then reconnect
		virtual bool SetSensorAddress(const RetSensorAddress_t &address, bool update) { return true; }

		//  virtual bool GetSystemInfoV2();

		virtual bool GetSystemStatus(ReqSystemStatus_t &sysStatus) { return true; }
		virtual bool ReadConfigFile(ConfigFileInfo_t &fileInfo) { return true; }
		virtual bool WriteConfigFile(char *data, int datalen) { return true; }
		virtual bool SetZCalibraParam(double *data, int datalen) { return true; }
		virtual bool GetZCalibraParam(double *data, int &datalen) { return true; }
		virtual bool SetTimeSync(char *timeStr) { return true; }
		/*
		Description : Used to clear all calibration in sensor
		return :
		*/
		virtual bool ClearCalibration() { return true; }
		virtual bool GetTimestamp(uint64_t &stamp) { return true; }
		virtual bool GetEncoderVal(int64_t encoderVal) { return true; }
		virtual bool ResetEncoder() { return true; }
		//Set Device Parameter
		virtual bool ResetSensor() { return true; }
		virtual bool Backup() { return true; }
		virtual bool RestoreBackup() { return true; }

		virtual bool GetDeviceInfo(uint64_t &serialNo,char *scanner) { return true; }
		virtual bool SetSeriealNo(uint64_t serialNo) { return true; }

		//获取未连接设备的序列号和设备型号
		virtual bool GetUnconnectedDeviceInfo(std::string &serialNo, std::string &scannerType) { return true; };
		//设置未连接设备的序列号和设备型号
		virtual void SetUnconnectedDeviceInfo(std::string serialNo, std::string scannerType) { return; };

		//Set Device Parameter
		virtual bool SetSoftTrig() { return true; }
		virtual bool Reset() { return true; }
		virtual bool RestoreFactorySetting() { return true; }
		virtual bool Upgrade() { return true; }

		//Exposure
		virtual bool SetAutoExposure() { return true; }
		virtual bool SetExposureTime() { return true; }
		virtual bool GetExposureTime() { return true; }

		//laser parameter
		virtual bool SetLaserPower() { return true; }
		virtual bool GetLaserPower() { return true; }

		virtual bool SetPeakSensitivity() { return true; }
		virtual bool GetPeakSensitivity() { return true; }

		//output type
		virtual bool SetOutput() { return true; }
		virtual bool SetOutputType() { return true; }
		virtual bool GetOutputType() { return true; }

		virtual bool GetSampleType(uint8_t &type) { return true; }
		virtual bool SetSampleType(SampleType type) { return true; }
		virtual bool SetTriggerType(TriggerType type) { return true; }
		virtual bool GetCapFrequency(uint32_t &frequency) { return true; }
		virtual bool SetCapFrequency(uint32_t frequency) { return true; }
		virtual bool GetConveyerBeltSpeed(double &conveySpeed) { return true; }
		virtual bool SetConveyerBeltSpeed(double conveySpeed) { return true; }
		virtual bool GetEncoderResol(double &encoderResol) { return true; }
		virtual bool SetEncoderResol(double encoderResol) { return true; }
		virtual bool GetEncoderFreq(uint32_t &encoderResol) { return true; }
		virtual bool SetEncoderFreq(uint32_t encoderResol) { return true; }
		virtual bool SetXRange(uint8_t mode, uint16_t xleft, uint16_t xright) { return true; }
		virtual bool GetXRange(uint8_t &mode, uint16_t &xleft, uint16_t &xright) { return true; }
		virtual bool SetZRange(uint8_t mode, uint16_t zleft, uint16_t zright) { return true; }
		virtual bool GetZRange(uint8_t &mode, uint16_t &zleft, uint16_t &zright) { return true; }

		virtual bool GetTargetMode(uint8_t& mode) { return true; }
		virtual bool SetTargetMode(uint8_t mode) { return true; }
		virtual bool GetHDRMode(uint8_t &mode) { return true; }
		virtual bool SetHDRMode(uint8_t mode) { return true; }

		virtual bool SetExposureMode(uint8_t exposureMode) { return true; }
		virtual bool GetExposureMode(uint8_t &exposureMode) { return true; }
		virtual bool SetExposureTime(uint32_t exposureTime) { return true; }
		virtual bool GetExposureTime(uint32_t &exposureTime) { return true; }
		virtual bool SetLaserPower(uint8_t laserPower) { return true; }
		virtual bool GetLaserPower(uint8_t &laserPower) { return true; }
		virtual bool SetPeakSensitivity(uint8_t sensitivity) { return true; }
		virtual bool GetPeakSensitivity(uint8_t &sensitivity) { return true; }
		virtual bool SetInvalInterpolPts(uint16_t invalpts) { return true; }
		virtual bool GetInvalInterpolPts(uint16_t &invalpts) { return true; }
		virtual bool SetPeakMode(uint8_t peakMode) { return true; }
		virtual bool GetPeakMode(uint8_t &peakMode) { return true; }
		virtual bool SetExposureTimes(uint8_t exposureTimes) { return true; }
		virtual bool GetExposureTimes(uint8_t &exposureTimes) { return true; }
		virtual bool GetInstallTheta(double &theta) { return true; }
		virtual bool SetInstallTheta(double theta) { return true; }
		virtual bool GetInstallZCoeff(double &zCoeff) { return true; }
		virtual bool SetInstallZCoeff(double zCoeff) { return true; }
		virtual bool SetXCalibraParam(double *data, int datalen) { return true; }
		virtual bool GetXCalibraParam(double *data, int &datalen) { return true; }
		virtual bool SetDarkCorrection(bool darkMode) { return true; }
		virtual bool SetThreshSelect(int threshSelect) { return true; };
		virtual bool SetFilterParam(int type, int size) { return true; };
		virtual bool SetCenterCalibraParam(uint16_t centerX, uint16_t centerZ) { return true; }
		virtual bool GetCenterCalibraParam(uint16_t &centerX, uint16_t &centerZ) { return true; }
		virtual void StartRenderHeightMap();
		virtual void StopRenderHeightMap();

		virtual void StartSaveData(const std::string& filePath, int/*, std::promise<size_t>**/) override;
		virtual void StopSaveData() ;

		virtual void SetDeviceVector(std::vector<Device *> *device_vector);

		virtual bool GetTemperature(float &temperature) override { return false; };//获取设备温度
		virtual bool GetConnectedStatus() const  override { return false; };
		virtual bool SyncCurrentTimeToArm() override { return false; };
		virtual bool GetActualFrequency(uint32_t &freq)  override { return false; };
		virtual bool GetXZProportionality(uint32_t &xScale, uint32_t &zScale, int32_t &xOffset, int32_t &zoffset) override { return false; };//获取xz的比例系数
		virtual bool SetXZProportionality(uint32_t xScale, uint32_t zScale, int32_t xOffset, int32_t zoffset) override { return false; };//获取xz的比例系数

		/// \brief 设置坐标转换参数
		/// \param [in] theta 旋转角度
		/// \param [in] dx	X平移
		/// \param [in] dz	Z平移
		/// \return true-成功，false-失败
		virtual bool SetCoordTransformParam(float theta, float dx, float dz) override { return false; };

		/// \brief 获取坐标转换参数
		/// \param [out] theta 旋转角度
		/// \param [out] dx	X平移
		/// \param [out] dz	Z平移
		/// \return true-成功，false-失败
		virtual bool GetCoordTransformParam(float & theta, float & dx, float & dz) override { return false; };

	private:
		DeviceType       devType;
		std::vector<Device *> *v_devicePtr=nullptr;

		std::ofstream profileFile;

	//	ProfileOutput *profileOutput;
		OutputStreams*    streams;

		std::atomic_bool isCreated = false;
		std::atomic_bool isInputRunning = false;
		std::atomic_bool isRecvFrame = false;
		PThread           thread;
		PThread           framethread;
		


		static void *StartRecvData(void *puser);
		static void *StartRecvFrame(void *puser);

		void RecvSenserData();
		void RecvSenserFrame();

		int  getFirstFramId(ProfileOutputInterface *profileOutput);

		bool CreateProfileFile(std::string& filePath, const std::string currentTime, std::string subfold = "");
	};
}


#endif
