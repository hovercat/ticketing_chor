from datetime import datetime
from uuid import uuid4

import sqlalchemy
from nordigen import NordigenClient
from argparse import ArgumentParser

from db_map_ticketing.mapper import Mapper

parser = ArgumentParser()
parser.add_argument('--secret_key', type=str, required=True)
parser.add_argument('--secret_id', type=str, required=True)
parser.add_argument('--account_token', type=str, required=True)
parser.add_argument('--refresh_token', type=str, required=True)
parser.add_argument('--sql_connector', type=str, required=True)

args = parser.parse_args()


def establish_api(secret_id, secret_key, refresh_token):
    # setup nordigen client
    nordigen_client = NordigenClient(secret_key=secret_key, secret_id=secret_id)
    # refresh tokens
    new_tokens = nordigen_client.exchange_token(refresh_token)
    nordigen_client.token = new_tokens['access']
    # save tokens somewhere
    # with open("ACCESS_TOKEN", "w") as acc_file:
    #    acc_file.write(new_tokens['access'])

    return nordigen_client


def add_transaction_to_db(db, nordigen_transactions):
    transactions = nordigen_transactions['transactions']['booked']

    for t in transactions:
        # check if already exists (stupid but works)
        query = db.session.query(db.Transaction).where(t['transactionId'] == db.Transaction.bank_transaction_id)
        query_result = db.session.execute(query)

        if query_result.first() is not None:
            continue

        db_trans = db.Transaction()
        db_trans.bank_transaction_id = t['transactionId']
        db_trans.payment_reference = t.get('remittanceInformationStructured',
                                           t.get('remittanceInformationUnstructured', None))
        db_trans.currency = t['transactionAmount']['currency']
        db_trans.amount = t['transactionAmount']['amount']
        db_trans.payment_date = datetime.strptime(t['bookingDate'], '%Y-%m-%d')
        db_trans.debtor_iban = t.get('debtorAccount', {'iban': None})['iban']
        db_trans.debtor_name = t.get('debtorName', None)
        db_trans.handled = False

        db.session.add(db_trans)

    db.session.commit()
    return


def connect_transactions_and_reservations(db):
    query = sqlalchemy.sql.select(db.Transaction, db.Reservation).where(db.Transaction.res_id == None).join(
        db.Reservation, db.Reservation.payment_reference == db.Transaction.payment_reference)
    query_result = db.session.execute(query)

    for t, r in query_result:
        t.reservation = r

    db.session.commit()


def handle_transactions(db):
    # get all transactions not yet handled
    # t <- db
    query = sqlalchemy.sql.select(db.Reservation).where(db.Transaction.handled == False).join(db.Reservation,
                                                                                              db.Reservation.res_id == db.Transaction.res_id)
    query_result = db.session.execute(query)

    # loop through reservations
    for r in query_result:
        # check whether all has been paid
        exp_total = 10
        paid_total = 10

        # if exp == paid
        #  send out mail and finalize
        # elif exp > paid # paid too little
        #  do something, e.g. send mail informing of too little payment
        # else # too much paid
        #  do something
        pass


def main(args):
    #  establish nordigen api
    nordigen_client = establish_api(args.secret_key, args.secret_id, args.refresh_token)
    #  get bank account
    bank_account = nordigen_client.account_api(args.account_token)
    # connect to sql-db
    db = Mapper(args.sql_connector)

    # get transactions
    # transactions = bank_account.get_transactions()
    # add_transaction_to_db(db, transactions)

    # connect transactions with reservations
    connect_transactions_and_reservations(db)

    # finalize reservations
    handle_transactions(db)


main(args)
print(1)
