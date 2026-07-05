#pragma once
#include "Device.h"

namespace FHJD_3D
{

	class DeviceListInterface
	{
	public:
		/**
		* constructor.
		*/
		DeviceListInterface(void) {}

		/**
		* Virtual destructor.
		*/
		virtual ~DeviceListInterface(void) {}

		/**
		* Copy constructor
		*/
		DeviceListInterface(const DeviceListInterface *iface) {};

		/**
		* Assignment operator.
		*/
		DeviceListInterface* operator=(const DeviceListInterface* iface) {};

		/**
		* Array subscription operators.
		*/
		virtual Device* operator[](unsigned int index) = 0;

		/**
		* Returns the size of the camera list.  The size is the number
		* of Camera objects stored in the list.
		*
		* @return An integer that represents the list size.
		*/
		virtual unsigned int GetSize() const = 0;



		virtual bool Empty() const = 0;


		/**
		* Returns a pointer to a camera object at the "index". This function will throw
		* a Spinnaker exception with SPINNAKER_ERR_INVALID_PARAMETER error if the input
		* index is out of range.
		*
		* @param index The index at which to retrieve the camera object
		*
		* @return A pointer to an camera object.
		*/
		virtual Device* GetByIndex(unsigned int index) const = 0;

		/**
		* Returns a pointer to a camera object with the specified serial number. This
		* function will return a NULL CameraPtr if no matching camera serial is found.
		*
		* @param serialNumber The serial number of the camera object to retrieve
		*
		* @return A pointer to an camera object.
		*/
		virtual Device* GetBySerial(std::string serialNumber) const = 0;


		virtual Device* GetByIpadd(std::string ipadd) const = 0;
		virtual bool GetDeviceIpAddByIndex(unsigned int index,std::string& IpAdd) const = 0;

		/**
		* Clears the list of cameras and destroys their corresponding reference counted
		* objects. This is necessary in order to clean up the parent interface.
		* It is important that the camera list is destroyed or is cleared before calling
		* system->ReleaseInstance() or else the call to system->ReleaseInstance()
		* will result in an error message thrown that a reference to the camera
		* is still held.
		*
		* @see System:ReleaseInstance()
		*/
		virtual void Clear() = 0;

		/**
		* Removes a camera at "index" and destroys its corresponding reference counted
		* object. This function will throw a Spinnaker exception with
		* SPINNAKER_ERR_INVALID_PARAMETER error if the input index is out of range.
		*
		* @param index The index at which to remove the Camera object
		*/
		virtual void RemoveByIndex(unsigned int index) = 0;

		/**
		* Removes a camera using its serial number and destroys its corresponding reference counted
		* object. This function will throw a Spinnaker exception with SPINNAKER_ERR_NOT_AVAILABLE
		* error if no matching camera serial is found.
		*
		* @param serialNumber The serial number of the Camera object to remove
		*/
		virtual void RemoveBySerial(std::string serialNumber) = 0;

		virtual void RemoveByIp(const char* ipadd) = 0;

		/**
		* Appends a camera list to the current list.
		*
		* @param otherList The other list to append to this list
		*/
		virtual void Append(std::string ip,DeviceListInterface* otherList) = 0;

		virtual void Append(std::string ip, Device *device) = 0;
	};


}