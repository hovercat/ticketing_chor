from flask import Flask, render_template, request
from ..mapper import Mapper
from ..constants import *
import json
app = Flask(__name__)
db = Mapper(DB_URL)

@app.route("/")
def landing():
    return render_template("index.html", cards_left=5, price_student=10, price_full=15, concerts=db.get_concerts())

@app.route("/reserved", methods=['GET', 'POST'])
def reserved():
    if request.method == 'POST': # Maybe just have one function for landing & confirmed page?
        #TODO: IMplement doing the reservation
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


