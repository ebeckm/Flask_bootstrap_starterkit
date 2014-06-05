# Base package imports
from __future__ import print_function
import sys, os
from cStringIO import StringIO
from datetime import datetime, date, timedelta

# Flask extensions
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, jsonify, json
# Flask forms
from flask.ext.wtf import Form
from wtforms import TextField, BooleanField, PasswordField, TextAreaField, SubmitField, \
    validators, ValidationError
# Flask mail
from flask.ext.mail import Message, Mail
# Flask security
from flask.ext.login import current_user
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.security import Security, SQLAlchemyUserDatastore, \
    login_required, UserMixin, RoleMixin
import flask.ext.security.utils as security_utils


###########################################################################
# Configuration
###########################################################################

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'super-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///databases/security.db'
app.config['SQLALCHEMY_BINDS'] = {
    'security':        'sqlite:///databases/security.db',
    'application':     'sqlite:///databases/application.db'
}
app.config['SECURITY_PASSWORD_HASH'] = 'sha512_crypt'
app.config['SECURITY_PASSWORD_SALT'] = '9yAPe05Nsjl6UjJEMlXOTsiuyPlcvfr9n26OLVuCReIs3Pw3SGnHv39'
app.config['SECURITY_REGISTERABLE'] = True
app.config['SECURITY_CHANGABLE'] = True
app.config['SECURITY_RECOVERABLE'] = True
app.config['SECURITY_CONFIRMABLE'] = False


# Mail
mail = Mail()
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = 'user@gmail.com'
app.config["MAIL_PASSWORD"] = '*****'
mail.init_app(app)


###########################################################################
# SQLAlchemy
###########################################################################

'''
Known bugs
----------
Bug: The database adds users as they submit registration,
     so unconfirmed users will be stored in the database.
     Thus, it may be possible to overwhelm the database by
     registering billions of unused email addresses.
Sol: Run a script every so often that flushes the databased of
     unregistered users.
'''

db = SQLAlchemy(app)

roles_users = db.Table('roles_users',
    db.Column('user_id',db.Integer(),db.ForeignKey('app_users.id')),
    db.Column('role_id',db.Integer(),db.ForeignKey('app_roles.id')))

class AppRole(db.Model, RoleMixin):
    __bind_key__ = 'security'
    __tablename__ = 'app_roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class AppUser(db.Model, UserMixin):
    __bind_key__ = 'security'
    __tablename__ = 'app_users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String)
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('AppRole', secondary=roles_users,
        backref=db.backref('users',lazy='dynamic'))

class Filer( db.Model ):
    __bind_key__ = 'application'
    __tablename__ = 'filers'
    id           = db.Column(db.Integer, primary_key=True)
    cik          = db.Column(db.Integer)
    filer_type   = db.Column(db.String)
    sector       = db.Column(db.String)
    industry     = db.Column(db.String)
    filer_names  = db.relationship('FilerName', backref='filer')

class FilerName( db.Model ):
    __bind_key__ = 'application'
    __tablename__ = 'filer_names'
    id          = db.Column(db.Integer, primary_key=True)
    cik         = db.Column(db.Integer, db.ForeignKey('filers.cik'))
    name        = db.Column(db.String)

class FormFour( db.Model ):
    __bind_key__ = 'application'
    __tablename__ = 'form_fours'
    id                         = db.Column(db.Integer, primary_key=True)
    file_name                  = db.Column(db.String)
    filing_date                = db.Column(db.Date)
    issuer_cik                 = db.Column(db.Integer, db.ForeignKey('filers.cik'))
    symbol                     = db.Column(db.String)
    owner_cik                  = db.Column(db.Integer, db.ForeignKey('filers.cik'))
    owner_name                 = db.Column(db.String)
    owner_title                = db.Column(db.String)
    owner_address_street1      = db.Column(db.String)
    owner_address_street2      = db.Column(db.String)
    owner_address_city         = db.Column(db.String)
    owner_address_state        = db.Column(db.String)
    owner_address_zip          = db.Column(db.String)
    owner_is_director          = db.Column(db.Boolean)
    owner_is_officer           = db.Column(db.Boolean)
    owner_is_ten_percent_owner = db.Column(db.Boolean)
    owner_is_other             = db.Column(db.Boolean)
    footnotes                  = db.Column(db.String)
    remarks                    = db.Column(db.String)
    transactions               = db.relationship('FormFourTransaction', backref='filing')

class FormFourTransaction( db.Model):
    __bind_key__ = 'application'
    __tablename__ = 'form_four_transactions'
    id                         = db.Column(db.Integer, primary_key=True)
    form_id                    = db.Column(db.Integer, db.ForeignKey('form_fours.id'))
    derivative                 = db.Column(db.String)
    trans_number               = db.Column(db.Integer)
    trans_security_title       = db.Column(db.String)
    trans_date                 = db.Column(db.Date)
    trans_formtype             = db.Column(db.String)
    trans_code                 = db.Column(db.String)
    trans_equity_swap          = db.Column(db.Boolean)
    shares_change              = db.Column(db.Numeric)
    trans_price                = db.Column(db.Numeric)
    shares_owned_post          = db.Column(db.Numeric)
    ownership_nature           = db.Column(db.String)


# Setup Flask-Security
db.session.execute("PRAGMA journal_mode=WAL")
user_datastore = SQLAlchemyUserDatastore(db, AppUser, AppRole)
security = Security(app, user_datastore)
db.create_all()


###########################################################################
# Forms
###########################################################################

class contact_form(Form):
    name = TextField("Name")
    email = TextField("Email", [validators.Required(), \
                                validators.Email("Please enter a valid email address.")])
    subject = TextField("Subject")
    message = TextAreaField("Message")
    submit = SubmitField("Send")

###########################################################################
# Search bar
###########################################################################

@app.route('/filer_search')
def filer_search():
    search = request.args.get('q')
    results = db.session.query(FilerName.name,FilerName.cik)
    results = results.filter(FilerName.name.like('%'+search+'%')).limit(10).all()
    results = [{'name':name,'cik':cik} for name,cik in results]
    return json.dumps(results)

###########################################################################
# Form four
###########################################################################

@app.route('/form_four')
def form_four():
    # If q, look up cik, render template
    cik = request.args.get('q')
    try:
        filer_type, = db.session.query(Filer.filer_type).filter(Filer.cik==cik).one()
        if filer_type == 'owner':
            results = db.session.query(FormFour).filter(FormFour.owner_cik==cik)
        elif filer_type == 'issuer':
            results = db.session.query(FormFour).filter(FormFour.issuer_cik==cik)
        results = results.filter(FormFour.filing_date<=date(2010,2,1))
        results = results.all()
        filer_info = results[0].__dict__
    except:
        return render_template('404.html'), 404
    filings = []
    for res in results:
        filings.append({
            'filing_date':res.filing_date,
            'transactions':[trans.__dict__ for trans in res.transactions]
            })
    res_string = StringIO()
    print(filings,file=res_string)
    return res_string.getvalue()


###########################################################################
# About
###########################################################################

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


@app.route('/index')
@app.route('/')
def index():
    return render_template('index.html',
       is_auth=current_user.is_authenticated())

@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html',
        is_auth=current_user.is_authenticated())

@app.route('/about')
def about():
    return render_template('about.html',
        is_auth=current_user.is_authenticated())

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    css_link = '"/static/css/forms.css?v=' + str(datetime.now()) + '"'
    css = { 'link' : css_link }
    form = contact_form()
    if request.method == 'POST':
        if form.validate() == False:
            return render_template('contact.html', form=form, css=css)
        else:
            msg = Message(form.subject.data, sender='user@gmail.com',
                          recipients=['user@gmail.com'])
            msg.body="""
            From: %s <%s>
            %s
            """ % (form.name.data, form.email.data, form.message.data)
            mail.send(msg)
            return render_template('about.html',
        is_auth=current_user.is_authenticated())
    elif request.method == 'GET':
        return render_template('contact.html',
            form=form, css=css,
            is_auth=current_user.is_authenticated())

###########################################################################
# Main
###########################################################################

if __name__ == "__main__":
    app.run(debug=True)
