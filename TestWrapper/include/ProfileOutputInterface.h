#pragma once

#include "ProfileInterface.h"
#include "MeasureModeData.h"
#include <map>

//#define ENABLE_SAVE_FILE   //在代理类中保存轮廓数据和图像数据

#ifdef ENABLE_SAVE_FILE
//#define ENABLE_SAVE_OUT   //是否保存用于计算OUT测量值的轮廓数据
#ifdef ENABLE_SAVE_OUT
#include <atomic>
#endif
#endif

namespace FHJD_3D
{
	class Device;
	class ProfileOutputInterface
	{
	public:
		virtual ~ProfileOutputInterface() {};
		virtual void Insert(ProfileInterface* frame) = 0;
		virtual void AddFrame(ProfileInterface* frame)=0;
		virtual void CalcOut(ProfileInterface* frame) = 0;
		virtual void InsertPostProcess(ProfileInterface* frame) = 0;
		virtual ProfileInterface* GetLatestFrame() = 0;
		virtual ProfileInterface* GetFirstFrame() = 0;
		virtual ProfileInterface* GetJoinFirstFrame()=0;
		virtual ProfileInterface* GetSaveFirstFrame()=0;
		virtual void ClearFrames() = 0;
		virtual void SetOutMeasure(OUT_MEASURE *out, ProfileInterface*profile) = 0;
		virtual void SetOutMeasure(OUT_MEASURE *out, OutResult& result, OutResult& staresult, bool isCurProfile = false) =0;
		virtual std::vector<OUT_MEASURE> * GetOutInfo() = 0;
		virtual bool HasRegistProfile() = 0;

		virtual void RegistProfile(ProfileInterface * profile) = 0;

		virtual void UnregistProfile() = 0;

		virtual ProfileInterface *GetRegistProfile() = 0;

		virtual void SetCurOut(OUT_MEASURE *out) = 0;
		virtual OUT_MEASURE * GetCurOut() = 0;

		virtual void ZScale(ProfileData_t* srcPts, float scale, ProfileData_t* dstPts)=0;//Z方向校准
		virtual void ZScale(ProfileInterface* frame, float scale) = 0;//Z方向校准 
		virtual void setZScaleFactor(float scale) = 0;//设置Z方向校准因子
		virtual void EnableZScale(bool _isZScaleEnable) = 0;//使能Z方向校准
		virtual float getZScaleFactor() = 0;//获取安装校准角度


		virtual void RotatePoints(ProfileData_t* srcPts, float angle, ProfileData_t* dstPts, bool isClockWise = true) = 0;
	
		virtual void setCorrectAngle(float angle) = 0;//设置安装校准角度

		virtual void EnableCorrect(bool _isCorrectEnable) = 0;//使能安装校准
		virtual void EnableZReverse(bool isZReverseEnable) = 0;  //x方向反转使能
		virtual void EnableXReverse(bool isXReverseEnable) = 0;	//z方向反转使能


		virtual bool getXCorrectEnable()= 0;
		virtual bool getZScaleEnable()= 0;

		virtual float getCorrectAngle() = 0;

		virtual void dataFilter(ProfileData_t* data) = 0;

		virtual int getPointIdInRect(std::map<unsigned, Point16f> ptMap, float ave, MEASURE_DIRECTION measureDir, OUT_DIRECTION outDir, int index) = 0;

		virtual void setXCorrect(DirectionXCorrect value) = 0;

		virtual DirectionXCorrect& getXCorrect() = 0;

		virtual ProfileInterface * getTempProfile() = 0;

		virtual void setXOffset(float offset) = 0;
		virtual void setZOffset(float offset) =0 ;
		virtual float getXOffset() = 0;
		virtual float getZOffset() =0 ;

		virtual void calcParalleLinePara(std::map<unsigned, FHJD_3D::Point16f>& xzfit1, std::map<unsigned, FHJD_3D::Point16f>& xzfit2, paralleLinesPara &m_para) = 0;

		virtual float wrapXCorrect(BasePosition * pos, ProfileData_t *profileData) =0;

		virtual void setSmoothCnt(smoothNumInfo m_smoothNumInfo) = 0;
		virtual smoothNumInfo getSmoothCnt() = 0;
		virtual void smoothX(ProfileInterface* frame, int smoothCnt, bool xory) = 0;
		virtual void smoothY(const std::vector<ProfileInterface*> &frameBuffer, int smoothCnt, bool xory) = 0;
		virtual void doCalculate(ProfileInterface *profile, OUT_MEASURE *out, bool isTemp = false)=0;
		virtual void doCalculate(ProfileInterface *profile, OUT_MEASURE *out, OutResult& result, OutResult& staresult, bool isTemp = false)=0;
		virtual void initOutInfo()=0;

		virtual OUT_MEASURE * GetOutMeasureResult(OutResult& result, OutResult& staresult)=0;		//计算选定OUT测量的数据

		virtual void UpdateOutInfo(Device *) = 0;

		virtual void circfit(std::vector<Point16f> vecPoints, Point16f &ptc, float &radius)=0;	//拟合圆

		virtual void startMeasure(bool) = 0;

		virtual void LeastSquareFit(std::map<unsigned, Point16f>& ptMap, float(&linearPara)[2]) = 0;
#ifdef ENABLE_SAVE_OUT
	public:
		std::atomic_bool isFinishSaveFile = true;//是否结束文件保存线程
#endif
	};
}