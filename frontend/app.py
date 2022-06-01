import hashlib
import re
import smtplib

from flask import Flask, render_template, request, url_for, redirect, flash
from flask_admin.contrib.sqla import ModelView
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash

from frontend.AuthAdminIndexView import AuthAdminIndexView
from frontend.ReservationModelView import ReservationModelView
from frontend.TransactionModelView import TransactionModelView
from frontend.ConcertModelView import ConcertModelView
from mapper import Mapper
from constants import *
import json
import datetime
from flask_admin import Admin, AdminIndexView

app = Flask(__name__)
db = Mapper(DB_URL)

# flask admin
admin_auth = HTTPBasicAuth()
app.config['SECRET_KEY'] = FLASK_SECRET
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'

admin = Admin(app, name='TU Chor Ticketing Adminbereich', template_mode='bootstrap3', index_view=AuthAdminIndexView(admin_auth))

admin.add_view(ConcertModelView(Mapper.Concert, db.session, admin_auth))
admin.add_view(ReservationModelView(Mapper.Reservation, db.session, admin_auth))
#admin.add_view(PaidReservationModelView(Mapper.Reservation, db.session, admin_auth, name='Reservations (new version)', endpoint='res_new' ))
admin.add_view(TransactionModelView(Mapper.Transaction, db.session, admin_auth))


# repost_tokens = {}


@app.route("/")
def landing():
    url_for('static', filename='style.css')
    url_for('static', filename='js.js')
    # repost_token = hashlib.sha1(str(datetime.datetime.now()).encode()).hexdigest()[:20]
    # repost_tokens[repost_token] = 0  # set unused token
    repost_token = Mapper.Post_Token(what_for='reserving', used=False, token_time=datetime.datetime.now())
    repost_token.gen_token()
    db.session.add(repost_token)
    db.session.commit()
    concerts = db.get_concerts()
    if len(concerts) > 0:
        return render_template("index.html", concerts=db.get_concerts(), hidden_repost_token=repost_token.token)
    else:
        return render_template("no_concerts.html")


@app.route("/reserve", methods=['GET', 'POST'])
def reserve():
    if request.method == 'POST':  # Maybe just have one function for landing & confirmed page?
        # check repost token
        if not db.invalidate_token(request.form['hidden_repost_token']):
            return render_template("error.html", error1="Das Formular hat leider seine Gültigkeit verloren.",
                                   error2="Sollten Sie bereits reserviert haben, überprüfen Sie Ihr Email-Postfach. Ansonsten laden Sie bitte die Seite neu und erstellen Sie eine neue Reservierung.")

        # email validation
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if not re.fullmatch(regex, request.form['email']):
            print("Invalid Email")
            return render_template(
                "error.html",
                error1="Email-Adresse {email} nicht gültig.!".format(request.form['email']),
                error2="Bitte überprüfen Sie die Schreibweise der Email-Adresse."
            )

        tickets_full = int(request.form['tickets_full'].strip() or 0)
        tickets_student = int(request.form['tickets_student'].strip() or 0)

        if tickets_full < 0 or tickets_student < 0 or tickets_student + tickets_full <= 0:
            return "Error: Can't buy less than 0 tickets"
        if tickets_student + tickets_full > 50:
            return "Error: Can't buy so many tickets. Please contact chor directly."

        reservation = Mapper.Reservation(
            user_email=request.form['email'],
            user_name=request.form['name'],
            tickets_full_price=tickets_full,
            tickets_student_price=tickets_student,
            # date_reservation_created=datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
            status='new',
            pay_state='none',
            concert_id=int(request.form['concertdate'])
        )
        db.session.add(reservation)
        db.session.commit()
        db.session.refresh(reservation)
        reservation.set_payment_reference()
        db.session.commit()
        db.session.refresh(reservation)

        try:
            reservation.reserve()  # TODO: WTF is even this DB API ?? Need to commit the DB object and get its Id then get it from DB or something
        except smtplib.SMTPRecipientsRefused as e:
            return render_template(
                "error.html",
                error1='Ihre E-Mail {email} funktioniert wohl nicht.'.format(email=request.form['email']),
                error2='Bitte kontrollieren Sie die Schreibweise der Mail-Addresse.'
            )
        finally:
            db.session.commit()

        return render_template("confirm.html", email=request.form['email'])
    elif request.method == 'GET':
        return "Error"


@app.route("/confirm/<reservation_hash>")
def confirm_reservation(reservation_hash):
    reservation = db.get_reservation_by_payment_reference(reservation_hash)
    if reservation is None:
        return render_template("not_found.html")
    else:
        newly_confirmed = reservation.status == 'new' or reservation.status == 'new_seen'
        if newly_confirmed:
            reservation.activate()
            db.session.commit()
        return render_template("confirmed.html",
                               total=reservation.get_expected_amount_eur(),
                               latest_payment_date=reservation.get_latest_possible_payment_date(),
                               payment_reference=reservation.payment_reference,
                               newly_confirmed=newly_confirmed)


@app.route("/getseats/<id>", methods=['GET'])
def getseats(id):
    try:
        id = int(id)
        concert = list(filter(lambda c: c.concert_id == id, db.get_concerts()))[0]
        return json.dumps({'failed': False, 'seats': concert.get_available_tickets_amount()})
    except Exception as e:
        return json.dumps({"failed": True, "details": str(e)})


@app.route("/getprice/<id>")
def getprice(id):
    try:
        id = int(id)
        concert = list(filter(lambda c: c.concert_id == id, db.get_concerts()))[0]
        return json.dumps({'failed': False, 'full': concert.full_price, 'student': concert.student_price})
    except Exception as e:
        return json.dumps({"failed": True, "details": str(e)})


@app.route("/confirm")
def confirm():
    pass


@app.route("/login")
@admin_auth.login_required
def login():
    if admin_auth.get_auth():
        flash("Logged in!")
        return redirect('/admin')


@admin_auth.verify_password
def verify_password(user, pw):
    if user in admins.keys() and check_password_hash(admins[user], pw):
        return True
    else:
        return False


@app.errorhandler(404)
def page_not_found(e):
    return render_template("not_found.html")

# @app.errorhandler(smtplib.SMTPRecipientsRefused):
#    pass
