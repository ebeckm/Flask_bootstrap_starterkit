###########################################################################
# Security
###########################################################################

import sqlite3
db_path = 'databases/'

connection = sqlite3.connect(db_path + 'security.db')
cursor = connection.cursor()

cursor.execute('''
    CREATE TABLE app_users(
        id INTEGER,
        email TEXT,
        password TEXT,
        active INTEGER,
        confirmed_at TEXT,
        PRIMARY KEY (id),
        UNIQUE (email)
)
''')

cursor.execute('''
    CREATE TABLE app_roles(
        id INTEGER,
        name TEXT,
        description TEXT,
        PRIMARY KEY (id),
        UNIQUE (name)
)
''')

cursor.execute('''
    CREATE TABLE roles_users(
        user_id INTEGER,
        role_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES app_users(id),
        FOREIGN KEY (role_id) REFERENCES app_roles(id)
)
''')

connection.commit()
connection.close()

###########################################################################
# Backend
###########################################################################

import sqlite3
db_path = 'databases/'

connection = sqlite3.connect(db_path + 'filings.db')
cursor = connection.cursor()

cursor.execute('''
    CREATE TABLE daily_index(
        id INTEGER,
        cik INTEGER,
        company_name TEXT,
        form_type TEXT,
        date_filed TEXT,
        file_name TEXT,
        PRIMARY KEY (id)
)
''')

cursor.execute('DROP TABLE filers')
cursor.execute('DROP TABLE filer_names')
cursor.execute('DROP TABLE filer_symbols')
cursor.execute('DROP TABLE form_four_transactions')
cursor.execute('DROP TABLE form_fours')

cursor.execute('''
    CREATE TABLE filers(
        id INTEGER,
        cik INTEGER,
        filer_type TEXT,
        sector TEXT,
        industry TEXT,
        PRIMARY KEY (id)
)
''')

cursor.execute('''
    CREATE TABLE filer_names(
        id INTEGER,
        cik INTEGER,
        name TEXT,
        FOREIGN KEY(cik) REFERENCES filers(cik),
        PRIMARY KEY (id)
)
''')

cursor.execute('''
    CREATE TABLE filer_symbols(
        id INTEGER,
        cik INTEGER,
        symbol TEXT,
        FOREIGN KEY(cik) REFERENCES filers(cik),
        PRIMARY KEY (id)
)
''')

cursor.execute('''
    CREATE TABLE form_fours(
        id INTEGER,
        file_name TEXT,
        filing_date TEXT,
        issuer_cik INTEGER,
        symbol TEXT,
        owner_cik INTEGER,
        owner_name TEXT,
        owner_title TEXT,
        owner_address_street1 TEXT,
        owner_address_street2 TEXT,
        owner_address_city TEXT,
        owner_address_state TEXT,
        owner_address_zip TEXT,
        owner_is_director INTEGER,
        owner_is_officer INTEGER,
        owner_is_ten_percent_owner INTEGER,
        owner_is_other INTEGER,
        footnotes TEXT,
        remarks TEXT,
        FOREIGN KEY(issuer_cik) REFERENCES filers(cik),
        FOREIGN KEY(owner_cik) REFERENCES filers(cik),
        PRIMARY KEY (id)
)
''')

cursor.execute('''
    CREATE TABLE form_four_transactions(
        id INTEGER,
        form_id INTEGER,
        file_name TEXT,
        derivative INTEGER,
        trans_number INTEGER,
        trans_date TEXT,
        trans_security_title TEXT,
        trans_formtype TEXT,
        trans_code TEXT,
        trans_equity_swap INTEGER,
        shares_change REAL,
        trans_price REAL,
        shares_owned_post REAL,
        ownership_nature TEXT,
        FOREIGN KEY(form_id) REFERENCES form_fours(id),
        PRIMARY KEY(id)
);
''')

connection.commit()
connection.close()

###########################################################################
# Application
###########################################################################

import sqlite3
db_path = 'databases/'

connection = sqlite3.connect(db_path + 'application.db')
cursor = connection.cursor()
