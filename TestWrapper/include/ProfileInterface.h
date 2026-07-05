#pragma once

#include "SpinnakerDefs.h"
#include <vector>

namespace FHJD_3D
{
	class ProfileInterface
	{
	public:
		ProfileInterface() {}
		virtual ~ProfileInterface() {}

	public:
		virtual int GetProfileNums() const = 0;

		virtual int GetWidth() const = 0;

		virtual int GetXScale() const = 0;

		virtual int GetZScale() const = 0;

		virtual int GetXOffset() const = 0;

		virtual int GetZOffset() const = 0;

		virtual int SetProfileData(ProfileData_t *data,int datalen) = 0;

		virtual int SetProfileRawData(ProfileData_t *data, int datalen) = 0;

		virtual ProfileData_t *GetProfileData() = 0;

		virtual ProfileData_t *GetProfileRawData() = 0;

		virtual Point16f* GetXZData() = 0;

		/**
		 * @brief 获取中心坐标和中心亮度数据
		 * return 中心坐标和中心亮度数据，(x1,y1,z1),...,(xn,yn,zn)，其中y1...yn代表中心亮度
		 */
		virtual Point16f* GetXZCData() = 0;

		/// \brief 获取Y值
		/// \return Y值
		virtual double GetYData() const = 0;

		virtual int GetMinmaxId() = 0;

		virtual void SetMinmaxId(int id) = 0;

		virtual void clearProfileData() = 0;

		virtual void InsertOutResult(OutResult &outResult) = 0;

		virtual std::vector<OutResult> * GetOutResult() = 0;

		virtual OutResult * GetCurResult() = 0;

		virtual OutResult * GetStaResult() = 0;

		virtual void CopyTo(ProfileInterface** other)=0;
	};
}
