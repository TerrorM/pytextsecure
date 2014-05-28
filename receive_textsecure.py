import hmac
import hashlib
import base64
import time

from protos import IncomingPushMessageSignal_pb2, WhisperTextProtocol_pb2
import sys

import Crypto.Cipher.AES as AES
from Crypto.Util import Counter

import config
from keyutils import PreKeyUtil, ChatSessionUtil, IdentityKeyUtil

import send_message
import ratcheting_session

from curve25519 import keys
import keyutils

import session_record
#import ratcheting_session

def receive_textsecure_message(message, q):
    global queue
    queue = q
    plaintext = decryptMessage(message)
    incomingPushMessageSignal = IncomingPushMessageSignal_pb2.IncomingPushMessageSignal()
    incomingPushMessageSignal.ParseFromString(plaintext)

    handleIncomingPushMessageProto(incomingPushMessageSignal)

class KeyExchangeProcessor():

    def __init__(self, phoneNumber, recipientDevice=1):
        self.recipientDevice = recipientDevice
        self.sessionRecord = session_record.SessionRecord(phoneNumber, recipientDevice)

    def processKeyExchangeMessage(self, message):
        # When sending a message to someone we may end up in this function
        ourBaseKey = ratcheting_session.Curve().generateKeyPair(True)
        ourEphemeralKey = ratcheting_session.Curve().generateKeyPair(True)
        theirBaseKey = message.publicKey
        theirEphemeralKey = theirBaseKey
        theirIdentityKey = message.identityKey
        ourIdentityKey = IdentityKeyUtil().getIdentityKeyPair()

        #if self.sessionRecord.sessionState.needsRefresh: self.sessionRecord.sessionState.archiveCurrentState()
        #else:                                            self.sessionRecord.sessionState.clear()

        ratcheting_session.initializeSession(self.sessionRecord.sessionState,
                                     ourBaseKey, theirBaseKey,
                                     ourEphemeralKey, theirEphemeralKey,
                                     ourIdentityKey, theirIdentityKey)

        self.sessionRecord.sessionState.setPendingPreKey(message.keyId, ourBaseKey.publicKey)
        self.sessionRecord.sessionState.setLocalRegistrationId(123)
        self.sessionRecord.sessionState.setRemoteRegistrationId(message.registrationId)

        self.sessionRecord.save()


    def processPreKeyExchangeMessage(self, message):
        # When receiving a message from someone we end up here
        preKeyId = message.preKeyId
        theirBaseKey = message.baseKey
        theirEphemeralKey = message.message.senderEphemeral
        theirIdentityKey = message.identityKey

        print("KeyExchangeProcessor: Received pre-key with local key ID: " + str(preKeyId))

        #if not PreKeyRecord().hasRecord(preKeyId) and SessionRecord().hasSession(self.recipientDevice):
        #    raise "We've already processed the prekey part, letting bundled message fall through..."

        #if not PreKeyRecord().hasRecord(preKeyId):
        #    print("No such prekey:" + str(preKeyId))
        #    raise "ERROR"

        preKeyRecord = PreKeyRecord(preKeyId)
        ourBaseKey = preKeyRecord.keyPair
        ourEphemeralKey = ourBaseKey
        ourIdentityKey = IdentityKeyUtil().getIdentityKeyPair()
        #simultaneousInitiate = self.sessionRecord.getSessionState().hasPendingPreKey()

        #if not simultaneousInitiate:
        #    self.sessionRecord.clear()
        #else:
        #    self.sessionRecord.archiveCurrentState()

        ratcheting_session.initializeSession(self.sessionRecord.sessionState,
                                             ourBaseKey, theirBaseKey,
                                             ourEphemeralKey, theirEphemeralKey,
                                             ourIdentityKey, theirIdentityKey)

        self.sessionRecord.sessionState.setLocalRegistrationId(123)
        self.sessionRecord.sessionState.setRemoteRegistrationId(message.registrationId)

        #if simultaneousInitiate:
        #    self.sessionRecord.getSessionState().setNeedsRefresh(True)

        self.sessionRecord.save()

        #if preKeyId != 0xFFFFFF:
        #    PreKeyRecord.delete(context, preKeyId)

        #preKeyService.initiateRefresh(context, masterSecret)

        #DatabaseFactory.getIdentityDatabase(context)
        #            .saveIdentity(masterSecret, recipientDevice.getRecipientId(). theirIdentity)

from protos import LocalStorageProtocol_pb2
class PreKeyRecord():

    def __init__(self, preKeyId):
        self.structure = LocalStorageProtocol_pb2.PreKeyRecordStructure()
        self.id = preKeyId
        #self.masterSecret = masterSecret

        self.loadData()

    def hasRecord(self, preKeyId):
        return PreKeyUtil().hasPreKey(self.preKeyId)

    def loadData(self):
        publicKey = ratcheting_session.Curve().decodePrivatePoint(PreKeyUtil().getPreKey(self.id))
        privateKey = ratcheting_session.Curve().decodePrivatePoint(PreKeyUtil().getPreKeyPrivate(self.id))
        self.publicKey = publicKey
        self.privateKey = privateKey
        self.keyPair = ECKeyPair( self.publicKey , self.privateKey )

class ECKeyPair():

    def __init__(self, publicKey, privateKey):
        self.publicKey = publicKey
        self.privateKey = privateKey

class CipherTextMessage:

    UNSUPPORTED_VERSION = 1
    CURRENT_VERSION = 2
    WHISPER_TYPE = 2
    PREKEY_TYPE = 3

    ENCRYPTED_MESSAGE_OVERHEAD = 53

class PreKeyWhisperMessage(CipherTextMessage):

    def __init__(self, serialized=None, registrationId=None, preKeyId=None, baseKey=None, identityKey=None, message=None):
        self.type = self.PREKEY_TYPE

        if serialized:
            self.initFromSerialized(serialized)
        else:
            self.initFromParams(registrationId, preKeyId, baseKey, identityKey, message)

    def initFromParams(self, registrationId, preKeyId, baseKey, identityKey, message):
        self.version = self.CURRENT_VERSION
        self.registrationId = registrationId
        self.preKeyId = preKeyId
        self.baseKey = baseKey
        self.identityKey = identityKey
        self.message = message

        versionBytes = bytes([((self.CURRENT_VERSION << 4 | self.version) & 0xFF)])
        messageProto = WhisperTextProtocol_pb2.PreKeyWhisperMessage()
        messageProto.preKeyId = preKeyId
        messageProto.baseKey = baseKey.serialize()
        messageProto.identityKey = b'\x05' + identityKey
        messageProto.message = message.serialized
        messageProto.registrationId = registrationId

        messageBytes = messageProto.SerializeToString()

        self.serialized = versionBytes + messageBytes


    def initFromSerialized(self, serialized):
        self.version = (serialized[0] & 0xFF) >> 4

        if self.version > self.CURRENT_VERSION:
            raise "Unknown version: " + str(self.version)

        preKeyWhisperMessage = WhisperTextProtocol_pb2.PreKeyWhisperMessage()
        preKeyWhisperMessage.ParseFromString(serialized[1:])

        self.serialized = serialized
        self.registrationId = preKeyWhisperMessage.registrationId
        self.preKeyId = preKeyWhisperMessage.preKeyId
        self.baseKey = ratcheting_session.Curve().decodePoint(preKeyWhisperMessage.baseKey) #decode point...?
        self.identityKey = ratcheting_session.Curve().decodePoint(preKeyWhisperMessage.identityKey)
        self.message = WhisperMessage(serialized=preKeyWhisperMessage.message)

class WhisperMessage(CipherTextMessage):

    MAC_LENGTH = 8

    def __init__(self, serialized=None, macKey=None, senderEphemeral=None, counter=None, previousCounter=None, ciphertext=None):
        self.type = self.WHISPER_TYPE

        if serialized:
            self.initFromSerialized(serialized)
        else:
            self.initFromParams(macKey, senderEphemeral, counter, previousCounter, ciphertext)

    def initFromParams(self, macKey, senderEphemeral, counter, previousCounter, ciphertext):
        version = ((self.CURRENT_VERSION << 4 | self.CURRENT_VERSION) & 0xFF)
        message = WhisperTextProtocol_pb2.WhisperMessage()
        message.ephemeralKey = senderEphemeral.serialize()
        message.counter = counter
        message.previousCounter = previousCounter
        message.ciphertext = ciphertext

        mac = self.getMac(macKey, bytes([version]) + message.SerializeToString())

        self.serialized = bytes([version]) + message.SerializeToString() + mac
        self.senderEpehmeral = senderEphemeral
        self.counter = counter
        self.previousCounter = previousCounter
        self.ciphertext = ciphertext

    def initFromSerialized(self, serialized):
        version = serialized[0] #is this int 34? because initparams is int 34...
        message = serialized[1:][:len(serialized) - 1 - self.MAC_LENGTH]
        mac = serialized[len(serialized) - 1 - self.MAC_LENGTH:][:self.MAC_LENGTH]

        if (version & 0xFF) >> 4 <= 1:
            raise "Legacy message: " + str((version & 0xFF) >> 4)

        if (version & 0xFF) >> 4 != 2:
            raise "Unknown version: " + str((version & 0xFF) >> 4)


        #if highBitsToInt(version) <= self.UNSUPPORTED_VERSION:
        #    raise "Legacy Message: " + str(version)

        #if highBitsToInt(version) != self.CURRENT_VERSION:
        #    raise "Unknown version: " + str(version)

        whisperMessage = WhisperTextProtocol_pb2.WhisperMessage()
        whisperMessage.ParseFromString(message)

        self.serialized = serialized
        self.senderEphemeral = ratcheting_session.Curve().decodePoint(whisperMessage.ephemeralKey)
        self.counter = whisperMessage.counter
        self.previousCounter = whisperMessage.previousCounter
        self.ciphertext = whisperMessage.ciphertext


    def verifyMac(self, macKey):
        ourMac = self.getMac( macKey, self.serialized[:len(self.serialized) - self.MAC_LENGTH] )
        theirMac = self.serialized[len(self.serialized) - self.MAC_LENGTH:][:self.MAC_LENGTH]

        if not ourMac == theirMac:
            print( "Bad Mac! (inside WhisperMessage verifyMac)")

    def getMac(self, macKey, serialized):
        fullMac = hmac.new(macKey, serialized, digestmod=hashlib.sha256).digest()
        return fullMac[:self.MAC_LENGTH]


def handleReceivedPreKeyBundle( incomingPushMessageSignal ):
    recipient = incomingPushMessageSignal.source
    recipientDevice = incomingPushMessageSignal.sourceDevice

    processor = KeyExchangeProcessor(recipient)

    preKeyExchange = PreKeyWhisperMessage(serialized=incomingPushMessageSignal.message)

    processor.processPreKeyExchangeMessage(preKeyExchange)

    incomingPushMessageSignal.message = preKeyExchange.message.serialized
    bundledMessage = incomingPushMessageSignal
    handleReceivedSecureMessage(bundledMessage)

RESULT_OK = 1

def handleDecrypt(incomingPushMessageSignal, message_id, result):

    pushMessageContent = IncomingPushMessageSignal_pb2.PushMessageContent()
    pushMessageContent.ParseFromString(incomingPushMessageSignal.message)

    if pushMessageContent.flags == pushMessageContent.END_SESSION:
        handleEndSessionMessage(incomingPushMessageSignal, pushMessageContent)
    else:
        handleReceivedTextMessage(incomingPushMessageSignal, pushMessageContent)


def handleEndSessionMessage(incomingPushMessageSignal, pushMessageContent):
    recipient = incomingPushMessageSignal.source

    session_record.SessionRecord(recipient).deleteAll()
    #KeyExchangeProcessor.broadcastSecurityUpdateEvent()

def handleReceivedTextMessage(incomingPushMessageSignal, pushMessageContent):
    global queue
    #insert into the database... or whatever here
    alias = keyutils.RecipientUtil().getAliasFromNumber(incomingPushMessageSignal.source)
    data = { 'alias' : alias, 'message' : pushMessageContent.body }
    print(alias + ': ' + pushMessageContent.body)
    queue.put(data)

def handleReceivedSecureMessage(incomingPushMessageSignal):
    # some database shit happens here?
    #id = Database.getPushDatabase(context).insert(message)

    # it queues it for decryption... but we dont need to I guess
    decryptWorkItem(1, incomingPushMessageSignal)

import session_cipher
def decryptWorkItem(message_id, incomingPushMessageSignal):
    recipient = incomingPushMessageSignal.source
    recipientDevice = incomingPushMessageSignal.sourceDevice

    #if not SessionRecord().hasSession(recipientDevice):
    #    sendResult(pushReceiver.RESULT_NO_SESSION)

    sessionCipher = session_cipher.SessionCipher(recipient)
    plaintextBody = sessionCipher.decrypt(incomingPushMessageSignal.message)

    incomingPushMessageSignal.message = plaintextBody

    handleDecrypt(incomingPushMessageSignal, message_id, RESULT_OK)

def handleIncomingPushMessageProto(incomingPushMessageSignal):
    # by now the outside AES is decrypted

    if incomingPushMessageSignal.type == 0: # TYPE_MESSAGE_PLAINTEXT
        pass
    elif incomingPushMessageSignal.type == 1: # TYPE_MESSAGE_CIPHERTEXT
        handleReceivedSecureMessage(incomingPushMessageSignal)
    elif incomingPushMessageSignal.type == 3: # TYPE_MESSAGE_PREKEY_BUNDLE
        if incomingPushMessageSignal.message[0] != (2 << 4 | 2):
            raise "Bad version byte"

        handleReceivedPreKeyBundle(incomingPushMessageSignal)


def decryptMessage(message):
    signalingKey = config.getConfigOption("signalingKey")

    aes_key = signalingKey[0:32]
    mac_key = signalingKey[32:32+20]

    data = base64.b64decode(message)
    if data[0] != 1:
        raise "Got bad version number: " + str(data[0])

    iv = data[1:1+16]
    ciphertext = data[1+16: len(data) - 10]
    ivAndCipherText = data[1: len(data) - 10]
    mac = data[len(data) - 10: ]

    verifyMACWithVersionByte(ivAndCipherText, mac_key, mac)

    return decryptPaddedAES(ciphertext, aes_key, iv)

def verifyMACWithVersionByte(data, key, mac, version = 1 ):
    calculated_mac = hmac.new(key, bytes([version]) + data, digestmod=hashlib.sha256).digest()

    #print(calculated_mac)
    #print(mac)

    if calculated_mac[0:10] != mac:
        print("Bad MAC")

def encryptAESCTR(plaintext, key, counter):
    import struct
    counterbytes = struct.pack('>L', counter) + (b'\x00' * 12)
    counterint = int.from_bytes(counterbytes, byteorder='big')
    ctr=Counter.new(128, initial_value=counterint)

    encrypto = AES.new(key, AES.MODE_CTR, counter=ctr)
    ciphertext = encrypto.encrypt(plaintext)
    return ciphertext


def decryptAESCTR(ciphertext, key, counter):
    #print('AESCTR counter: ')
    #print(counter)


    import struct
    counterbytes = struct.pack('>L', counter) + (b'\x00' * 12)
    counterint = int.from_bytes(counterbytes, byteorder='big')
    ctr=Counter.new(128, initial_value=counterint)

    decrypto = AES.new(key, AES.MODE_CTR, counter=ctr)
    plaintext = decrypto.decrypt(ciphertext)
    return plaintext


#def intToByteArray(bytes, offset, value):
#    bytes[offset+3] = value
#    bytes[offset+2] = (value >> 8)
#    bytes[offset+1] = (value >> 16)
#    bytes[offset] = (value >> 24)
#    return bytes


def decryptPaddedAES(ciphertext, key, iv):

    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = _unpad(cipher.decrypt(ciphertext))
    return decrypted

def _unpad(s):
    return s[:-ord(s[len(s)-1:])]

