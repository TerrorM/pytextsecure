from gcm import defaultProtos
from gcm.protos import GooglePlay_pb2
import requests

class LoginError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class ServerError(Exception):
    def __init__(self , code, message):
        self.code = code
        self.message = message
    def __str__(self):
        return self.message

class GooglePlayAPI(object):

    SERVICE = "ac2dm"
    URL_LOGIN = "https://android.clients.google.com/auth" # "https://www.google.com/accounts/ClientLogin"
    ACCOUNT_TYPE_GOOGLE = "GOOGLE"
    ACCOUNT_TYPE_HOSTED = "HOSTED"
    ACCOUNT_TYPE_HOSTED_OR_GOOGLE = "HOSTED_OR_GOOGLE"
    authSubToken = None

    def __init__(self, email=None, password=None, debug=False): # you must use a device-associated androidId value
        self.preFetch = {}
        self.androidId = None
        self.regid = None
        self.debug = debug
        self.password = password
        self.email = email
        self.authenticated_checkedin = False

        if (email is None or password is None):
            raise Exception("You should provide at least authSubToken or (email and password)")


    def setAuthSubToken(self, authSubToken):
        self.authSubToken = authSubToken

        # put your auth token in config.py to avoid multiple login requests
        if self.debug:
            print("authSubToken: " + authSubToken)

    def login(self, email=None, password=None):
        """Login to your Google Account. You must provide either:
        - an email and password
        - a valid Google authSubToken"""
        if (self.authSubToken is not None):
            return self.authSubToken
        else:
            params = {"Email": self.email,
                                "Passwd": self.password,
                                "service": self.SERVICE,
                                "accountType": self.ACCOUNT_TYPE_HOSTED_OR_GOOGLE,
                                "has_permission": "1",
                                "source": "android",
                                #"androidId": self.androidId,
                                "androidId" : self.getAndroidIdStr(),
                                #"app": "com.android.vending",
                                "app": "com.google.android.gsf",
                                #"client_sig": self.client_sig,
                                "client_sig": "blah",
                                "device_country": "fr",
                                "operatorCountry": "fr",
                                "lang": "fr",
                                "sdk_version": "16"}
            headers = { "Accept-Encoding": "" }
            response = requests.post(self.URL_LOGIN, data=params, headers=headers, verify=False)
            data = response.text.split()

            params = {}
            for d in data:
                if not "=" in d: continue
                k, v = d.split("=")
                params[k.strip().lower()] = v.strip()
            if "auth" in params:
                self.setAuthSubToken(params["auth"])
                return params["auth"]
            elif "error" in params:
                raise LoginError("server says: " + params["error"])
            else:
                raise LoginError("Auth token not found.")
            return self.authSubToken

    #checks in a device and returns a androidid and securitytoken
    def checkin(self):

        if self.authSubToken and self.email:
            request = defaultProtos.authenticatedCheckinRequest(self.androidId,
                                                                self.securityToken,
                                                                self.email,
                                                                self.authSubToken)
        else:
            request = defaultProtos.checkinRequest()

        plaintext = request.SerializeToString()

        headers = {'Content-type': 'application/x-protobuffer'}

        r = requests.post('https://android.clients.google.com/checkin',
                         headers=headers,
                         data=plaintext )

        checkinResponseProto = GooglePlay_pb2.AndroidCheckinResponse()
        checkinResponseProto.ParseFromString(r.content)
        self.androidId = checkinResponseProto.androidId
        self.securityToken = checkinResponseProto.securityToken

    def authenticated_checkin(self):
        if not self.androidId or not self.securityToken:
            self.checkin()

        self.login(self.email,self.password)
        self.checkin()
        self.authenticated_checkedin = True

    def getAndroidIdStr(self):
        #returns string such as 6c83741de341
        return hex(self.androidId)[2:]

    def getAndroidId(self):
        if self.authenticated_checkedin:
            return self.androidId
        else:
            self.authenticated_checkin()
            return self.androidId

    def getSecurityToken(self):
        if self.authenticated_checkedin:
            return self.securityToken
        else:
            self.authenticated_checkin()
            return self.securityToken

    def register(self, app, senderId):
        #register
        if not self.androidId or not self.securityToken:
            raise 'Need an authenticated androidId and securityToken'

        '''
        POST /c2dm/register3 HTTP/1.1
        Authorization: AidLogin 4225320654661056283:5566832047112099807
        app: com.iapplize.gcm.test
        Content-Length: 171
        Content-Type: application/x-www-form-urlencoded
        Host: android.clients.google.com
        Connection: Keep-Alive
        User-Agent: AndroidC2DM/1.1 (vbox86tp JLS36G)

        X-GOOG.USER_AID=4225320654661056283&app=com.iapplize.gcm.test&sender=879830610296&cert=3e8287802e732b16cb88dd8c4b9cc518d553d435&device=4225320654661056283&device_user_id=0
        '''

        auth_header = 'AidLogin ' + str(self.androidId) + ':' + str(self.securityToken)

        headers = {'Content-type': 'application/x-www-form-urlencoded',
                   'Authorization' : auth_header,
                   'app' : 'com.iapplize.gcm.test',
                   'User-Agent': 'AndroidC2DM/1.1' }

        payload = {'X-GOOG.USER_AID' :  self.androidId,
                   'app' : app,
                   'sender': senderId,
                   'cert' : '',
                   'device': self.androidId,
                   'device_user_id': 0
                    }

        r = requests.post('http://android.clients.google.com/c2dm/register3',
                         headers=headers,
                         data=payload )

        if r.status_code == 401:
            raise ServerError(r.status_code, 'Invalid authentication credentials.')
        elif r.status_code == 200:

            #regid or is that a different value?
            self.regid = r.content.decode("utf-8").split("=")[1]

            return self.regid

