from sqlalchemy import exists

from database import session; session=session #fix the IDE
from dbmodel import Config; Config=Config

def existsConfigOption(param):
    if session.query(exists().where(Config.param==param)).scalar():
        return True
    else:
        return False


def getConfigOption(param):
    return session.query(Config).filter(Config.param==param).first().value

def getConfigOptionPair(param):
    return session.query(Config).filter(Config.param==param).first()

def setConfigOption(param,value):
    if type(value) == str:
        value = value.encode()

    if session.query(exists().where(Config.param==param)).scalar():
        confobj = session.query(Config).filter(Config.param==param).first()
        confobj.value = value
    else:
        session.add(Config(param, value))
    session.commit()

session.commit()


'''class Config():

    def __getitem__(self, param):
        return getConfigOption(param)


c = Config
p = c['foobar']'''