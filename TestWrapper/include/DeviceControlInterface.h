#ifndef FHJD_3D_DEVICECONTROL_INTERFACE__H
#define FHJD_3D_DEVICECONTROL_INTERFACE__H

#include <memory>
#include <string>
#include "BaseDefine.h"
#include "ProfileTypeInfo.h"

namespace FHJD_3D
{
	class DeviceControlInterface
	{
	public:
		//*************************************************
		//函数：Open(const char* deviceIpAddress)
		//参数：const char* deviceIpAddress 当前连接设备的ip地址
		//返回值：true 成功打开
		//说明：打开设备
		//*************************************************
		virtual bool Open(const char* url) = 0;

		//*************************************************
		//函数：IsOpened()
		//参数：
		//返回值：true 设备已经打开
		//说明：判断
		//*************************************************
		virtual bool IsOpened() = 0;

		//*************************************************
		//函数：Close()
		//参数：
		//返回值：true 成功关闭
		//说明：关闭设备
		//*************************************************
		virtual bool Close() = 0;

		//*************************************************
		//函数：GetTemperature(float &temperature)
		//参数：
		//返回值：float 设备温度
		//说明：获取设备温度
		//*************************************************
		virtual bool GetTemperature(float &temperature) = 0;

		//*************************************************
		//函数：GetConnectedStatus()
		//参数：
		//返回值：设备连接状态
		//说明：获取设备连接状态
		//*************************************************
		virtual bool GetConnectedStatus()const = 0;

		//*************************************************
		//函数：TrigByExternal()
		//参数：
		//返回值：
		//说明：外部触发
		//*************************************************
		virtual bool TrigByExternal() = 0;

		//*************************************************
		//函数：TrigByTime()
		//参数：
		//返回值：
		//说明：时间触发
		//*************************************************
		virtual bool TrigByTime() = 0;

		//*************************************************
		//函数：GetCapFrequency(uint32_t &frequency)
		//参数：uint32_t frequency 
		//返回值：是否获取到当前的采样频率
		//说明：按时间触发后，采样频率获取（Hz）
		//*************************************************
		virtual bool GetCapFrequency(uint32_t &frequency) = 0;

		//*************************************************
		//函数：SetCapFrequency(uint32_t &frequency)
		//参数：uint32_t frequency 
		//返回值：是否设置成功
		//说明：按时间触发后，采样频率设置（Hz）
		//*************************************************
		virtual bool SetCapFrequency(uint32_t frequency) = 0;

		//*************************************************
		//函数：GetLatestFrame() 
		//参数：无
		//返回值：std::shared_ptr<ProfileData> 返回轮廓
		//说明：获取当前轮廓并返回是否已经触发
		//*************************************************
		virtual std::shared_ptr<ProfileData> GetLatestFrame() = 0;

		//*************************************************
		//函数：GetFirstFrame() 
		//参数：无
		//返回值：std::shared_ptr<ProfileData> 返回轮廓
		//说明：获取最旧帧轮廓并返回是否已经触发
		//*************************************************
		virtual std::shared_ptr<ProfileData> GetFirstFrame() = 0;

		//*************************************************
		//函数：GetSensorAddress(std::string& m_ipAddress)
		//参数：m_ipAddress std::string 
		//返回值：
		//说明：获取设备地址
		//*************************************************
		virtual bool GetSensorAddress(std::string& m_ipAddress) = 0;

		//*************************************************
		//函数：SetSensorAddress(std::string& m_ipAddress，bool update)
		//参数：m_ipAddress std::string ； update bool 
		//返回值：
		//说明：获取设备地址
		//*************************************************
		virtual bool SetSensorAddress(std::string m_ipAddress, bool update) = 0;


		//*************************************************
		//函数：SetExposureTime(uint32_t exposureTime)
		//参数：uint32_t exposureTime 曝光时间
		//返回值：是否设置成功   超过曝光时间限制，设置失败
		//说明：设置曝光时间
		//*************************************************
		virtual bool SetExposureTime(uint32_t exposureTime) = 0;

		//*************************************************
		//函数：GetExposureTime(uint32_t exposureTime)
		//参数：uint32_t exposureTime 曝光时间
		//返回值：是否获取成功
		//说明：获取曝光时间
		//*************************************************
		virtual bool GetExposureTime(uint32_t &exposureTime) = 0;

		//*************************************************
		//函数：GetHDRMode(uint8_t &mode)
		//参数：uint8_t mode HDR成像模式
		//返回值：是否获取成功
		//说明：获取HDR成像模式
		//*************************************************
		virtual bool GetHDRMode(uint8_t &mode) = 0;

		//*************************************************
		//函数：SetHDRMode(uint8_t &mode)
		//参数：uint8_t mode HDR成像模式
		//返回值：是否设置成功
		//说明：设置HDR成像模式
		//*************************************************
		virtual bool SetHDRMode(uint8_t mode) = 0;

		//*************************************************
		//函数：SetLaserPower(uint8_t laserPower)
		//参数：uint8_t laserPower 成像光亮控制参数（0-100）
		//返回值：是否设置成功
		//说明：设置成像光亮控制参数
		//*************************************************
		virtual bool SetLaserPower(uint8_t laserPower) = 0;


		//*************************************************
		//函数：GetLaserPower(uint8_t laserPower)
		//参数：uint8_t laserPower 成像光亮控制参数（0-100）
		//返回值：是否获取成功
		//说明：获取成像光亮控制参数
		//*************************************************
		virtual bool GetLaserPower(uint8_t &laserPower) = 0;

		//*************************************************
		//函数：SetPeakSensitivity(uint8_t peakSensitivity)
		//参数：uint8_t peakSensitivity 灰度阈值提取中心线峰值灵敏度（1-5）
		//返回值：是否设置成功
		//说明：设置阈值提取中心线峰值灵敏度
		//备注：1难（阈值大，需要更亮的激光图），5易（阈值小，较暗的激光图也可提取轮廓）
		//*************************************************

		virtual bool SetPeakSensitivity(uint8_t peakSensitivity) = 0;

		//*************************************************
		//函数：GetPeakSensitivity(uint8_t peakSensitivity)
		//参数：uint8_t peakSensitivity 灰度阈值提取中心线峰值灵敏度（1-5）
		//返回值：是否获取成功
		//说明：获取阈值提取中心线峰值灵敏度
		//备注：1难（阈值大，需要更亮的激光图），5易（阈值小，较暗的激光图也可提取轮廓）
		//*************************************************
		virtual bool GetPeakSensitivity(uint8_t &peakSensitivity) = 0;

		//*************************************************
		//函数：Reset()
		//参数：
		//返回值：复位是否成功
		//说明：清空上位机数据缓冲，并通知下位机复位帧计数值
		//备注：
		//*************************************************
		virtual bool Reset() = 0;
		//*************************************************
		//函数：GetDeviceInfo()
		//参数：serialNo 获取序列号的变量值；scannetType扫描仪型号字符串
		//返回值：是否获取成功
		//说明：获取设备序列号
		//备注：
		//*************************************************
		virtual bool GetDeviceInfo(uint64_t &serialNo, char* scannetType) = 0;
		//*************************************************
		//函数：GetSampleType()
		//参数：uint8_t &type 触发模式（时间触发或者外同步触发）
		//返回值：当前触发模式
		//说明：获取当前触发模式
		//备注：
		//*************************************************
		virtual bool GetSampleType(uint8_t &type) = 0;
		//*************************************************
		//函数：SyncCurrentTimeToArm()
		//参数：无
		//返回值：true 时间同步成功  false 时间同步失败
		//说明：使当前时间与底层arm同步
		//*************************************************
		virtual bool SyncCurrentTimeToArm() = 0;
		//*************************************************
		//函数：GetActualFrequency()
		//参数：uint32_t &freq
		//返回值：true 获取成功  false 获取失败
		//说明：获取真实采样频率
		//*************************************************
		virtual bool GetActualFrequency(uint32_t &freq) = 0;

		/// \brief 设置坐标转换参数
		/// \param [in] theta 旋转角度，范围：[-180,180]
		/// \param [in] dx	X平移，范围：[-1000,1000]
		/// \param [in] dz	Z平移，范围：[-1000,1000]
		/// \return true-成功，false-失败
		virtual bool SetCoordTransformParam(float theta, float dx, float dz) = 0;

		/// \brief 获取坐标转换参数
		/// \param [out] theta 旋转角度
		/// \param [out] dx	X平移
		/// \param [out] dz	Z平移
		/// \return true-成功，false-失败
		virtual bool GetCoordTransformParam(float & theta, float & dx, float & dz) = 0;

		/// \brief 设置X方向画幅范围
		/// \param [in] x_mode X方向画幅模式，0-全幅，1-中幅，2-小幅
		/// \param [in] x_offset X方向偏移，限制如下：
		///				(1) 模式为全幅时，调整范围为[0,0]
		///				(2) 模式为中幅时，调整范围为[0,960]，且须为32的倍数
		///				(3) 模式为小幅时，调整范围为[0,1440]，且须为32的倍数
		/// \return true-成功，false-失败
		virtual bool SetXRange(uint8_t x_mode, uint16_t x_offset) = 0;

		/// \brief 获取X方向画幅范围
		/// \param [out] x_mode X方向画幅模式，0-全幅，1-中幅，2-小幅
		/// \param [out] x_offset X方向偏移
		/// \return true-成功，false-失败
		virtual bool GetXRange(uint8_t & x_mode, uint16_t & x_offset) = 0;

		/// \brief 设置Z方向画幅范围
		/// \param [in] z_mode Z方向画幅模式，0-全幅，1-中幅，2-小幅
		/// \param [in] z_offset Z方向偏移，限制如下：
		///				(1) 模式为全幅时，调整范围为[0,0]
		///				(2) 模式为中幅时，调整范围为[0,540]，且须为4的倍数
		///				(3) 模式为小幅时，调整范围为[0,810]，且须为4的倍数
		/// \return true-成功，false-失败
		virtual bool SetZRange(uint8_t z_mode, uint16_t z_offset) = 0;

		/// \brief 获取Z方向画幅范围
		/// \param [out] z_mode Z方向画幅模式，0-全幅，1-中幅，2-小幅
		/// \param [out] z_offset Z方向偏移
		/// \return true-成功，false-失败
		virtual bool GetZRange(uint8_t & z_mode, uint16_t & z_offset) = 0;

		/// \brief 取出缓存中第1帧图像
		/// \return 图像数据指针
		virtual std::shared_ptr<ImageData> GetFirstImage() const = 0;

		/// \breif 获取最新帧图像
		/// \return 图像数据指针
		virtual std::shared_ptr<ImageData> GetLatestImage() const = 0;
	};
}
#endif