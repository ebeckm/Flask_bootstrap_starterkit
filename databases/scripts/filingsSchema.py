from __future__ import division, print_function

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Date, Boolean
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, backref
from sqlalchemy import SmallInteger, Numeric
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class DailyFiling( Base ):
    __tablename__ = 'daily_index'
    id            = Column(Integer, primary_key=True)
    cik           = Column(Integer)
    company_name  = Column(String)
    form_type     = Column(String)
    date_filed    = Column(Date)
    file_name     = Column(String)

class Filer( Base ):
    __tablename__ = 'filers'
    id           = Column(Integer, primary_key=True)
    cik          = Column(Integer)
    filer_type   = Column(String)
    sector       = Column(String)
    industry     = Column(String)
    filer_names  = relationship('FilerName', backref='filer')


class FilerName( Base ):
    __tablename__ = 'filer_names'
    id          = Column(Integer, primary_key=True)
    cik         = Column(Integer, ForeignKey('filers.cik'))
    name        = Column(String)


class FormFour( Base ):
    __tablename__ = 'form_fours'
    id                         = Column(Integer, primary_key=True)
    file_name                  = Column(String)
    filing_date                = Column(Date)
    issuer_cik                 = Column(Integer, ForeignKey('filers.cik'))
    symbol                     = Column(String)
    owner_cik                  = Column(Integer, ForeignKey('filers.cik'))
    owner_name                 = Column(String)
    owner_title                = Column(String)
    owner_address_street1      = Column(String)
    owner_address_street2      = Column(String)
    owner_address_city         = Column(String)
    owner_address_state        = Column(String)
    owner_address_zip          = Column(String)
    owner_is_director          = Column(Boolean)
    owner_is_officer           = Column(Boolean)
    owner_is_ten_percent_owner = Column(Boolean)
    owner_is_other             = Column(Boolean)
    footnotes                  = Column(String)
    remarks                    = Column(String)
    transactions               = relationship('FormFourTransaction', backref='filing')


class FormFourTransaction( Base ):
    __tablename__ = 'form_four_transactions'
    id                         = Column(Integer, primary_key=True)
    form_id                    = Column(Integer, ForeignKey('form_fours.id'))
    derivative                 = Column(String)
    trans_number               = Column(Integer)
    trans_security_title       = Column(String)
    trans_date                 = Column(Date)
    trans_formtype             = Column(String)
    trans_code                 = Column(String)
    trans_equity_swap          = Column(Boolean)
    shares_change              = Column(Numeric)
    trans_price                = Column(Numeric)
    shares_owned_post          = Column(Numeric)
    ownership_nature           = Column(String)



if __name__ == "__main__":
    db_path = 'databases/'
    db_name = 'application.db'
    engine = create_engine('sqlite:///' + db_path + db_name, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

