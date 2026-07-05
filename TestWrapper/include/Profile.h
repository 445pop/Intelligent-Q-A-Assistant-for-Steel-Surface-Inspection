#ifndef FHJD_SPINNAKER_PROFILE_H
#define FHJD_SPINNAKER_PROFILE_H

#include <vector>
#include "ProfileInterface.h"


namespace FHJD_3D
{
	struct ResampleProfileData_t;

	class Profile : public ProfileInterface
	{
	public:
		virtual ~Profile() 
		{
			if (profile_data_ptr_)
			{
				delete[] reinterpret_cast<char*>(profile_data_ptr_);
			}
			if (raw_profile_data_ptr_)
			{
				delete[] reinterpret_cast<char*>(raw_profile_data_ptr_);
			}
		}

		Profile() : ProfileInterface()
		{
			profile_data_ptr_ = NULL;
			raw_profile_data_ptr_ = NULL;
		}

		Profile(ResampleProfileData_t *resample_profile_data_ptr);

		Profile(ProfileData_t *profile_data_ptr);

		int GetProfileNums() const
		{
			return profile_data_ptr_->count;
		}

		int GetWidth() const
		{
			return profile_data_ptr_->width;
		}

		int GetXScale() const
		{
			return profile_data_ptr_->xScale;
		}

		int GetZScale() const
		{
			return profile_data_ptr_->zScale;
		}

		int GetXOffset() const
		{
			return profile_data_ptr_->xOffset;
		}

		int GetZOffset() const
		{
			return profile_data_ptr_->zOffset;
		}

		ProfileData_t *GetProfileData()
		{
			return profile_data_ptr_;
		}

		ProfileData_t *GetProfileRawData()
		{
			return raw_profile_data_ptr_;
		}

		Point16f* GetXZData()
		{
			int point_count = profile_data_ptr_->count * profile_data_ptr_->width;
			xz_data_.resize(point_count);
			for (int i = 0; i < point_count; i++)
			{
				xz_data_[i].x = profile_data_ptr_->points[i].x;
				xz_data_[i].z = profile_data_ptr_->points[i].z;
			}
			return xz_data_.data();
		}

		Point16f* GetXZCData()
		{
			return profile_data_ptr_->points;
		}

		void SetYData(double y_value)
		{
			y_value_ = y_value;
		}

		/// \brief 获取Y值
		/// \return Y值
		virtual double GetYData() const override
		{
			return y_value_;
		}

		//deep copy
		virtual int SetProfileData(ProfileData_t *data,int datalen)
		{
			ProfileData_t *temp = this->profile_data_ptr_;
		
			this->profile_data_ptr_ = (ProfileData_t*)new char[datalen];
			memcpy(this->profile_data_ptr_, data, datalen);
			if (temp)
			{
				delete[] reinterpret_cast<char*>(temp);
				temp = nullptr;
			}

			data_point_indexes_.resize(data->width*data->count);
			for (int i = 0; i < data_point_indexes_.size(); i++)
			{
				data_point_indexes_[i] = i;
			}

			return 0;
		}

		virtual int SetProfileRawData(ProfileData_t *data, int datalen)
		{
			ProfileData_t *temp = this->raw_profile_data_ptr_;
			this->raw_profile_data_ptr_ = (ProfileData_t*)new char[datalen];
			memcpy(this->raw_profile_data_ptr_, data, datalen);
			if (temp)
			{
				delete[] reinterpret_cast<char*>(temp);
				temp = nullptr;
			}

			raw_data_point_indexes_.resize(data->width*data->count);
			for (int i = 0; i < data_point_indexes_.size(); i++)
			{
				raw_data_point_indexes_[i] = i;
			}

			return 0;
		}

		virtual void clearProfileData()
		{
			if (profile_data_ptr_)
			{
				delete[] reinterpret_cast<char*>(profile_data_ptr_);
				profile_data_ptr_ = nullptr;
			}

			if (raw_profile_data_ptr_)
			{
				delete[] reinterpret_cast<char*>(raw_profile_data_ptr_);
				raw_profile_data_ptr_ = nullptr;
			}
		}

		int GetMinmaxId()
		{
			return outresult.minmaxid;
		}

		void SetMinmaxId(int id)
		{
			outresult.minmaxid = id;
		}


		virtual std::vector<OutResult> * GetOutResult()
		{
			return &v_outresult; 
		}

		virtual void InsertOutResult(OutResult &outResult)
		{
			v_outresult.emplace_back(std::move(outResult));
		}

		virtual OutResult * GetCurResult()
		{
			return &outresult;
		}

		virtual OutResult * GetStaResult()
		{
			return &st_outresult;
		}

		virtual void CopyTo(ProfileInterface** other)
		{
			Profile* temp = new Profile();
			other[0] = dynamic_cast<ProfileInterface*>(temp);

			int datalen = sizeof(ProfileData_t) + this->GetWidth() * sizeof(Point24f);
			temp->profile_data_ptr_ = (ProfileData_t*)new char[datalen];
			memcpy(temp->profile_data_ptr_, this->profile_data_ptr_, datalen);

			temp->data_point_indexes_ = this->data_point_indexes_;
			temp->raw_data_point_indexes_ = this->raw_data_point_indexes_;

			std::vector<OutResult> _v_outresult(v_outresult.begin(), v_outresult.end());
			for (auto iter = _v_outresult.begin(); iter != _v_outresult.end(); iter++)
			{
				temp->InsertOutResult(*iter);
			}
		}

		virtual std::vector<std::size_t> & GetProfileDataPointIndexes() final
		{
			return data_point_indexes_;
		}

		virtual std::vector<std::size_t> & GetProfileRawDataPointIndexes() final
		{
			return raw_data_point_indexes_;
		}

		void SetAvgLuminances(uint8_t *points, uint32_t point_count)
		{
			for (int i = 0; i < point_count; i++)
			{
				profile_data_ptr_->points[i].c = points[i];
				raw_profile_data_ptr_->points[i].c = points[i];
			}
		}

	private:
		/// \brief 载入数据
		/// \param [in] resample_profile_data_ptr 重采样轮廓数据指针
		void loadFromData(ResampleProfileData_t *resample_profile_data_ptr);

		/// \brief 载入数据
		/// \param [in] profile_data_ptr 轮廓数据指针
		void loadFromData(ProfileData_t *profile_data_ptr);

	private:
		ProfileData_t* profile_data_ptr_ = nullptr;			//处理过后的数据
		ProfileData_t* raw_profile_data_ptr_ = nullptr;		//原始数据
		std::vector<std::size_t> data_point_indexes_;
		std::vector<std::size_t> raw_data_point_indexes_;
		OutResult outresult;
		OutResult st_outresult;
		std::vector<OutResult> v_outresult;
		std::vector<Point16f> xz_data_; // 中心坐标XZ数据
		double y_value_{ 0 }; // Y值
	};

#if 0
	class ProfileList
	{
	public:
		virtual ~ProfileList() {};

		ProfileList() {};

		size_t GetNumProfile()
		{
			return profiles.size();
		}

		Profile* GetProfile(int index)
		{
			if (index > profiles.size())
				return NULL;
			return profiles.at(index);
		}

	private:
	    std::vector<Profile*> profiles;
    };
#endif
}

#endif