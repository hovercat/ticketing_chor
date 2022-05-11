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
        db_trans.status = Mapper.Payment_Status.new

        db.session.add(db_trans)

    db.session.commit()
    return


def connect_transactions_and_reservations(db):
    query = sqlalchemy.sql.select(db.Transaction, db.Reservation).where(db.Transaction.res_id == None).join(
        db.Reservation, db.Reservation.payment_reference == db.Transaction.payment_reference)
    query_result = db.session.execute(query)

    for t, r in query_result:
        t.status = Mapper.Payment_Status.valid
        t.reservation = r

    db.session.commit()


def cancel_reservation(db, reservation):
    pass


def finalize_reservation(db, reservation):
    pass


def remind_reservation(db, reservation):
    pass


def paid_too_little_reservation(db, reservation):
    pass


def paid_too_much_reservation(db, reservation):
    pass


def already_canceled_but_paid(db, reservation):
    pass


def handle_reservations(db):
    #  get all reservations not yet finalized
    query = sqlalchemy.sql.select(db.Reservation).where(db.Reservation.status != Mapper.Reservation_Status.finalized)
    query_result = db.session.execute(query)

    for r in query_result:
        #
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
    # handle_transactions(db)


if __name__ == '__main__':
    args = parser.parse_args()
    main(args)
    print(1)


def spot_and_assign_transactions(db: Mapper, transactions: Mapper.Transaction):
    for t in transactions:
        res_iterator = db.session.execute(
            sqlalchemy.sql.select(Mapper.Reservation)
                .where(Mapper.Reservation.payment_reference == t.payment_reference)
        ).first()
        if res_iterator is not None:
            r = res_iterator[0]
            t.reservation = r
            t.status = 'valid'
        else:
            t.status = 'unrelated'


def check_payment_reservation(db, res: Mapper.Reservation):
    if res.status in ['open', 'open_reminded']:
        # finalize if all correct
        if res.get_paid_amount() == res.get_expected_amount():
            # send_mail
            res.status = 'finalized'
            pass
        # disputed if smaller than expected and TODO tell someone
        elif res.get_paid_amount() < res.get_expected_amount():
            # send_mail to person in charge
            res.status = 'disputed'
            pass
        # finalized if paid is bigger than expected and TODO tell someone!
        elif res.get_paid_amount() > res.get_expected_amount():
            # send_mail
            res.status = 'finalized'
            pass

    if res.status in ['canceled']:
        if res.get_paid_amount() > 0:
            # todo send mail to person in charge
            pass

def check_overdue_reservations(db, res):
    # wat do here?


def check_reservations(db: Mapper):
    reservations = db.session.execute(sqlalchemy.sql.select(db.Reservation)) # TODO nur die open oder open_reminded sind?
    for r in reservations:
        check_payment_reservation(db, r)
