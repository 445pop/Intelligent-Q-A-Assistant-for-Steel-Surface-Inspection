//=============================================================================
// Copyright (c) 2001-2018 FLIR Systems, Inc. All Rights Reserved.
//
// This software is the confidential and proprietary information of FLIR
// Integrated Imaging Solutions, Inc. ("Confidential Information"). You
// shall not disclose such Confidential Information and shall use it only in
// accordance with the terms of the license agreement you entered into
// with FLIR Integrated Imaging Solutions, Inc. (FLIR).
//
// FLIR MAKES NO REPRESENTATIONS OR WARRANTIES ABOUT THE SUITABILITY OF THE
// SOFTWARE, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
// PURPOSE, OR NON-INFRINGEMENT. FLIR SHALL NOT BE LIABLE FOR ANY DAMAGES
// SUFFERED BY LICENSEE AS A RESULT OF USING, MODIFYING OR DISTRIBUTING
// THIS SOFTWARE OR ITS DERIVATIVES.
//=============================================================================

#ifndef FLIR_SPINNAKER_DEFS_H
#define FLIR_SPINNAKER_DEFS_H
//#include "Network.h"
//#include <Windows.h>
//
//#include <memory.h>
#include <stdint.h>
#include <string>
#include "MeasureModeData.h"
//#include "UVTPInfo.h"

#ifndef min
#define min(x,y)  (x) < (y) ? (x):(y)
#endif

#ifndef max
#define max(x,y)  (x) > (y) ? (x):(y)
#endif



namespace FHJD_3D
{

	

    /**
    *  @defgroup SpinnakerHeaders Spinnaker Headers
    */

    /*@{*/

    /**
    * @defgroup SpinnakerDefs Spinnaker Definitions
    *
    * Definitions file for Spinnaker.
    */

    /**
    * Timeout values for getting next image, device, or interface event
    */
    const uint64_t EVENT_TIMEOUT_NONE = 0;					// Do not wait.  GetNextImage will return immediately. 
    const uint64_t EVENT_TIMEOUT_INFINITE = 0xFFFFFFFFFFFFFFFF;	// Never timeout.  GetNextImage will wait indefinitely.

	//typedef std::numeric_limits<float> nanInfo;
	//float const NaN_f = nanInfo::quiet_NaN();

	/**
	* 轮廓设置，轮廓过滤器设置
	*/
	struct smoothNumInfo
	{
		//过滤器点数smoothPoint设置,x轴
		unsigned int SPCnt_MEANX = 1;//1,2,4,...64
		unsigned int SPCnt_MEDIANX = 0;//off(0),3,5,7,9
		//过滤器次数smoothFrame设置,时间轴
		unsigned int SFCnt_MEANY = 1;//1,2,4,...256
		unsigned int SFCnt_MEDIANY = 0;//off(0),3,5,7,9
	};

	/**
	* 轮廓过滤器设置中中心线过滤器模式
	*/
	enum SmoothMode
	{
		SMOOTH_OFF,		//不使用过滤器
		SMOOTH_X,		//x轴
		SMOOTH_Y,       //y轴（时间轴）
	};


	struct paralleLinesPara
	{
		float k1 = NaN_f;//直线1的斜率
		float b1;//直线1的截距
		float k2 = NaN_f;//直线2的斜率
		float b2;//直线2的截距
		float hxz;//平行线间高度
		float htheta;//线与x轴的夹角
		bool flag = false;
	};


	struct OutResult
	{
		bool isvalid = false;				//OUT测量对象是否有效
		std::wstring out_name;				//OUT测量名称前段
		std::wstring dif_name;				//OUT测量名称后段
		float out_value = 0;				//OUT测量值，即显示在主界面上的值
		OUT_LEVEL out_level = LEVEL_GO;		//OUT测量报警值
		int minmaxid = -1;					//OUT测量值对应的点在点序列中的ID
		POSITION_MEASURE m_type;			//OUT测量类型
		float measure_value=0;				//OUT测量矩形框1的值
		float std_value=0;					//OUT测量矩形框2的值，与measure_value结合计算out_value
		paralleLinesPara para;				//平行线间的距离
		int framid;							//帧编号
		OutResult()
		{
			m_type = POSITION_MEASURE::POSITION_AV;
		}
	};




#pragma pack(push,1)
#if 0
	struct ProfileData
	{
		uint32_t Size;//为轮廓数据头(除size)+轮廓数据的长度
		uint16_t Control;//报文类型标志符
		uint16_t AttributeSize;//属性的大小
		uint32_t Count;//单条中心线
		uint32_t Width;//单条中心线的点数
		uint32_t xScale;//x比例
		uint32_t zScale;//z比例
		int32_t xOffset;//x偏移
		int32_t zOffset;//z偏移
		uint8_t Source;//源
		uint32_t Exposure;//曝光
		uint8_t CameraIndex;//相机索引
		uint8_t Reserved[2];//保留
							//Point16s坐标序列，存储xz值
		Point16f points[0];
	};
#endif
#pragma pack(pop)


	struct Rect 
	{
		int x;
		int y;
		int width;
		int height;
	};


	enum PixelFormatEnums
	{
		PixelFormat_RAW8,
		PixelFormat_RAW10
	};

	enum StreamType
	{
		OUTPUT_TIMESTAMP = 0x01,
		OUTPUT_IMAGE = 0x02,
		OUTPUT_PROFILE = 0x04,
		OUTPUT_HEIGHTMAP = 0X08
	};

	enum Transform
	{
		Transform_NONE,
		Transform_XInstallationCorrection,   //x direction installation correction
		Transform_ZInstallationCorrection,   //z direction installation correction
		Transform_XMeasurementCorrection,
		Transform_ZMeasurementCorrection,
		//out measurement
		Transform_AltitudeDifference,  //
	};


    /*@{*/

    /**
    * @brief Spinnaker enum definitions.
    */

    /**
    * The error codes used in Spinnaker.  These codes are returned as part of
    * Spinnaker::Exception.  The error codes in the range of -1000 to -1999
    * are reserved for exceptions that map directly to GenTL values.
    * The error codes in the range of -2000 to -2999 are reserved
    * for GenICam related errors.  The error codes in the range of -3000 to -3999
    * are reserved for image processing related errors.
    */
    enum Error
    {
        SPINNAKER_ERR_SUCCESS = 0,
        SPINNAKER_ERR_ERROR = -1001,
        SPINNAKER_ERR_NOT_INITIALIZED = -1002,
        SPINNAKER_ERR_NOT_IMPLEMENTED = -1003,
        SPINNAKER_ERR_RESOURCE_IN_USE = -1004,
        SPINNAKER_ERR_ACCESS_DENIED = -1005,
        SPINNAKER_ERR_INVALID_HANDLE = -1006,
        SPINNAKER_ERR_INVALID_ID = -1007,
        SPINNAKER_ERR_NO_DATA = -1008,
        SPINNAKER_ERR_INVALID_PARAMETER = -1009,
        SPINNAKER_ERR_IO = -1010,
        SPINNAKER_ERR_TIMEOUT = -1011,
        SPINNAKER_ERR_ABORT = -1012,
        SPINNAKER_ERR_INVALID_BUFFER = -1013,
        SPINNAKER_ERR_NOT_AVAILABLE = -1014,
        SPINNAKER_ERR_INVALID_ADDRESS = -1015,
        SPINNAKER_ERR_BUFFER_TOO_SMALL = -1016,
        SPINNAKER_ERR_INVALID_INDEX = -1017,
        SPINNAKER_ERR_PARSING_CHUNK_DATA = -1018,
        SPINNAKER_ERR_INVALID_VALUE = -1019,
        SPINNAKER_ERR_RESOURCE_EXHAUSTED = -1020,
        SPINNAKER_ERR_OUT_OF_MEMORY = -1021,
        SPINNAKER_ERR_BUSY = -1022,

        GENICAM_ERR_INVALID_ARGUMENT = -2001,
        GENICAM_ERR_OUT_OF_RANGE = -2002,
        GENICAM_ERR_PROPERTY = -2003,
        GENICAM_ERR_RUN_TIME = -2004,
        GENICAM_ERR_LOGICAL = -2005,
        GENICAM_ERR_ACCESS = -2006,
        GENICAM_ERR_TIMEOUT = -2007,
        GENICAM_ERR_DYNAMIC_CAST = -2008,
        GENICAM_ERR_GENERIC = -2009,
        GENICAM_ERR_BAD_ALLOCATION = -2010,

        SPINNAKER_ERR_IM_CONVERT = -3001,
        SPINNAKER_ERR_IM_COPY = -3002,
        SPINNAKER_ERR_IM_MALLOC = -3003,
        SPINNAKER_ERR_IM_NOT_SUPPORTED = -3004,
        SPINNAKER_ERR_IM_HISTOGRAM_RANGE = -3005,
        SPINNAKER_ERR_IM_HISTOGRAM_MEAN = -3006,
        SPINNAKER_ERR_IM_MIN_MAX = -3007,
        SPINNAKER_ERR_IM_COLOR_CONVERSION = -3008,
        SPINNAKER_ERR_IM_DECOMPRESSION = -3009,

        SPINNAKER_ERR_CUSTOM_ID = -10000
    };

    /**
    * Event types in Spinnaker.
    *
    * @see Event::GetEventType()
    */
    enum EventType
    {
        SPINNAKER_EVENT_ARRIVAL_REMOVAL,
        SPINNAKER_EVENT_DEVICE,
        SPINNAKER_EVENT_DEVICE_SPECIFIC,
        SPINNAKER_EVENT_NEW_BUFFER,
        SPINNAKER_EVENT_LOGGING_EVENT,
        SPINNAKER_EVENT_UNKNOWN
    };

    /**
    * This enum represents the namespace in which the TL specific pixel format
    * resides.  This enum is returned from a captured image when calling
    * Image::GetTLPixelFormatNamespace().  It can be used to interpret the raw
    * pixel format returned from Image::GetTLPixelFormat().
    *
    * @see Image::GetTLPixelFormat()
    *
    * @see Image::GetTLPixelFormatNamespace()
    */
    enum PixelFormatNamespaceID
    {
        SPINNAKER_PIXELFORMAT_NAMESPACE_UNKNOWN = 0,   /* GenTL v1.2 */
        SPINNAKER_PIXELFORMAT_NAMESPACE_GEV = 1,   /* GenTL v1.2 */
        SPINNAKER_PIXELFORMAT_NAMESPACE_IIDC = 2,   /* GenTL v1.2 */
        SPINNAKER_PIXELFORMAT_NAMESPACE_PFNC_16BIT = 3,   /* GenTL v1.4 */
        SPINNAKER_PIXELFORMAT_NAMESPACE_PFNC_32BIT = 4,   /* GenTL v1.4 */

        SPINNAKER_PIXELFORMAT_NAMESPACE_CUSTOM_ID = 1000
    };

    /**
     * Color processing algorithms. Please refer to our knowledge base at
     * article at http://www.ptgrey.com/support/kb/index.asp?a=4&q=33 for
     * complete details for each algorithm.
     */
    enum ColorProcessingAlgorithm
    {
        /** Default method. */
        DEFAULT,
        /** No color processing. */
        NO_COLOR_PROCESSING,
        /**
         * Fastest but lowest quality. Equivalent to
         * FLYCAPTURE_NEAREST_NEIGHBOR_FAST in FlyCapture.
         */
        NEAREST_NEIGHBOR,
        /** Weights surrounding pixels based on localized edge orientation. */
        EDGE_SENSING,
        /** Well-balanced speed and quality. */
        HQ_LINEAR,
        /** Slowest but produces good results. */
        RIGOROUS,
        /** Multi-threaded with similar results to edge sensing. */
        IPP,
        /** Best quality but much faster than rigorous. */
        DIRECTIONAL_FILTER,
        /** Weighted pixel average from different directions*/
        WEIGHTED_DIRECTIONAL_FILTER
    };

    enum PolarizationAlgorithm
    {
        /** No polarization. */
        NO_POLARIZATION,
        /** Extracts a Mono8 pixel format image of the 0 degree of polarization.
        * Polarization value pointer will be null. */
        QUADRANT_I0_GRAYSCALE,
        /** Extracts a Mono8 pixel format image of the 45 degree of polarization.
        * Polarization value pointer will be null. */
        QUADRANT_I45_GRAYSCALE,
        /** Extracts a Mono8 pixel format image of the 90 degree of polarization.
        * Polarization value pointer will be null. */
        QUADRANT_I90_GRAYSCALE,
        /** Extracts a Mono8 pixel format image of the 135 degree of polarization.
        * Polarization value pointer will be null. */
        QUADRANT_I135_GRAYSCALE,
        /** Extracts a Mono8 pixel format Stokes' parameter image S0. */
        STOKES_S0_GRAYSCALE,
        /** Extracts a BGRa8 pixel format HeatMap representation of the Stokes' parameter image S0. */
        STOKES_S0_HEATMAP,
        /** Extracts a Mono8 pixel format Stokes' parameter image S1. */
        STOKES_S1_GRAYSCALE,
        /** Extracts a BGRa8 pixel format HeatMap representation of the Stokes' parameter image S1. */
        STOKES_S1_HEATMAP,
        /** Extracts a Mono8 pixel format Stokes' parameter image S2. */
        STOKES_S2_GRAYSCALE,
        /** Extracts a BGRa8 pixel format HeatMap representation of the Stokes' parameter image S2. */
        STOKES_S2_HEATMAP,
        /** Extracts a Mono8 pixel format image representation of the DoLP (Degree of Linear Polarization). */
        DOLP_GRAYSCALE,
        /** Extracts a BGRa8 pixel format HeatMap representation of the DoLP (Degree of Linear Polarization).
        * Resulting polarization values are normalized between 0 and 1. */
        DOLP_HEATMAP,
        /** Extracts a Mono8 pixel format image representation of the AoP (Angle of Polarization). */
        AOP_GRAYSCALE,
        /** Extracts a BGRa8 pixel format HeatMap representation of the AoP (Angle of Polarization).
        * Resulting polarization values are normalized between 0 and 1. */
        AOP_HEATMAP
    };

    enum PolarizationResolution
    {
        /** Quarter Resolution. */
        QUARTER_RESOLUTION,
        /** Full Resolution. */
        FULL_RESOLUTION
    };

    enum HeatMapColor
    {
        HEATMAP_BLACK = 1,
        HEATMAP_BLUE = 2,
        HEATMAP_CYAN = 3,
        HEATMAP_GREEN = 4,
        HEATMAP_YELLOW = 5,
        HEATMAP_RED = 6,
        HEATMAP_WHITE = 7
    };

    /** File formats to be used for saving images to disk. */
    enum ImageFileFormat
    {
        FROM_FILE_EXT = -1, /**< Determine file format from file extension. */
        BMP, /**< Bitmap. */
    };

    /** Status of images returned from GetNextImage() call. */
    enum ImageStatus
    {
        IMAGE_UNKNOWN_ERROR = -1, /**< Image has an unknown error. */
        IMAGE_NO_ERROR = 0, /**< Image is returned from GetNextImage() call without any errors. */
        IMAGE_CRC_CHECK_FAILED = 1, /**< Image failed CRC check. */
        IMAGE_DATA_OVERFLOW = 2, /**< Received more data than the size of the image. */
        IMAGE_MISSING_PACKETS = 3, /**< Image has missing packets */
        IMAGE_LEADER_BUFFER_SIZE_INCONSISTENT = 4, /**< Image leader is incomplete. */
        IMAGE_TRAILER_BUFFER_SIZE_INCONSISTENT = 5, /**< Image trailer is incomplete. */
        IMAGE_PACKETID_INCONSISTENT = 6, /**< Image has an inconsistent packet id. */
        IMAGE_MISSING_LEADER = 7, /**< Image leader is missing. */
        IMAGE_MISSING_TRAILER = 8, /**< Image trailer is missing. */
        IMAGE_DATA_INCOMPLETE = 9, /**< Image data is incomplete. */
        IMAGE_INFO_INCONSISTENT = 10, /**< Image info is corrupted. */
        IMAGE_CHUNK_DATA_INVALID = 11, /**< Image chunk data is invalid */
        IMAGE_NO_SYSTEM_RESOURCES = 12 /**< Image cannot be processed due to lack of system
                                       resources. */
    };


    /** Options for saving Bitmap image. */
    struct BMPOption
    {
        bool indexedColor_8bit;
        /** Reserved for future use. */
        unsigned int reserved[16];

        BMPOption()
        {
            indexedColor_8bit = false;
            memset(reserved, 0, sizeof(reserved));
        }
    };

    /** Provides easier access to the current version of Spinnaker. **/
    struct LibraryVersion
    {
        /** Major version of the library **/
        unsigned int major;

        /** Minor version of the library **/
        unsigned int minor;

        /** Version type of the library **/
        unsigned int type;

        /** Build number of the library **/
        unsigned int build;
    };

    /**
    * Channels that allow statistics to be calculated.
    */
    enum StatisticsChannel
    {
        GREY,
        RED,
        GREEN,
        BLUE,
        HUE,
        SATURATION,
        LIGHTNESS,
        NUM_STATISTICS_CHANNELS
    };

    /** log levels */
    enum SpinnakerLogLevel
    {
        LOG_LEVEL_OFF = -1,			// Logging is off.
        LOG_LEVEL_FATAL = 0,		// Not used by Spinnaker.
        LOG_LEVEL_ALERT = 100,		// Not used by Spinnaker.
        LOG_LEVEL_CRIT = 200,		// Not used by Spinnaker.
        LOG_LEVEL_ERROR = 300,		// Failures that are non-recoverable without user intervention.
        LOG_LEVEL_WARN = 400,		// Failures that are recoverable without user intervention.
        LOG_LEVEL_NOTICE = 500,		// Events such as camera arrival and removal, initialization and deinitialization, starting and stopping image acquisition, and feature modification.
        LOG_LEVEL_INFO = 600,		// Information about recurring events that are generated regularly such as information on individual images.
        LOG_LEVEL_DEBUG = 700,		// Information that can be used to troubleshoot the system.
        LOG_LEVEL_NOTSET = 800		// Logs everything.
    };

    /* Enumeration of TLType dependent payload types. Introduced in GenTL v1.2 */
    enum PayloadTypeInfoIDs
    {
        PAYLOAD_TYPE_UNKNOWN = 0,		/* GenTL v1.2 */
        PAYLOAD_TYPE_IMAGE = 1,			/* GenTL v1.2 */
        PAYLOAD_TYPE_RAW_DATA = 2,		/* GenTL v1.2 */
        PAYLOAD_TYPE_FILE = 3,			/* GenTL v1.2 */
        PAYLOAD_TYPE_CHUNK_DATA = 4,	/* GenTL v1.2, Deprecated in GenTL 1.5*/
        PAYLOAD_TYPE_JPEG = 5,			/* GenTL v1.4 */
        PAYLOAD_TYPE_JPEG2000 = 6,		/* GenTL v1.4 */
        PAYLOAD_TYPE_H264 = 7,			/* GenTL v1.4 */
        PAYLOAD_TYPE_CHUNK_ONLY = 8,	/* GenTL v1.4 */
        PAYLOAD_TYPE_DEVICE_SPECIFIC = 9,   /* GenTL v1.4 */
        PAYLOAD_TYPE_MULTI_PART = 10,	/* GenTL v1.5 */

        PAYLOAD_TYPE_CUSTOM_ID = 1000,	/* Starting value for GenTL Producer custom IDs. */
        PAYLOAD_TYPE_EXTENDED_CHUNK = 1001
    };

    /** Possible Status Codes Returned from Action Command. */
    enum ActionCommandStatus
    {
        ACTION_COMMAND_STATUS_OK = 0,				/* The device acknowledged the command.*/
        ACTION_COMMAND_STATUS_NO_REF_TIME = 0x8013,	/* The device is not synchronized to a master clock to be used as time reference. Typically used when scheduled action commands cannot be scheduled for a future time since the reference time coming from IEEE 1588 is not locked. */
        ACTION_COMMAND_STATUS_OVERFLOW = 0x8015,	/* Returned when the scheduled action commands queue is full and the device cannot accept the additional request. */
        ACTION_COMMAND_STATUS_ACTION_LATE = 0x8016,	/* The requested scheduled action command was requested at a point in time that is in the past. */
        ACTION_COMMAND_STATUS_ERROR = 0x8FFF		/* Generic Error. Try enabling the Extended Status Code 2.0 bit on gvcp configuration register in order to receive more meaningful/detailed acknowledge messages from the device. */
    };

    /** Action Command Result */
    struct ActionCommandResult
    {
        unsigned int DeviceAddress;		/* IP Address of device that responded to Action Command. */
        ActionCommandStatus Status;		/* Action Command status return from device. */
    };

    /** Possible integer types and packing used in a pixel format. */
    enum PixelFormatIntType
    {
        IntType_UINT8,		/* Unsigned 8-bit integer. */
        IntType_INT8,		/* Signed 8-bit integer. */
        IntType_UINT10,		/* Unsigned 10-bit integer. */
        IntType_UINT10p,	/* LSB packed unsigned 10-bit integer. */
        IntType_UINT10P,	/* MSB packed unsigned 10-bit integer. */
        IntType_UINT12,		/* Unsigned 12-bit integer (unpacked). */
        IntType_UINT12p,	/* LSB packed unsigned 12-bit integer. */
        IntType_UINT12P,	/* MSB packed unsigned 12-bit integer. */
        IntType_UINT14,		/* Unsigned 14-bit integer (unpacked). */
        IntType_UINT16,		/* Unsigned 16-bit integer (unpacked). */
        IntType_FLOAT32,	/* 32-bit float. */
        IntType_UNKNOWN
    };

    enum BufferOwnership
    {
        BUFFER_OWNERSHIP_SYSTEM,   /* Buffers are owned and managed by the library */
        BUFFER_OWNERSHIP_USER      /* Buffers are owned and managed by the user */
    };

    /*@}*/

    /*@}*/


}

#endif // FLIR_SPINNAKER_DEFS_H
