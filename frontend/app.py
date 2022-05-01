from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def landing():
    return render_template("index.html", cards_left = 5, price_student=10, price_full = 15)

@app.route("/reserved", methods=['GET', 'POST'])
def reserved():
    if request.method == 'POST': # Maybe just have one function for landing & confirmed page?
        return render_template("confirm.html", email=request.form['email'])
    elif request.method == 'GET':
        return "Error"

@app.route("/confirm")
def confirm():
    pass


