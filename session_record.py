from protos import LocalStorageProtocol_pb2
from keyutils import IdentityKeyUtil, ChatSessionUtil

import ratcheting_session

class SessionRecord:

    def __init__(self, recipientId, deviceId = 1):
        self.recipientId = recipientId
        self.chatSessionUtil = ChatSessionUtil()
        self.loadData()

    #def getSessionState(self):
    #    return self.sessionState

    def save(self):
        self.chatSessionUtil.saveChatSession(self.recipientId, self.sessionState.sessionStructure.SerializeToString())

    def loadData(self):
        #print('in session record recipientId:' + str(self.recipientId))
        localStorageProto = ChatSessionUtil().getChatSession(self.recipientId)

        sessionStructure = LocalStorageProtocol_pb2.SessionStructure()

        if localStorageProto:
            sessionStructure.ParseFromString(localStorageProto)

        self.sessionState = SessionState(sessionStructure)

    def hasSession(self):
        return ( self.chatSessionUtil.hasSession(self.recipientId) and SessionRecord(self.recipientId).sessionState.hasSenderChain() )

    def deleteAll(self):

        self.chatSessionUtil.deleteChatSession(self.recipientId)

        #for device in devices:
        #self.chatSessionUtil.getChatSession(number)

class SessionState:

    def __init__(self, sessionStructure):
        self.sessionStructure = sessionStructure

    def getStructure(self):
        self.sessionStructure;

    def getNeedsRefresh(self):
        return self.sessionStructure.needsRefresh

    def setNeedsRefresh(self, needsRefresh):
        self.sessionStructure.needsRefresh = needsRefresh

    def setSessionVersion(self, version):
        self.sessionStructure.version = version

    def getSessionVersion(self):
        return self.sessionStructure.version

    def setRemoteIdentityKey(self, identityKey):
        self.sessionStructure.remoteIdentityPublic = identityKey.serialize()

    def setLocalIdentityKey(self, identityKey):
        self.sessionStructure.localIdentityPublic = identityKey

    def getRemoteIdentityKey(self):
        if not self.sessionStructure.hasRemoteIdentityPublic():
            return None

        return IdentityKey(self.sessionStructure.getRemoteIdentityPublic().toByteArray(), 0)

    def getLocalIdentityKey(self):
        return IdentityKey(self.sessionStructure.getLocalIdentityPublic().toByteArray(), 0)


    def getPreviousCounter(self):
        return sessionStructure.getPreviousCounter()

    def setPreviousCounter(self, previousCounter):
        self.sessionStructure.previousCounter = previousCounter

    def getRootKey(self):
        return ratcheting_session.RootKey(self.sessionStructure.rootKey)

    def setRootKey(self, rootKey):
        self.sessionStructure.rootKey = rootKey.key

    def getSenderEphemeral(self):
        return ratcheting_session.Curve().decodePoint(self.sessionStructure.senderChain.senderEphemeral, 0);

    def getSenderEphemeralPair(self):
        import receive_textsecure
        publicKey = self.getSenderEphemeral()
        privateKey = ratcheting_session.Curve().decodePrivatePoint(self.sessionStructure.senderChain.senderEphemeralPrivate);
        return receive_textsecure.ECKeyPair(publicKey, privateKey)

    def hasReceiverChain(self, senderEphemeral):
        return self.getReceiverChain(senderEphemeral) != None

    def hasSenderChain(self):
        return self.sessionStructure.senderChain != None

    def getReceiverChain(self, senderEphemeral):
        receiverChains = self.sessionStructure.receiverChains
        index          = 0

        for receiverChain in receiverChains:
            chainSenderEphemeral = ratcheting_session.Curve().decodePoint(receiverChain.senderEphemeral, 0)

            if chainSenderEphemeral.publicKey == senderEphemeral.publicKey:
                return ( receiverChain, index )

            index += 1

        return None

    def getReceiverChainKey(self, senderEphemeral):
        receiverChainAndIndex = self.getReceiverChain(senderEphemeral)
        receiverChain = receiverChainAndIndex[0]

        if receiverChain == None:
            return None

        return ratcheting_session.ChainKey(receiverChain.chainKey.key, receiverChain.chainKey.index)

    def addReceiverChain(self, senderEphemeral, chainKey):
        chainKeyStructure = LocalStorageProtocol_pb2.SessionStructure.Chain.ChainKey()
        chainKeyStructure.key = chainKey.key
        chainKeyStructure.index = chainKey.index

        chain = LocalStorageProtocol_pb2.SessionStructure.Chain()
        chain.chainKey.CopyFrom(chainKeyStructure)
        chain.senderEphemeral = senderEphemeral.serialize()

        receiverChains = self.sessionStructure.receiverChains.add()
        receiverChains.CopyFrom(chain)

        if len(self.sessionStructure.receiverChains) > 5:
            del self.sessionStructure.receiverChains[0]


    def setSenderChain(self, senderEphemeralPair, chainKey):
        chainKeyStructure = LocalStorageProtocol_pb2.SessionStructure.Chain.ChainKey()
        chainKeyStructure.key = chainKey.key
        chainKeyStructure.index = chainKey.index

        senderChain = LocalStorageProtocol_pb2.SessionStructure.Chain()
        senderChain.senderEphemeral = senderEphemeralPair.publicKey.serialize()
        senderChain.senderEphemeralPrivate = senderEphemeralPair.privateKey.publicKey
        senderChain.chainKey.CopyFrom(chainKeyStructure)

        self.sessionStructure.senderChain.CopyFrom(senderChain)


    def getSenderChainKey(self):
        chainKeyStructure = self.sessionStructure.senderChain.chainKey
        return ratcheting_session.ChainKey(chainKeyStructure.key, chainKeyStructure.index);

    def setSenderChainKey(self, nextChainKey):
        chainKey = LocalStorageProtocol_pb2.SessionStructure.Chain.ChainKey()
        chainKey.key = nextChainKey.key
        chainKey.index = nextChainKey.index

        #chain = LocalStorageProtocol_pb2.SessionStructure.senderChain()
        #chain.chainKey = chainKey

        self.sessionStructure.senderChain.chainKey.CopyFrom(chainKey)

    def hasMessageKeys(self, senderEphemeral, counter):
        chainAndIndex = self.getReceiverChain(senderEphemeral)
        chain = chainAndIndex[0]

        if chain == None:
            return False

        messageKeys = chain.messageKeys

        for messageKey in messageKeys:
            if messageKey.index == counter:
                return True

        return False

    def removeMessageKeys(self, senderEphemeral, counter):
        chainAndIndex = self.getReceiverChain(senderEphemeral)
        chain = chainAndIndex[0]

        if chain == None:
            return None

        messageKeys = chain.messageKeys
        result = None

        for messageKey in messageKeys:

            if messageKey.index == counter:
                result = ratcheting_session.MessageKeys(messageKey.cipherKey, messageKey.macKey, messageKey.index);

                break

        updatedChain = chain.ClearField("messageKeys")
        chain.messageKeys.extend(messageKeys)

        #self.sessionStructure.ClearField("receiverChains")
        #self.sessionStructure.receiverChains.extend(updatedChain)

        return result

    def setMessageKeys(self, senderEphemeral, messageKeys):
        chainAndIndex = self.getReceiverChain(senderEphemeral)
        chain = chainAndIndex[0]
        messageKeyStructure = LocalStorageProtocol_pb2.SessionStructure.Chain.MessageKey()
        messageKeyStructure.cipherKey = messageKeys.cipherKey
        messageKeyStructure.macKey = messageKeys.macKey
        messageKeyStructure.index = messageKeys.counter

        messageKeys = chain.messageKeys.add()
        messageKeys.CopyFrom(messageKeyStructure)

        addChain = self.sessionStructure.receiverChains.add()
        addChain.CopyFrom(chain)



    def setReceiverChainKey(self, senderEphemeral, chainKey):
        chainAndIndex = self.getReceiverChain(senderEphemeral)
        chain = chainAndIndex[0]
        chainKeyStructure = LocalStorageProtocol_pb2.SessionStructure.Chain.ChainKey()
        chainKeyStructure.key = chainKey.key
        chainKeyStructure.index = chainKey.index

        chain.chainKey.CopyFrom(chainKeyStructure)

        #self.sessionStructure.receiverChains(chainAndIndex[1], updatedChain)

    def setPendingKeyExchange(self, sequence, ourBaseKey, ourEpehemeralKey, ourIdentityKey):
        structure = LocalStorageProtocol_pb2.SessionStructure.PendingKeyExchange()
        structure.sequence = sequence
        structure.localBaseKey.copyFrom(ourBaseKey.getPublicKey().serialize())
        structure.localBaseKeyPrivate.copyFrom(ourBaseKey.getPrivateKey().serialize())
        structure.localEphemeralKey.copyFrom(ourEpehemeralKey.getPublicKey().serialize())
        structure.localEphemeralKeyPrivate.copyFrom(ourEpehemeralKey.getPrivateKey().serialize())
        structure.localIdentityKey.copyFrom(ourIdentityKey.getPublicKey().serialize())
        structure.localIdentityKeyPrivate.copyFrom(ourIdentityKey.getPrivateKey().serialize())

        self.sessionStructure.pendingKeyExchange = structure

    def getPendingKeyExchangeSequence(self):
        return self.sessionStructure.pendingKeyExchange.sequence

    def getPendingKeyExchangeBaseKey(self):
        publicKey   = Curve.decodePoint(sessionStructure.getPendingKeyExchange()
                                                                .getLocalBaseKey().toByteArray(), 0);

        privateKey = Curve.decodePrivatePoint(sessionStructure.getPendingKeyExchange()
                                                                       .getLocalBaseKeyPrivate()
                                                                       .toByteArray());

        return (publicKey, privateKey)


    def getPendingKeyExchangeEphemeralKey(self):
        publicKey   = Curve.decodePoint(sessionStructure.getPendingKeyExchange()
                                                                .getLocalEphemeralKey().toByteArray(), 0);

        privateKey = Curve.decodePrivatePoint(sessionStructure.getPendingKeyExchange()
                                                                       .getLocalEphemeralKeyPrivate()
                                                                       .toByteArray());

        return (publicKey, privateKey)

    def getPendingKeyExchangeIdentityKey(self):
        publicKey   = Curve.decodePoint(sessionStructure.getPendingKeyExchange()
                                                                .getLocalIdentityKey().toByteArray(), 0);

        privateKey = Curve.decodePrivatePoint(sessionStructure.getPendingKeyExchange()
                                                                       .getLocalIdentityKeyPrivate()
                                                                       .toByteArray());

        return (publicKey, privateKey)

    def hasPendingKeyExchange(self):
        return self.sessionStructure.pendingKeyExchange

    def setPendingPreKey(self, preKeyId, baseKey):
        self.sessionStructure.pendingPreKey.preKeyId = preKeyId
        self.sessionStructure.pendingPreKey.baseKey = baseKey.serialize()

    def hasPendingPreKey(self):
        return (len(self.sessionStructure.pendingPreKey.baseKey) != 0)


    def getPendingPreKey(self):
        return ( self.sessionStructure.pendingPreKey.preKeyId , ratcheting_session.Curve().decodePoint(self.sessionStructure.pendingPreKey.baseKey)  )

    def clearPendingPreKey(self):
        self.sessionStructure.clearPendingPreKey()

    def setRemoteRegistrationId(self, registrationId):
        self.sessionStructure.remoteRegistrationId = registrationId

    def getRemoteRegistrationId(self):
        return self.sessionStructure.remoteRegistrationId

    def setLocalRegistrationId(self, registrationId):
        self.sessionStructure.localRegistrationId = registrationId

    def getLocalRegistrationId(self):
        return self.sessionStructure.localRegistrationId

    def serialize(self):
        return self.sessionStructure
