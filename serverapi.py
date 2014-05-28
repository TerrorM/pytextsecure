import requests
import os
from random import SystemRandom
import base64
import json
import hashlib
import time
import ssl

from keyutils import PreKeyUtil, IdentityKeyUtil, RecipientPreKeyUtil

import config

class ServerError(Exception):
    def __init__(self , code, message):
        self.code = code
        self.message = message
    def __str__(self):
        return self.message

headers = {'Content-type': 'application/json'}

HOST = 'textsecure-service.whispersystems.org'
URL_BASE = "https://" + HOST
#URL_BASE = "http://127.0.0.1:8080"

# bugs.python.org/issue18293
# Monkey patching certificate pinning
with open('certs/' + HOST + '.der', 'rb') as f:
    valid_cert = f.read()

def cert_verify(self, conn, url, verify, cert):
    # skip built in certificate verification for our host
    if not conn.host == HOST:
        orig_cert_verify(self, conn, url, verify, cert)
    return

def do_handshake(self, block=False):
    orig_do_handshake(self, block=False)
    if self.server_hostname == HOST:
        # Ensure certificate is the pinned one
        if self.getpeercert(True) != valid_cert:
            raise ssl.SSLError('Did not match pinned certificate')

orig_do_handshake = ssl.SSLSocket.do_handshake
ssl.SSLSocket.do_handshake = do_handshake

orig_cert_verify = requests.adapters.HTTPAdapter.cert_verify
requests.adapters.HTTPAdapter.cert_verify = cert_verify


def requestVerificationCode(phone_number):
    r = requests.get( URL_BASE + '/v1/accounts/sms/code/' + phone_number)
    print(r.status_code)
    if r.status_code in (400 , 404):
        raise ServerError(r.status_code, 'The phone number was badly formatted.')
    elif r.status_code == 413:
        raise ServerError(r.status_code, 'Rate limit exceeded.')
    elif r.status_code == 415:
        raise ServerError(r.status_code, 'Invalid transport.')
    elif r.status_code == 200:
        return

def confirmVerificationCode(phone_number, token):
    password = base64.b64encode(os.urandom(16))[:-2].decode('utf-8')

    signalingKey = os.urandom(52)
    registrationId = SystemRandom().randint(1, 16380 + 1)

    payload = {
        "signalingKey" : base64.b64encode(signalingKey).decode('utf-8'),
        "supportsSms" : False,
        "fetchesMessages" : False,
        "registrationId" : registrationId
    }

    r = requests.put( URL_BASE + '/v1/accounts/code/' + token,
                     headers=headers,
                     auth=(phone_number, password),
                     data=json.dumps(payload) )

    if r.status_code in (400 , 404):
        raise ServerError(r.status_code, 'The token was badly formatted.')
    elif r.status_code == 401:
        raise ServerError(r.status_code, 'Badly formatted basic auth.')
    elif r.status_code == 403:
        raise ServerError(r.status_code, 'Verification code was incorrect.')
    elif r.status_code == 413:
        raise ServerError(r.status_code, 'Rate limit exceeded.')
    elif r.status_code == 417:
        raise ServerError(r.status_code, 'Number already registered.')
    elif r.status_code in (200, 204):
        config.setConfigOption('phone_number', phone_number)
        config.setConfigOption('password', password)
        config.setConfigOption('signalingKey', signalingKey)
        config.setConfigOption('registrationId', str(registrationId))
        return

def registerGCMid():

    regid = config.getConfigOption('gcmregid').decode('utf-8')
    phone_number = config.getConfigOption('phone_number').decode('utf-8')
    password = config.getConfigOption('password').decode('utf-8')

    data = { 'gcmRegistrationId' : regid }

    r = requests.put( URL_BASE + '/v1/accounts/gcm/',
                     headers=headers,
                     auth=(phone_number, password),
                     data=json.dumps(data)
                    )

    if r.status_code == 401:
        raise ServerError(r.status_code, 'Invalid authentication credentials.')
    elif r.status_code == 415:
        raise ServerError(r.status_code, 'Badly formatted JSON.')
    elif r.status_code in (200, 204):
        return r.content

def registerPreKeys():

    #get auth data
    phone_number = config.getConfigOption('phone_number').decode('utf-8')
    password = config.getConfigOption('password').decode('utf-8')

    #generate keys
    PreKeyUtil().generatePreKeys()
    PreKeyUtil().generateLastResortKey()
    IdentityKeyUtil().generateIdentityKey()

    records = PreKeyUtil().getPreKeys()

    preKeys = list()
    for preKey in records:
        preKeys.append(
            {
                'keyId' : preKey.keyId,
                'publicKey' : base64.b64encode(b'\x05' + preKey.publicKey).decode("utf-8"),
                'identityKey' : base64.b64encode(b'\x05' + IdentityKeyUtil().getIdentityKey()).decode("utf-8")
            }
        )

    lastResortKey = PreKeyUtil().getLastResortKey()
    lastResortKeyDict = {
                'keyId' : lastResortKey.keyId,
                'publicKey' : base64.b64encode(b'\x05' + lastResortKey.publicKey).decode("utf-8"),
                'identityKey' : base64.b64encode(b'\x05' + IdentityKeyUtil().getIdentityKey()).decode("utf-8")
            }

    data = { 'lastResortKey' : lastResortKeyDict , 'keys' : preKeys}

    r = requests.put( URL_BASE + '/v1/keys/',
                     headers=headers,
                     auth=(phone_number, password),
                     data=json.dumps(data) )

    if r.status_code == 401:
        raise ServerError(r.status_code, 'Invalid authentication credentials.')
    elif r.status_code == 415:
        raise ServerError(r.status_code, 'Badly formatted JSON.')
    elif r.status_code in (200, 204):
        return

def getContactIntersection(contacts):

    #get auth data
    phone_number = config.getConfigOption('phone_number').decode('utf-8')
    password = config.getConfigOption('password').decode('utf-8')

    contacts = [ '+611231231234', '+611231231235' ]
    tokens = []
    for contact in contacts:
        thash = hashlib.sha1(contact.encode('utf-8')).digest()[0:10]
        tokens.append(base64.b64encode(thash).decode('utf-8').rstrip('='))

    data = { 'contacts' : tokens }

    r = requests.put( URL_BASE + '/v1/directory/tokens',
                     headers=headers,
                     auth=(phone_number, password),
                     data=json.dumps(data) )

    if r.status_code == 400:
        raise ServerError(r.status_code, 'Badly formatted tokens.')
    if r.status_code == 401:
        raise ServerError(r.status_code, 'Invalid authentication credentials.')
    elif r.status_code == 415:
        raise ServerError(r.status_code, 'Badly formatted JSON.')
    elif r.status_code in (200, 204):
        print(r.content)
        return r.content

def getRecipientsPreKeyList(number):

    print('Getting recipients prekey')

    #get auth data
    phone_number = config.getConfigOption('phone_number').decode('utf-8')
    password = config.getConfigOption('password').decode('utf-8')

    r = requests.get(URL_BASE + '/v1/keys/' + number + '/*',
                     headers=headers,
                     auth=(phone_number, password))

    if r.status_code == 401:
        raise ServerError(r.status_code, 'Invalid authentication credentials.')
    elif r.status_code == 404:
        raise ServerError(r.status_code, 'Unknown/unregistered number.')
    elif r.status_code == 413:
        raise ServerError(r.status_code, 'Rate limit exceeded.')
    elif r.status_code in (200, 204):

        RecipientPreKeyUtil().saveRecipientPreKey(number, json.loads(r.content.decode('utf-8')))

        preKeyList = createPreKeyListFromJson(r.content)

        return preKeyList

import ratcheting_session
def createPreKeyListFromJson(serialized):
    data = json.loads(serialized.decode('utf-8'))

    keys = list()
    for key in data['keys']:
        publicKey = ratcheting_session.Curve().decodePoint( base64.b64decode( key['publicKey'] ) )
        identityKey = ratcheting_session.Curve().decodePoint( base64.b64decode( key['identityKey'] ) )

        keys.append( PreKeyEntity( key['deviceId'], key['keyId'], publicKey, identityKey, key['registrationId'] )  )

    preKeyList = PreKeyList('', keys)

    return preKeyList

class PreKeyList:

    def __init__(self, lastResortKey, keys):
        self.keys = keys
        self.lastResortKey = lastResortKey

class PreKeyEntity:

    def __init__(self, deviceId, keyId, publicKey, identityKey, registrationId):
        self.deviceId = deviceId
        self.keyId = keyId
        self.publicKey = publicKey
        self.identityKey = identityKey
        self.registrationId = registrationId


def submitMessage(messages):
    #get auth data
    phone_number = config.getConfigOption('phone_number').decode('utf-8')
    password = config.getConfigOption('password').decode('utf-8')

    for message in messages.messages:

        data = {
                'messages': [{
                       'type': message.type,
                       'destinationDeviceId': 1,
                       'destinationRegistrationId': message.remoteRegistrationId,
                       'body': base64.b64encode(message.body).decode('utf-8'),
                       'timestamp': int(time.time())
                      }]
        }

        r = requests.put( URL_BASE + '/v1/messages/' + messages.destination,
                         headers=headers,
                         auth=(phone_number, password),
                         data=json.dumps(data) )

    if r.status_code == 401:
        raise ServerError(r.status_code, 'Invalid authentication credentials.')
    elif r.status_code == 409:
        #this error returns data
        raise ServerError(r.status_code, 'Mismatched devices.')
    elif r.status_code == 410:
        #this error returns data
        raise ServerError(r.status_code, 'Stale devices.')
    elif r.status_code == 413:
        raise ServerError(r.status_code, 'Rate limit exceeded.')
    elif r.status_code == 415:
        raise ServerError(r.status_code, 'Badly formatted JSON.')
    elif r.status_code in (200, 204):
        return r.content

