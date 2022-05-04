from sqlalchemy.orm import Session
import sqlalchemy as db
from psycopg2 import connect, sql
import sys

import unittest


def connect_to_db(SQL_CONNECTOR):
    engine = db.create_engine(SQL_CONNECTOR, connect_args={'options': '-csearch_path=testing'})  # schema name
    connection = engine.connect()
    metadata = db.MetaData()
    session = Session(engine)
    return engine, session, connection, metadata


def create_db(DB, USR, HOST, PORT):
    conn = connect(
        dbname=DB,
        user=USR,
        # password = PW,
        host=HOST,
        port=PORT
    )
    cursor = conn.cursor()

    sql_create_statement = ""
    with open('db/CREATE_TEST_DB.sql', 'r') as create_test_db:
        cursor.execute(create_test_db.read())
    with open('db/choir_ticketing_ticketing_concert.sql', 'r') as f:
        cursor.execute(f.read())
    with open('db/choir_ticketing_ticketing_payment_status.sql', 'r') as f:
        cursor.execute(f.read())
    with open('db/choir_ticketing_ticketing_reservation_status.sql', 'r') as f:
        cursor.execute(f.read())
    with open('db/choir_ticketing_ticketing_reservation_payment_status.sql', 'r') as f:
        cursor.execute(f.read())
    with open('db/choir_ticketing_ticketing_reservation.sql', 'r') as f:
        cursor.execute(f.read())
    with open('db/choir_ticketing_ticketing_transaction.sql', 'r') as f:
        cursor.execute(f.read())

    return cursor, conn

SQL_CONNECTOR = "postgresql://postgres@localhost:5432/choir_ticketing/test_db"
DB = 'choir_ticketing'
USR = 'postgres'
HOST = 'localhost'
PORT = 5432


class CheckerTests(unittest.TestCase):

    def test_do_this(self):
        db = create_db(DB, USR, HOST, PORT)
        self.assertTrue(True, 'is true')

    def test_finalize_reservation(self):
        pass

    def test_cancel_reservation(self):
        pass

    def test_remind_reservation(self):
        pass

    def test_dispute_reservation_too_little_money(self):
        pass

    def test_dispute_reservation_too_much_money(self):
        pass

    def test_dispute_reservation_already_canceled(self):
        pass

    def test_send_mail(self):
        pass

    def test_handle_payments(self):
        pass

    def test_add_transactions_to_db(self):
        pass

    def test_establish_API(self):
        pass

    def test_database_connection(self):
        pass

    def test_connect_transaction_and_reservation(self):
        pass


    pass


if __name__ == '__main__':
    # datum = 13.05.2022
    unittest.main()
