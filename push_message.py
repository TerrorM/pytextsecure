from protos import IncomingPushMessageSignal_pb2, WhisperTextProtocol_pb2

import session_record

import serverapi

import receive_textsecure

def handleSendMms(text, alias):

    import keyutils
    number = keyutils.RecipientUtil().getNumberFromAlias(alias)

    deliver(text, number)

def deliver(text, number):

    messageProto = IncomingPushMessageSignal_pb2.PushMessageContent()
    messageProto.body = text

    #destination = '+18184316971'
    destination = number

    recipients = destination

    messages = getEncryptedMessages(recipients, messageProto)

    serverapi.submitMessage(messages)
    #sendMessage(messages)

def getEncryptedMessages(recipient, plaintext):
    messages = list()
    messages.append(getEncryptedMessage(recipient, plaintext))
    return OutgoingPushMessageList(recipient, '', messages)


import session_cipher
def getEncryptedMessage(recipient, plaintext):
    session = session_record.SessionRecord( recipient )
    # TODO also check hasSession
    if not session.hasSession() or session.sessionState.sessionStructure.needsRefresh:

        preKeyList = serverapi.getRecipientsPreKeyList(recipient)

        for preKey in preKeyList.keys:
            #device = PushAddress.create(recipient. number, preKey.deviceid)
            processor = receive_textsecure.KeyExchangeProcessor(recipient)

            # TODO check if the identity key is trusted
            #if processor.isTrusted(preKey):
            processor.processKeyExchangeMessage(preKey)

    cipher = session_cipher.SessionCipher(recipient)
    message = cipher.encrypt(plaintext)
    remoteRegistrationId = cipher.getRemoteRegistrationId()

    PREKEY_TYPE = 3
    WHISPER_TYPE = 2
    IncomingPushMessageSignal = IncomingPushMessageSignal_pb2.IncomingPushMessageSignal()

    if message.type == PREKEY_TYPE:
        return PushBody(IncomingPushMessageSignal.PREKEY_BUNDLE, remoteRegistrationId, message.serialized)
    elif message.type == WHISPER_TYPE:
        return PushBody(IncomingPushMessageSignal.CIPHERTEXT, remoteRegistrationId, message.serialized)
    else:
        raise "Unknown ciphertext type" + str(message.type)

class PushBody:
    def __init__(self, type, remoteRegistrationId, body):
        self.type = type
        self.remoteRegistrationId = remoteRegistrationId
        self.body = body

class OutgoingPushMessageList:
    def __init__(self, destination, relay, messages):
        self.destination = destination
        self.relay = relay
        self.messages = messages

