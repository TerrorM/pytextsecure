import random
import string
from gcm.protos import GoogleServicesFramework_pb2
import google.protobuf.internal.encoder as GoogleProtobufEncoder

server = "mtalk.google.com"

class Packets():

    def __init__(self): # you must use a device-associated androidId value
        self.id = 0
        self.prefix = self.randomString(7) + '-'
        self.packet_type = None

    def nextID(self):
        self.id += 1
        return self.prefix + str(self.id)

    def randomString(self, length):
        return "".join( random.choice(string.ascii_uppercase + string.digits) for _ in range(length) )

    def getBytes(self, protoPacket = 0):

        requestBytes = self.packet_type
        if protoPacket == 0:
            requestBytes += GoogleProtobufEncoder._VarintBytes(0)
        else:
            protoRequestBytes = protoPacket.SerializeToString()
            requestBytes += GoogleProtobufEncoder._VarintBytes(len(protoRequestBytes))
            requestBytes += protoRequestBytes

        return requestBytes

    def LoginRequestPacket(self, user, token, deviceID):
        self.packet_type = b'\x02'
        packet_id = self.nextID()

        heartbeatstat = GoogleServicesFramework_pb2.HeartBeatStat()
        heartbeatstat.timeout = False
        heartbeatstat.interval = 0

        loginRequest = GoogleServicesFramework_pb2.LoginRequest()
        loginRequest.packetid = packet_id
        #loginRequest.packetid = '\x41'
        loginRequest.domain = "mcs.android.com"
        loginRequest.user = str(user)
        loginRequest.resource = str(user)
        loginRequest.token = str(token)
        loginRequest.deviceid = "android-" + deviceID
        #lastrmqid 0
        #settings
        loginRequest.compress = 0
        #persistent ids
        #included streams in protobuf
        loginRequest.adaptiveheartbeat = False
        loginRequest.heartbeatstat.CopyFrom(heartbeatstat)
        loginRequest.accountid = -1
        loginRequest.unknown1 = 2
        loginRequest.networktype = 0

        return self.getBytes(loginRequest)

    def NotificationPacket(self, lastStreamId):
        self.packet_type = b'\x07'
        packet_id = self.nextID()

        extension = GoogleServicesFramework_pb2.Extension()
        extension.code = 10
        extension.message = "\x01\x20\x01"

        notificationRequest = GoogleServicesFramework_pb2.IQStanza()
        notificationRequest.type = 1
        notificationRequest.packetid = packet_id
        notificationRequest.extension.CopyFrom(extension)
        notificationRequest.laststreamid = lastStreamId
        notificationRequest.accountid = 1000000

        return self.getBytes(notificationRequest)

    def HeartBeatPacket(self):
        self.packet_type = b'\x00'
        return self.getBytes()
