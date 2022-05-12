from flask import Flask, render_template, request, url_for
from ..mapper import Mapper
from ..constants import *
import json
import datetime
import time
app = Flask(__name__)
db = Mapper(DB_URL)

@app.route("/")
def landing():
    url_for('static', filename='style.css')
    url_for('static', filename='js.js')
    return render_template("index.html",cards_left=5, concerts=db.get_concerts())

@app.route("/reserved", methods=['GET', 'POST'])
def reserved():
    if request.method == 'POST': # Maybe just have one function for landing & confirmed page?
        reservation = Mapper.Reservation(
            user_email=request.form['email'],
            user_name=request.form['name'],
            tickets_full_price=int(request.form['tickets_full']), 
            tickets_student_price=int(request.form['poor_people_tickets']),
            date_reservation_created=datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
            date_email_activated=datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
            status='new',
            pay_state='none',
            concert_id=int(request.form['concertdate'])
        )
        db.session.add(reservation)
        db.session.commit()
        db.session.refresh(reservation)
        reservation.reserve() #TODO: WTF is even this DB API ?? Need to commit the DB object and get its Id then get it from DB or something
        return render_template("confirm.html", email=request.form['email'])
    elif request.method == 'GET':
        return "Error"

@app.route("/confirm/<reservation_hash>")
def confirm_reservation(reservation_hash):
    pass #implement activation logic

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


