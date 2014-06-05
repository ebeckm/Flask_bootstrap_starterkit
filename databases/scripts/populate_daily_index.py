from __future__ import division, print_function

import urllib2
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from dateutil import parser as date_parser
import re
import StringIO, gzip, codecs

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Date, Boolean
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from filingsSchema import *


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

db_path = 'databases/'
db_name = 'application.db'
engine = create_engine('sqlite:///' + db_path + db_name, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

def get_filings_list_from_sec_ftp(date_str,quarter,year,zipped=False,current=False):
    ftp_url = 'ftp://ftp.sec.gov/edgar/daily-index/'
    if not current:
        ftp_url = ftp_url+str(year)+'/QTR'+str(qtr)+'/'
    ftp_url = ftp_url + 'master.' + date_str + '.idx'
    if zipped:
        ftp_url = ftp_url+'.gz'
    try:
        page = urllib2.urlopen(ftp_url)
    except:
        print('page does not exist at %s' % ftp_url)
        return[]
    if zipped:
        page = StringIO.StringIO(page.read())
        page = gzip.GzipFile(fileobj=page)
        lines = page.readlines()
        lines = [codecs.decode(l,'latin-1') for l in lines]
    else:
        lines = BeautifulSoup(page).get_text().split('\n')
    headers = ['cik','company_name','form_type','date_filed','file_name']
    flag = True
    for line in lines:
        if flag:
            if re.match(r'[-]+',line):
                flag=False
            continue
        if not line.strip():
            continue
        line = dict(zip(headers,[col.strip() for col in line.split('|')]))
        line['date_filed'] = date_parser.parse(line['date_filed'])
        line['cik'] = int(line['cik'])
        session.add(DailyFiling(
            cik = line['cik'],
            company_name = line['company_name'],
            form_type = line['form_type'],
            date_filed = line['date_filed'],
            file_name = line['file_name']
            ))
    session.commit()

def get_qtr_from_date(day):
    if day.month<=3:
        return 1
    elif day.month<=6:
        return 2
    elif day.month<=9:
        return 3
    else:
        return 4


def get_date_string(day):
    if day.year==1994:
        return day.strftime('%m%d%y')
    elif day.year<1998:
        return day.strftime('%y%m%d')
    else:
        return day.strftime('%Y%m%d')


if __name__ == "__main__":
    s_date = date(2012,1,1)
    e_date = date(2012,1,4)
    for interval in range((e_date-s_date).days):
        day = s_date + timedelta(days=interval)
        qtr = get_qtr_from_date(day)
        year = day.year
        d_string = get_date_string(day)
        print('Adding filings from day %s' % str(day))
        if day < date(2011,7,1):
            get_filings_list_from_sec_ftp(d_string,qtr,year)
        elif day <= date(2014,1,1):
            get_filings_list_from_sec_ftp(d_string,qtr,year,zipped=True)
        elif day <= date(2014,3,31):
            get_filings_list_from_sec_ftp(d_string,qtr,year)
        else:
            get_filings_list_from_sec_ftp(d_string,qtr,year,current=True)
