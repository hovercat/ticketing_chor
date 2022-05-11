from flask import Flask, render_template, request
from ..mapper import Mapper
import json
app = Flask(__name__)
SQL_CONNECTOR = "postgresql://postgres@localhost:5432/testing"
db = Mapper(SQL_CONNECTOR)

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

@app.route("/queryseats/<id>", methods=['GET'])
def getseats(id):
    try:
        id = int(id)
        concert = list(filter(lambda c: c.concert_id == id,db.get_concerts()))[0]
        return str(concert.get_available_tickets_amount())
    except Exception as e:
        return str(e)
    

@app.route("/confirm")
def confirm():
    pass


