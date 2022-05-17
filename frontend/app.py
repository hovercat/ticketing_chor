import re
from flask import Flask, render_template, request, url_for
from ..mapper import Mapper
from ..constants import *
import json
import datetime
app = Flask(__name__)
db = Mapper(DB_URL)

@app.route("/")
def landing():
    url_for('static', filename='style.css')
    url_for('static', filename='js.js')
    return render_template("index.html",tickets_left=5, concerts=db.get_concerts())

@app.route("/reserve", methods=['GET', 'POST'])
def reserve():
    if request.method == 'POST': # Maybe just have one function for landing & confirmed page?

        # email validation
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if not re.fullmatch(regex, request.form['email']):
            print("Invalid Email")
            return "Error: Email not valid."

        tickets_full = int(request.form['tickets_full'])
        tickets_student = int(request.form['tickets_student'])

        if (tickets_full < 0 or tickets_student < 0  or tickets_student + tickets_full <= 0):
            return "Error: Can't buy less than 0 tickets"
        if (tickets_student + tickets_full > 50):
            return "Error: Can't buy so many tickets. Please contact chor directly."


        reservation = Mapper.Reservation(
            user_email=request.form['email'],
            user_name=request.form['name'],
            tickets_full_price=int(request.form['tickets_full']), 
            tickets_student_price=int(request.form['tickets_student']),
            date_reservation_created=datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
            date_email_activated=datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
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
        reservation.reserve() #TODO: WTF is even this DB API ?? Need to commit the DB object and get its Id then get it from DB or something
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
        if reservation.status == 'new' or reservation.status == 'new_seen':
            reservation.activate()
            db.session.commit()
        return render_template("confirmed.html",
                               total=reservation.get_expected_amount_eur(),
                               latest_payment_date=reservation.get_latest_possible_payment_date(),
                               payment_reference=reservation.payment_reference)

@app.route("/getseats/<id>", methods=['GET'])
def getseats(id):
    try:
        id = int(id)
        concert = list(filter(lambda c: c.concert_id == id,db.get_concerts()))[0]
        return json.dumps({'failed': False, 'seats':concert.get_available_tickets_amount()})
    except Exception as e:
        return json.dumps({"failed":True, "details":str(e)})

@app.route("/getprice/<id>")
def getprice(id):
    try:
        id = int(id)
        concert = list(filter(lambda c: c.concert_id == id,db.get_concerts()))[0]
        return json.dumps({'failed': False, 'full':concert.full_price, 'student':concert.student_price})
    except Exception as e:
        return json.dumps({"failed":True, "details":str(e)})
        

    

@app.route("/confirm")
def confirm():
    pass


