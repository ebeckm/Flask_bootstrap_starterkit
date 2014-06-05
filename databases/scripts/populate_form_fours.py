from __future__ import division, print_function

import urllib2
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from dateutil import parser as date_parser
import re, time, sys
import StringIO, gzip, codecs

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Date, Boolean
from sqlalchemy.sql import and_, or_
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy import event
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

def list_grouper(seq, size, fillvalue=''):
    '''
    Chunk a list into pieces of size n, fill last chunk with '' up to size n
    '''
    return (seq[pos:pos + size] for pos in xrange(0, len(seq), size))


def patient_urlopen(url):
    response = urllib2.urlopen(url)
    html = ''
    while True:
        data = response.read()
        if not data: break
        html += data
    return html


def get_fulltext_forms_from_sec_ftp(forms,retry_attempts=1):
    '''Given a list dict extracted from sec daily filings file
    Print download forms from the sec database
    '''
    url_base = 'http://www.sec.gov/Archives/'
    filings = []
    for form in forms:
        for i in range(0,retry_attempts):
            try:
                html =  patient_urlopen(url_base + form['file_name'])
                filings.append(dict(form.items()+{'fulltext':html}.items()))
            except urllib2.URLError, e:
                print('URLError, perhaps page is missing at %s' % url_base + form['file_name'])
                print(e)
                time.sleep(5)
                continue
            except socket.timeout:
                print('urllib2 timeout when trying to fetch %s' % url_base + form['file_name'])
                time.sleep(5)
                continue
            break
    return filings


def extract_filer_info_from_fulltext(filings):
    for idx,filing in enumerate(filings):
        soup = BeautifulSoup(filing['fulltext'],'lxml')
        soup = soup.find('sec-header')
        soup = soup.get_text()
        header = {'ITEM INFORMATION':[]}
        sub_head = {'flag':0}
        for line in soup.split('\n'):
            if ':' not in line:
                sub_head = {'flag':0}
                continue
            k = line.split(':')[0].strip()
            v = line.split(':')[1:]
            v = u''.join(list(v)).strip()
            if v == '':
                sub_head['flag'] = 1
                sub_head['value'] = k
                header[k] = {}
            elif sub_head['flag']:
                header[sub_head['value']][k] = v
            elif k == 'ITEM INFORMATION':
                header[k].append(v)
            else:
                header[k] = v
        filings[idx] = dict(filing.items() + header.items())
    return filings


def soup_to_text_or_none(soup, key, func = lambda s: s, value=False):
    '''
    Work Streams
    ------------
    Consider replacing the get_text call with a loop that joins text across child nodes
    using a join character such as '|'
    '''
    if soup.find(key):
        if value and soup.find(key).find('value'):
            return func(soup.find(key).find('value').get_text().strip())
        elif not value:
            return func(soup.find(key).get_text().strip())
    else:
        return None


def clean_from_fulltext(forms):
    '''Given a list of dicts containing form four information including
    a fulltext version of the filing, return cleaned data and keys
    '''
    clean_forms = []
    stton = soup_to_text_or_none
    def ad_sign(soup):
        ad = stton(soup,'transactionacquireddisposedcode',value=True)
        return 1 if ad=='A' else -1
    for form in forms:
        soup = BeautifulSoup(form['fulltext'])
        filing = {
            'file_name'                  : form['file_name'],
            'filing_date'                : form['date_filed'],
            'issuer_cik'                 : stton(soup,'issuercik',int),
            'issuer_symbol'              : stton(soup,'issuertradingsymbol'),
            'issuer_name'                : stton(soup,'issuername'),
            'owner_cik'                  : stton(soup,'rptownercik',int),
            'owner_name'                 : stton(soup,'rptownername'),
            'owner_title'                : stton(soup,'officertitle'),
            'owner_address_street1'      : stton(soup,'rptownerstreet1'),
            'owner_address_street2'      : stton(soup,'rptownerstreet2'),
            'owner_address_city'         : stton(soup,'rptownercity'),
            'owner_address_state'        : stton(soup,'rptownerstate'),
            'owner_address_zip'          : stton(soup,'rptownerzipcode'),
            'owner_is_director'          : stton(soup,'isdirector', bool),
            'owner_is_officer'           : stton(soup,'isofficer', bool),
            'owner_is_ten_percent_owner' : stton(soup,'istenpercentowner', bool),
            'owner_is_other'             : stton(soup,'isother', bool),
            'footnotes'                  : stton(soup,'footnotes'),
            'remarks'                    : stton(soup,'remarks'),
            'transactions'               : []
        }
        tn  = 0
        for ndt in soup.find_all('nonderivativetransaction'):
            tn += 1
            transaction = {
                'derivative'             : False,
                'trans_number'           : tn,
                'trans_security_title'   : stton(ndt,'securitytitle',bool,True),
                'trans_date'             : stton(ndt,'transactiondate',\
                                                lambda xx : date_parser.parse(xx).date(),True),
                'trans_formtype'         : stton(ndt,'transactionformtype'),
                'trans_code'             : stton(ndt,'transactioncode'),
                'trans_equity_swap'      : stton(ndt,'equityswapinvolved',bool),
                'shares_change'          : stton(ndt,'transactionshares',
                                                 lambda x : ad_sign(ndt)*float(x),True),
                'trans_price'            : stton(ndt,'transactionpricepershare',float,True),
                'shares_owned_post'      : stton(ndt,'sharesownedfollowingtransaction', value=True),
                'ownership_nature'       : stton(ndt,'directorindirectownership')
            }
            filing['transactions'].append(transaction)
        tn = 0
        for dt in soup.find_all('derivativetransaction'):
            tn += 1
            transaction = {
                'derivative'             : True,
                'trans_number'           : tn,
                'trans_security_title'   : stton(dt,'securitytitle',bool,True),
                'trans_date'             : stton(dt,'transactiondate',\
                                                lambda xx : date_parser.parse(xx).date(),True),
                'trans_formtype'         : stton(dt,'transactionformtype'),
                'trans_code'             : stton(dt,'transactioncode'),
                'trans_equity_swap'      : stton(dt,'equityswapinvolved',bool),
                'shares_change'          : stton(dt,'transactionshares',
                                                 lambda x : ad_sign(dt)*float(x),True),
                'trans_price'            : stton(dt,'transactionpricepershare',float,True),
                'shares_owned_post'      : stton(dt,'sharesownedfollowingtransaction', value=True),
                'ownership_nature'       : stton(dt,'directorindirectownership')
            }
            filing['transactions'].append(transaction)
        clean_forms.append(filing)
    return clean_forms


def add_filers_listdict(session, filer_list, filer_type='issuer',cik_key='cik',sector_key='sector', industry_key='industry'):
    '''
    Given a list of filers and an active session for each filer in filer_list if filer does not already exist add filer to database.
    '''
    if type(filer_list) == dict: filer_list = [filer_list]
    for filer in filer_list:
        assert cik_key in filer
        sector = filer[sector_key] if sector_key in filer else None
        industry = filer[industry_key] if industry_key in filer else None
        filer_cik_exists = session.query(
            Filer
        ).\
        filter(
            Filer.cik==filer[cik_key]
        ).count()
        if not filer_cik_exists:
            session.add(
                Filer(
                    cik        = filer[cik_key],
                    filer_type = filer_type,
                    sector     = sector,
                    industry   = industry
                )
            )
    session.commit()


def add_filernames_listdict(session, filer_list, filer_type='issuer',
                            name_key='name', cik_key='cik',
                            sector_key='sector', industry_key='industry'):
    '''Given a list of filers with names and an active session add_filers_to_filer_database() for each filer in filer_list.  If filer name does not already exist add filer name to filer name database.
    '''
    if type(filer_list) == dict: filer_list = [filer_list]
    add_filers_listdict(
        session,
        filer_list,
        filer_type=filer_type,
        cik_key=cik_key,
        sector_key=sector_key,
        industry_key=industry_key
    )
    for filer in filer_list:
        assert cik_key in filer and name_key in filer
        filer_name_exists = session.query(
            FilerName
        ).\
        filter(
            and_(
                FilerName.cik==filer[cik_key],
                FilerName.name==filer[name_key]
            )
        ).count()
        if not filer_name_exists:
            session.add(
                FilerName(
                    cik=filer[cik_key],
                    name=filer[name_key]
                )
            )
    session.commit()

def add_form_fours_listdict(session, form_list):
    '''Given a list of dicts with appropriate tags,
    Write to database
    '''
    if type(form_list) == dict: form_list = [form_list]
    add_filernames_listdict(session, form_list, filer_type='issuer',
                                           cik_key='issuer_cik', name_key='issuer_name')
    add_filernames_listdict(session, form_list, filer_type='owner',
                                           cik_key='owner_cik', name_key='owner_name')
    for ff in form_list:
        if not session.query(FormFour).filter(FormFour.file_name==ff['file_name']).count():
            ff_add = FormFour(
                    file_name                  = ff['file_name'],
                    filing_date                = ff['filing_date'],
                    issuer_cik                 = ff['issuer_cik'],
                    symbol                     = ff['issuer_symbol'],
                    owner_cik                  = ff['owner_cik'],
                    owner_name                 = ff['owner_name'],
                    owner_title                = ff['owner_title'],
                    owner_address_street1      = ff['owner_address_street1'],
                    owner_address_street2      = ff['owner_address_street2'],
                    owner_address_city         = ff['owner_address_city'],
                    owner_address_state        = ff['owner_address_state'],
                    owner_address_zip          = ff['owner_address_zip'],
                    owner_is_director          = ff['owner_is_director'],
                    owner_is_officer           = ff['owner_is_officer'],
                    owner_is_ten_percent_owner = ff['owner_is_ten_percent_owner'],
                    owner_is_other             = ff['owner_is_other'],
                    footnotes                  = ff['footnotes'],
                    remarks                    = ff['remarks']
                    )
            session.add(ff_add)
            session.flush()
            for trans in ff['transactions']:
                session.add(
                    FormFourTransaction(
                        form_id                    = ff_add.id,
                        derivative                 = trans['derivative'],
                        trans_number               = trans['trans_number'],
                        trans_date                 = trans['trans_date'],
                        trans_security_title       = trans['trans_security_title'],
                        trans_formtype             = trans['trans_formtype'],
                        trans_code                 = trans['trans_code'],
                        trans_equity_swap          = trans['trans_equity_swap'],
                        shares_change              = trans['shares_change'],
                        trans_price                = trans['trans_price'],
                        shares_owned_post          = trans['shares_owned_post']
                        ))
    session.commit()


def build_form_list(forms):
    results = []
    for form in forms:
        results.append({
            'cik': form.cik,
            'company_name': form.company_name,
            'date_filed': form.date_filed,
            'form_type': form.form_type,
            'file_name': form.file_name
            })
    return results


def main(start_date = date(2012,1,1)):
    day_range = date(2012,1,4) - start_date
    for delta in range(day_range.days):
        day = start_date + timedelta(days=delta)
        forms = session.query(DailyFiling).filter(
            and_(
                DailyFiling.date_filed==day,
                DailyFiling.form_type=='4')
            ).all()
        if not forms or len(forms)==0:
            continue
        print('\n\n%s' % str(day))
        print('Building form list')
        forms = build_form_list(forms)
        forms = list_grouper(forms,10)
        for idx, form_list in enumerate(forms):
            print('Retrieving fulltext from group %s' % str(idx))
            form_list = get_fulltext_forms_from_sec_ftp(form_list)
            print('Cleaning fulltext')
            form_list = clean_from_fulltext(form_list)
            print('Adding forms to database')
            add_form_fours_listdict(session,form_list)
