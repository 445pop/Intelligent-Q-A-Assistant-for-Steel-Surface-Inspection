#ifndef FHJD_3D_SYSTEM_H
#define FHJD_3D_SYSTEM_H

#include "DeviceListInterface.h"

#ifdef API_EXPORTS
#define EXPORT_API __declspec(dllexport)
#else
#define EXPORT_API __declspec(dllimport)
#endif

namespace FHJD_3D
{
	

	class System
	{
	public:
		System() {}
		virtual ~System() {}

		virtual DeviceListInterface* GetDeviceList(/*bool update = true*/) = 0;

		virtual Device *GetFirstDevice() = 0;

		virtual Device *GetDeviceJoin() = 0;

		virtual bool GetCurrentVersion(std::string& versionnumber, std::string& builddate) = 0;
	};

	extern "C" __declspec(dllexport) System* __cdecl CreateSystem();
	extern "C" __declspec(dllexport) void __cdecl DestroySystem(void *handle);
}


#endif
