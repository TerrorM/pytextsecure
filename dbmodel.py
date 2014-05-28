from sqlalchemy import Column, Integer, String, LargeBinary
from database import Base, init_db


class PreKey(Base):

    __tablename__ = "prekeys"

    id = Column(Integer, primary_key=True)
    keyId = Column(Integer)
    publicKey = Column(LargeBinary)
    privateKey = Column(LargeBinary)


class PreKeyIndex(Base):

    __tablename__ = "prekeyindex"

    nextKeyId = Column(Integer, primary_key=True)


class IdentityKey(Base):

    __tablename__ = "identitykeys"

    id = Column(Integer, primary_key=True)
    publicKey = Column(LargeBinary)
    privateKey = Column(LargeBinary)


class RecipientPreKey(Base):

    __tablename__ = "recipientprekeys"

    id = Column(Integer, primary_key=True)
    phoneNumber = Column(String)
    deviceId = Column(Integer)
    keyId = Column(Integer)
    publicKey = Column(LargeBinary)
    identityKey = Column(LargeBinary)
    registrationId = Column(Integer)


class ChatSession(Base):

    __tablename__ = "chatsession"

    #id = Column(Integer, primary_key=True)
    phoneNumber = Column(String, primary_key=True)
    session = Column(LargeBinary)

class Recipients(Base):

    __tablename__ = "recipients"

    #id = Column(Integer, primary_key=True)
    phoneNumber = Column(String, primary_key=True)
    identityKey = Column(LargeBinary)
    alias = Column(String)

class Config(Base):

    __tablename__ = "config"

    id = Column(Integer, primary_key=True)
    param = Column(String, unique=True)
    value = Column(LargeBinary)

    def __init__(self, param, value):
        self.param = param
        self.value = value

    def __repr__(self):
        return '<Config %r %r>' % (self.param, self.value)

init_db()
