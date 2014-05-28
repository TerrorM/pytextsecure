from gcm.protos import GooglePlay_pb2

def authenticatedCheckinRequest(androidId, securityToken, email, authSubToken):

    request = checkinRequest()
    request.id = androidId
    request.securityToken = securityToken

    request.accountCookie.append('[' + email + ']')
    request.accountCookie.append(authSubToken)
    return request


def checkinRequest():

    build = GooglePlay_pb2.AndroidBuildProto()

    build.id = 'samsung/m0xx/m0:4.0.4/IMM76D/I9300XXALF2:user/release-keys'
    build.product = 'smdk4x12'
    build.carrier = 'Google'
    build.radio = 'I9300XXALF2'
    build.bootloader = 'PRIMELA03'
    build.client = 'android-google'
    build.timestamp = 139756;
    build.googleServices = 16
    build.device = 'm0'
    build.sdkVersion = 16
    build.model = 'GT-I9300'
    build.manufacturer = 'Samsung'
    build.buildProduct = 'm0xx'
    build.otaInstalled = False


    #event = CheckIn_pb2.CheckinRequest.Checkin.Event()
    #event.tag = 'event_log_start'
    #event.timeMs = int(time.time())

    checkin = GooglePlay_pb2.AndroidCheckinProto()
    checkin.build.CopyFrom(build)
    checkin.lastCheckinMsec = 0
    checkin.cellOperator = '310260'
    checkin.simOperator = '310260'
    checkin.roaming = 'mobile-notroaming'
    checkin.userNumber = 0

    deviceConfig = GooglePlay_pb2.DeviceConfigurationProto()
    deviceConfig.touchScreen = 3
    deviceConfig.keyboard = 1
    deviceConfig.navigation = 1
    deviceConfig.screenLayout = 2
    deviceConfig.hasHardKeyboard = True
    deviceConfig.hasFiveWayNavigation = False
    deviceConfig.screenDensity = 1
    deviceConfig.glEsVersion = 131072
    #repeated string sharedLibrary = 9; // PackageManager.getSystemSharedLibraryNames
    #repeated string availableFeature = 10; // PackageManager.getSystemAvailableFeatures
    deviceConfig.nativePlatform.append('armeabi')
    deviceConfig.screenWidth = 769
    deviceConfig.screenHeight = 1280
    deviceConfig.systemSupportedLocale.append('en-US')
    #repeated string glExtension = 15; // GLES10.glGetString(GLES10.GL_EXTENSIONS)

    request = GooglePlay_pb2.AndroidCheckinRequest()
    #request.imei = '968938206575195'
    #request.androidId = 0x39512220812e0529
    #request.androidId = 0
    #request.digest = 'NDCGrhVX2G0HPDd3RP/f3g=='
    request.id = 0
    request.checkin.CopyFrom(checkin)
    request.locale = 'en_US'
    request.timeZone = "Europe/Istanbul"
    request.version = 3
    request.deviceConfiguration.CopyFrom(deviceConfig)
    request.fragment = 0;
    #request.loggingId = 235673
    #request.macAddress.append('b407f9849142')
    #request.meid = "5728E9A8302812"


    #optional fixed64 securityToken = 0;
    #optional int32 version = 14; // 3 if securityToken != 0 OR androidId == 0
    #request.otaCert.append("--no-output--")
    #request.serial = "3933E67396739201"
    #request.esn = '82057481'

    #repeated string macAddressType = 19; // "ethernet", "wifi"
    #optional int32 userSerialNumber = 22; // UserManager.getUserSerialNumber (if != 0)

    return request
