from protos import WhisperTextProtocol_pb2

import receive_textsecure
import ratcheting_session
import session_record

class SessionCipher:

    def __init__(self, recipient):
        if not session_record.SessionRecord(recipient).hasSession():
            raise("Attempt to initialize cipher for non-existing session.")
        self.recipient = recipient

    def encrypt(self, paddedMessage):
        sessionRecord = self.getSessionRecord()
        sessionState = sessionRecord.sessionState
        chainKey = sessionState.getSenderChainKey()
        messageKeys = chainKey.getMessageKeys()
        senderEphemeral = sessionState.getSenderEphemeral()
        previousCounter = sessionState.sessionStructure.previousCounter

        ciphertextBody = self.getCiphertext(messageKeys, paddedMessage.SerializeToString())
        ciphertextMessage = receive_textsecure.WhisperMessage(macKey=messageKeys.macKey,
                                                              senderEphemeral=senderEphemeral,
                                                              counter=chainKey.index,
                                                              previousCounter=previousCounter,
                                                              ciphertext=ciphertextBody)

        if sessionState.hasPendingPreKey():
            pendingPreKey = sessionState.getPendingPreKey()
            localRegistrationId = sessionState.sessionStructure.localRegistrationId

            ciphertextMessage = receive_textsecure.PreKeyWhisperMessage(registrationId=localRegistrationId,
                                                                        preKeyId=pendingPreKey[0],
                                                                        baseKey=pendingPreKey[1],
                                                                        identityKey=sessionState.sessionStructure.localIdentityPublic,
                                                                        message=ciphertextMessage)

        sessionState.setSenderChainKey(chainKey.getNextChainKey())
        sessionRecord.save()

        return ciphertextMessage


    def getSessionRecord(self):
        return session_record.SessionRecord(self.recipient)

    def decrypt(self, decodedMessage):
        sessionRecord = self.getSessionRecord()
        sessionState = sessionRecord.sessionState
        #previousStates = sessionRecord.getPreviousSessions()

        plaintext = self._decrypt(sessionState, decodedMessage)
        sessionRecord.save()
        return plaintext

    def _decrypt(self, sessionState, decodedMessage):

        import receive_textsecure
        if not sessionState.sessionStructure.senderChain:
            print('Uninitialized session!')

        ciphertextMessage = receive_textsecure.WhisperMessage(serialized=decodedMessage)

        theirEphemeral = ciphertextMessage.senderEphemeral
        counter = ciphertextMessage.counter
        chainKey = self.getOrCreateChainKey(sessionState, theirEphemeral)
        messageKeys = self.getOrCreateMessageKeys(sessionState, theirEphemeral,
                                             chainKey, counter)

        # TODO add methods?
        ciphertextMessage.verifyMac(messageKeys.getMacKey())

        sessionState.sessionStructure.ClearField("pendingPreKey")
        plaintext = self.getPlaintext(messageKeys, ciphertextMessage.ciphertext)

        #sessionState.sessionStructure.clearPendingPreKey();

        return plaintext

    def getRemoteRegistrationId(self):
        sessionRecord = self.getSessionRecord()
        return sessionRecord.sessionState.getRemoteRegistrationId()

    def getOrCreateChainKey(self, sessionState, theirEphemeral):

        if sessionState.hasReceiverChain(theirEphemeral):
            return sessionState.getReceiverChainKey(theirEphemeral)

        rootKey = sessionState.getRootKey()
        ourEphemeral = sessionState.getSenderEphemeralPair()
        receiverChain = rootKey.createChain(theirEphemeral.publicKey, ourEphemeral)
        ourNewEphemeral = ratcheting_session.Curve().generateKeyPair( True )
        senderChain = receiverChain[0].createChain(theirEphemeral.publicKey, ourNewEphemeral)

        sessionState.setRootKey(senderChain[0])
        sessionState.addReceiverChain(theirEphemeral, receiverChain[1])
        if sessionState.getSenderChainKey().getIndex() - 1 != -1:
            sessionState.setPreviousCounter(sessionState.getSenderChainKey().getIndex()-1)
        sessionState.setSenderChain(ourNewEphemeral, senderChain[1])

        return receiverChain[1]

    def getOrCreateMessageKeys(self, sessionState, theirEphemeral, chainKey, counter):
        if chainKey.getIndex() > counter:
            if sessionState.hasMessageKeys(theirEphemeral, counter):
                return sessionState.removeMessageKeys(theirEphemeral,counter)
            raise "Duplicate Message Exception Received Message with old counter"

        if chainKey.getIndex() - counter > 2000:
            raise "Over 2000 messages into the future!"

        while chainKey.getIndex() < counter:
            messageKeys = chainKey.getMessageKeys()
            sessionState.setMessageKeys(theirEphemeral, messageKeys)
            chainKey = chainKey.getNextChainKey()

        sessionState.setReceiverChainKey(theirEphemeral, chainKey.getNextChainKey())
        return chainKey.getMessageKeys()

    def getCiphertext(self, messageKeys, plaintext):
        import receive_textsecure
        return receive_textsecure.encryptAESCTR(plaintext, messageKeys.cipherKey, messageKeys.counter)

    def getPlaintext(self, messageKeys, ciphertext):
        import receive_textsecure
        return receive_textsecure.decryptAESCTR(ciphertext, messageKeys.cipherKey, messageKeys.counter)



