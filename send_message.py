from protos import IncomingPushMessageSignal_pb2
from protos import WhisperTextProtocol_pb2
from keyutils import IdentityKeyUtil, ChatSessionUtil

import hmac
import hashlib
import os

import Crypto.Cipher.AES as AES

from database import session; session=session

from sqlalchemy import exists
from dbmodel import PreKey, PreKeyIndex, IdentityKey, RecipientPreKey

#from nacl.public import PrivateKey, Box
from curve25519 import keys

import ratcheting_session

sendDestinations = ['+611231231231']

from hkdf import Hkdf

def TSHKDF(secret, salt, info):

    if salt == None:
        salt = b"\x00" * 32

    tshkdf = ratcheting_session.HKDF().deriveSecrets(salt, secret)
    okm = tshkdf.expand(info, 64)

    RK = okm[:32]
    CK = okm[32:64]

    return [ RK, CK ]

def tripleDH(isInitiator, a, a0, B, B0):

    if isInitiator:
        sharedKey =  genDH( B, a0, ephemeral=0 )
        sharedKey +=  genDH( B0, a, ephemeral=1 )
        sharedKey +=  genDH( B0, a0, ephemeral=1 )
        return sharedKey
    else:
        sharedKey = genDH(B0, a, ephemeral=0)
        sharedKey += genDH(B, a0, ephemeral=1)
        sharedKey += genDH(B0, a0, ephemeral=1)
        return sharedKey

def genDH(a, B, ephemeral=0):
    key = keys.Private(secret=a, ephemeral=ephemeral)
    return key.get_shared_key(keys.Public(B), lambda x: x)




#initSession(true, baseKey, deviceObject.encodedNumber, deviceObject.identityKey, deviceObject.publicKey
def initSession(isInitiator, ourEphemeralKey, phoneNumber,
                theirIdentityPubkey, theirEphemeralPubKey, ourEpehemeralKeyPublic):

    # ourIdentityPrivKey -> B
    # ourEphemeralKey -> B0
    # theirIdentityPubkey -> A
    # theirEphemeralPubKey -> A0

    #here we can be sure that theiridentityPubkey, theirEphemeralPubKey are correct
    # also outEphemeralKey is selected by the prekeyid they gave us, so that is probably correct

    ourIdentityPrivKey = IdentityKeyUtil().getIdentityPrivKey()

    #theirEphemeralPubKey and ourEphemeralKey are wrong
    sharedKey = tripleDH(isInitiator, theirIdentityPubkey, theirEphemeralPubKey,
              ourIdentityPrivKey, ourEphemeralKey)

    # generate master_key = HASH( DH(A,B0) || DH(A0, B) || DH(A0,B0 )
    # note Box() function is backwards

    import binascii

    masterKey = ratcheting_session.HKDF().deriveSecrets(sharedKey, None, "WhisperText")

    print('masterKeys: ')
    print(binascii.hexlify(bytearray(masterKey[0])))
    print(binascii.hexlify(bytearray(masterKey[1])))

    session = { 'currentRatchet': { 'rootKey': masterKey[0],
                                   'ephemeralKeyPairPriv': ourEphemeralKey,
                                   'lastRemoteEphemeralKey': theirEphemeralPubKey } ,
               'oldRatchetList': []  }

    # depending on if we are sending or receiving ourEphemeralKey
    # is a public key or a private so we need to get the public key a different way
    session[ourEpehemeralKeyPublic] = { 'messageKeys': {},
                                       'chainKey': { 'counter': -1 , 'key': masterKey[1]  } }

    session[theirEphemeralPubKey] =  { 'messageKeys': {},
                                       'chainKey': { 'counter': 0xffffffff , 'key': ''  } }

    ChatSessionUtil().saveChatSession(phoneNumber, session)
    #save session into something

def encryptAESCTR(plaintext, key, counter):
    #counter is fixed? CRYPPTO BUG
    counter = bytes([counter])
    #counter = os.urandom(16)
    encrypto = AES.new(key, AES.MODE_CTR, counter=lambda: counter)
    encrypted = encrypto.encrypt(plaintext)
    return encrypted

def fillMessageKeys(chain, counter):
    messageKeys = chain['messageKeys']
    key = chain['chainKey']['key']

    # Chain Key Derivation
    for i in range(chain['chainKey']['counter'], counter):
        # Derive the message key
        messageKeys[i+1] = hmac.new(key, b"\x01", digestmod=hashlib.sha256).digest()
        # Derive the next chain key
        key = hmac.new(key, b"\x02", digestmod=hashlib.sha256).digest()

    chain['chainKey']['key'] = key
    chain['chainKey']['counter'] = counter

def doEncryptPushMessageContent(deviceObject, pushMessageContent, session):
    msg = WhisperTextProtocol_pb2.WhisperMessage()
    plaintext = pushMessageContent.SerializeToString()
    print(plaintext)

    print(session['currentRatchet'])
    msg.ephemeralKey = session['currentRatchet']['ephemeralKeyPairPub']
    chain = session[msg.ephemeralKey]

    fillMessageKeys(chain, chain['chainKey']['counter'] + 1)

    # Message Key Derivation
    keys = ratcheting_session.HKDF().deriveSecrets(chain['messageKeys'][chain['chainKey']['counter']], None, 'WhisperMessageKeys')
    del chain['messageKeys'][chain['chainKey']['counter']]
    msg.counter = chain['chainKey']['counter']

    #todo
    msg.previousCounter = 1

    msg.ciphertext = encryptAESCTR(plaintext, keys[0], chain['chainKey']['counter'])

    encodedMsg = msg.SerializeToString()

    print(encodedMsg)
    #TODO finish this function...
    #mac = calculateMACWithVersionByte(encodedMsg, keys[1], (2 << 4) | 2)

    pass

def encryptMessageFor(deviceObject, pushMessageContent):
    preKeyMsg = WhisperTextProtocol_pb2.PreKeyWhisperMessage
    preKeyMsg.identityKey = IdentityKeyUtil().getIdentityKey()
    keyPair = PrivateKey.generate()
    preKeyMsg.baseKey = keyPair.public_key
    preKeyMsg.keyId = deviceObject.keyId

    initSession(True, keyPair, deviceObject.phoneNumber,
                deviceObject.identityKey, deviceObject.publicKey)

    session = ChatSessionUtil().getChatSession(deviceObject.phoneNumber)

    doEncryptPushMessageContent(deviceObject, pushMessageContent, session)


def sendMessageToDevices(number, devicesForNumber, message):
    for deviceObject in devicesForNumber:
        encryptMessageFor(deviceObject, message)


def sendMessageToNumbers(sendDestinations, messageProto):
    for number in sendDestinations:
        devicesForNumber = getDeviceObjectListFromNumber(number)
        if len(devicesForNumber) == 0:
            #serverapi.getRecipientsPreKey
            pass
        else:
            sendMessageToDevices(number, devicesForNumber, messageProto)

def getDeviceObjectListFromNumber(number):
    return session.query(RecipientPreKey).\
        filter(RecipientPreKey.phoneNumber==number).\
        group_by(RecipientPreKey.deviceId).all()

def getDeviceIdListFromNumber(number):
    return session.query(RecipientPreKey.deviceId).\
        filter(RecipientPreKey.phoneNumber==number).distinct(RecipientPreKey.deviceId)



#serverapi.getRecipientsPreKey('')

'''
messageProto = IncomingPushMessageSignal_pb2.PushMessageContent()
messageProto.body = 'hello!'

sendMessageToNumbers(['+0123456789'],messageProto)
'''