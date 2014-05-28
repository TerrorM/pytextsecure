
from keyutils import PreKeyUtil, ChatSessionUtil, IdentityKeyUtil

import hmac
import hashlib

from curve25519 import keys

#initSession(true, baseKey, deviceObject.encodedNumber, deviceObject.identityKey, deviceObject.publicKey
#def initSession(isInitiator, ourEphemeralKey, phoneNumber,
#                theirIdentityPubkey, theirEphemeralPubKey):

def initializeSession(sessionState, ourBaseKey, theirBaseKey,
                ourEphemeralKey, theirEphemeralKey,
                ourIdentityKey, theirIdentityKey):

    if isAlice( ourBaseKey.publicKey.publicKey, theirBaseKey, ourEphemeralKey.publicKey.publicKey, theirEphemeralKey ):
        initializeSessionAsAlice(sessionState, ourBaseKey, theirBaseKey, theirEphemeralKey,
                                 ourIdentityKey, theirIdentityKey)
    else:
        initializeSessionAsBob(sessionState, ourBaseKey, theirBaseKey,
                               ourEphemeralKey, ourIdentityKey, theirIdentityKey)


def initializeSessionAsAlice(sessionState,
                           ourBaseKey, theirBaseKey,
                           theirEphemeralKey,
                           ourIdentityKey, theirIdentityKey):

    sessionState.setRemoteIdentityKey(theirIdentityKey)
    sessionState.setLocalIdentityKey(ourIdentityKey.publicKey)

    sendingKey = Curve().generateKeyPair( True )

    receivingChain = calculate3DHE( True, ourBaseKey, theirBaseKey,
                                 ourIdentityKey, theirIdentityKey)

    sendingChain = receivingChain[0].createChain( theirEphemeralKey.publicKey, sendingKey, ephemeral=1 )


    sessionState.addReceiverChain(theirEphemeralKey, receivingChain[1] )
    sessionState.setSenderChain( sendingKey, sendingChain[1] )
    sessionState.setRootKey( sendingChain[0] )


def initializeSessionAsBob(sessionState,
                           ourBaseKey, theirBaseKey,
                           ourEphemeralKey,
                           ourIdentityKey, theirIdentityKey):

    sessionState.setRemoteIdentityKey(theirIdentityKey)
    sessionState.setLocalIdentityKey(ourIdentityKey.publicKey)

    sendingChain = calculate3DHE( False, ourBaseKey, theirBaseKey,
                                 ourIdentityKey, theirIdentityKey)

    sessionState.setSenderChain( ourEphemeralKey, sendingChain[1] )
    sessionState.setRootKey(sendingChain[0])


def calculate3DHE( isAlice,
                   ourEphemeral, theirEphemeral,
                   ourIdentity, theirIdentity ):

    if isAlice: #alice
        sharedKey = Curve().calculateAgreement( theirEphemeral.publicKey, ourIdentity.privateKey )
        sharedKey += Curve().calculateAgreement( theirIdentity.publicKey, ourEphemeral.privateKey.publicKey, ephemeral=1 )
        sharedKey += Curve().calculateAgreement(theirEphemeral.publicKey, ourEphemeral.privateKey.publicKey, ephemeral=1 )
    else: #bob
        sharedKey = Curve().calculateAgreement(theirIdentity.publicKey, ourEphemeral.privateKey.publicKey)
        sharedKey += Curve().calculateAgreement(theirEphemeral.publicKey, ourIdentity.privateKey)
        sharedKey += Curve().calculateAgreement(theirEphemeral.publicKey, ourEphemeral.privateKey.publicKey)

    cipherKey, macKey = HKDF().deriveSecrets(sharedKey, None, "WhisperText")

    return ( RootKey ( cipherKey ) , ChainKey( macKey, 0 ) )


def isAlice(ourBaseKey, theirBaseKey,
            ourEphemeralKey, theirEphemeralKey):

    if ourEphemeralKey == ourBaseKey:
        return False

    if theirEphemeralKey == theirBaseKey:
        return True

    if ourBaseKey < theirBaseKey:
        return False



class MessageKeys:

    def __init__(self, cipherKey, macKey, counter):
        self.cipherKey = cipherKey
        self.macKey = macKey
        self.counter = counter

    def getCipherKey(self):
        return self.cipherKey

    def getMacKey(self):
        return self.macKey

    def getCounter(self):
        return self.counter


class ChainKey:

    MESSAGE_KEY_SEED = b'\x01'
    CHAIN_KEY_SEED = b'\x02'

    def __init__(self, key, index):
        self.key = key
        self.index = index

    def getKey(self):
        return self.key

    def getIndex(self):
        return self.index

    def getNextChainKey(self):
        nextKey = self.getBaseMaterial(self.CHAIN_KEY_SEED)
        return ChainKey(nextKey, self.index + 1)

    def getMessageKeys(self):
        inputKeyMaterial = self.getBaseMaterial(self.MESSAGE_KEY_SEED)
        cipherKey, macKey = HKDF().deriveSecrets(inputKeyMaterial, None, "WhisperMessageKeys")

        #return ( RootKey ( cipherKey ) , ChainKey( macKey, 0 ) )
        return MessageKeys(cipherKey, macKey, self.index)

    def getBaseMaterial(self, seed):
        return hmac.new(self.key, seed, hashlib.sha256).digest()


class RootKey:

    def __init__(self, key):
        self.key = key

    def getKeyBytes(self):
        return self.key

    def createChain(self, theirEphemeral, ourEphemeral, ephemeral=0):

        sharedKey = Curve().calculateAgreement(theirEphemeral, ourEphemeral.privateKey.publicKey, ephemeral)
        cipherKey, macKey = HKDF().deriveSecrets(sharedKey, self.key, "WhisperRatchet")

        return ( RootKey ( cipherKey ) , ChainKey( macKey, 0 ) )

class Curve:

    DJB_TYPE = 5

    # always DJB curve25519 keys
    def generateKeyPair(self, ephemeral):
        import receive_textsecure
        privateKey = keys.Private(ephemeral=ephemeral)
        publicKey = privateKey.get_public()
        return receive_textsecure.ECKeyPair(DjbECPublicKey(publicKey.public), DjbECPublicKey(privateKey.private))

    def calculateAgreement(self, publicKey, privateKey, ephemeral=0):
        key = keys.Private(secret=privateKey, ephemeral=ephemeral)
        return key.get_shared_key(keys.Public(publicKey), lambda x: x)

    def decodePoint(self, bytes, offset=0):
        type = bytes[0] # byte appears to be automatically converted to an integer??

        if type == self.DJB_TYPE:
            type = bytes[offset] & 0xFF
            if type != self.DJB_TYPE:
                print("InvalidKeyException Unknown key type: " + str(type) )
            keyBytes = bytes[offset+1:][:32]
            return DjbECPublicKey(keyBytes)
        else:
            print("InvalidKeyException Unknown key type: " + str(type) )

    def decodePrivatePoint(self, bytes):
        return DjbECPublicKey(bytes)

class IdentityKey:

    DJB_TYPE = b'\x05'

    def __init__(self, publicKey):
        self.publicKey = publicKey

    def serialize(self):
        return self.DJB_TYPE + self.publicKey

class DjbECPublicKey:

    DJB_TYPE = b'\x05'

    def __init__(self, publicKey):
        self.publicKey = publicKey

    def serialize(self):
        return self.DJB_TYPE + self.publicKey

class HKDF:

    # PRK = Pseudorandom Key
    # info = context and application specific information
    # OKM = Output Keying Material

    HASH_OUTPUT_SIZE = 32
    KEY_MATERIAL_SIZE = 64

    CIPHER_KEYS_OFFSET = 0
    MAC_KEYS_OFFSET = 32

    def deriveSecrets(self, inputKeyMaterial, salt, info):
        from hkdf import Hkdf

        if salt == None:
            salt = b"\x00" * self.HASH_OUTPUT_SIZE

        tshkdf = Hkdf(salt, inputKeyMaterial)
        okm = tshkdf.expand(info, self.KEY_MATERIAL_SIZE)

        cipherKey = okm[self.CIPHER_KEYS_OFFSET:self.HASH_OUTPUT_SIZE]
        macKey = okm[self.MAC_KEYS_OFFSET:self.MAC_KEYS_OFFSET + self.HASH_OUTPUT_SIZE]
        return ( cipherKey, macKey )


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
