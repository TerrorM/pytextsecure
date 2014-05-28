import socket
import ssl
import threading
import time

import queue

import google.protobuf.internal.decoder as GoogleProtobufDecoder

from gcm import mtalk, googleplayapi
from gcm.protos import GoogleServicesFramework_pb2

import config
import receive_textsecure
import dialogs

app = "org.thoughtcrime.securesms.gcm"
senderId = "312334754206"

#app = "com.iapplize.gcm.test"
#senderId = "879830610296"

q = queue.Queue()
quit_thread = False


def configGCM(email, password, app=app, senderId=senderId):
    gapi = googleplayapi.GooglePlayAPI(email, password)
    androidId = gapi.getAndroidId()
    securityToken = gapi.getSecurityToken()
    regid = gapi.register(app, senderId)

    config.setConfigOption('gcmandroidId', str(androidId))
    config.setConfigOption('gcmsecurityToken', str(securityToken))
    config.setConfigOption('gcmregid', regid)


def connectGCM(androidId, securityToken):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context()
    conn = context.wrap_socket(s, server_hostname=mtalk.server)
    conn.connect((mtalk.server, 5228))

    conn.sendall(b'\x07')
    data = conn.recv(1024)

    mtalkpacket = mtalk.Packets()
    loginRequestPacket = mtalkpacket.LoginRequestPacket(androidId, securityToken, hex(androidId)[2:])

    conn.sendall(loginRequestPacket)

    threading.Thread(target=send_heartbeats,
                     args=(conn, ),
                     daemon=True, ).start()

    lastStreamId = 1
    while True:
        data = b''
        while 1:
            data += conn.recv(1024)
            if len(data) != 0:
                packetlength, varintlength = GoogleProtobufDecoder._DecodeVarint(data, 1)
                if (len(data) - varintlength) == packetlength:
                    break

        tag = data[0]
        data = data[varintlength:]

        print('message parsed with tag: ' + str(tag))
        print(data)

        if tag == 0x00:
            print('Disconnected from GCM')
        if tag == 0x03:
            # Recieved LoginResponse
            loginResponse = GoogleServicesFramework_pb2.LoginResponse()
            loginResponse.ParseFromString(data)
            if loginResponse.error.code == 0:
                print('Login Successful')
        elif tag == 0x07:
            # Recieved DataMessageStanza
            iqStanza = GoogleServicesFramework_pb2.IQStanza()
            iqStanza.ParseFromString(data)
        elif tag == 0x08:
            # Recieved DataMessageStanza
            dataMessageStanza = GoogleServicesFramework_pb2.DataMessageStanza()
            dataMessageStanza.ParseFromString(data)
            if dataMessageStanza.category == app:
                for appdata in dataMessageStanza.appdata:
                    #print(appdata.key + ' - ' + appdata.value)
                    if appdata.key == 'message':
                        print('Received GCM message for textsecure')
                        receive_textsecure.receive_textsecure_message(appdata.value, q)
            else:
                pass
                #if debug:
                #    for appdata in dataMessageStanza.appdata:
                #        print(appdata.key + ' - ' + appdata.value)

        notificationRequestPacket = mtalkpacket.NotificationPacket(lastStreamId)
        conn.sendall(notificationRequestPacket)
        lastStreamId += 1

def send_heartbeats(conn):
    while True:
        time.sleep(120)
        send_heartbeat(conn)

def send_heartbeat(conn):
    mtalkpacket = mtalk.Packets()
    heartBeatPacket = mtalkpacket.HeartBeatPacket()

    conn.sendall(heartBeatPacket)

def start_gcm(GUIObject):

    #get config here to prevent reading from database in a thread
    androidId = int(config.getConfigOption('gcmandroidId'))
    securityToken = int(config.getConfigOption('gcmsecurityToken'))

    threading.Thread(target=connectGCM,
                     args=(androidId,
                           securityToken, ),
                     daemon=True,
    ).start()

    threading.Thread(target=handle_queue,
                     args=(GUIObject, ),
                     daemon=True,
    ).start()


def handle_queue(GUIObject):
    from gi.repository import Gdk
    while True:
        data = q.get()
        Gdk.threads_enter()
        GUIObject.received_message( data )
        Gdk.threads_leave()
        #GUIObject.set_chat_text(text)
