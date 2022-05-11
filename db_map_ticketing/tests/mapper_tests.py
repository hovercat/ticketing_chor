import datetime

import sqlalchemy.sql
from sqlalchemy.orm import Session, InstanceEvents
import sqlalchemy as db
from psycopg2 import connect, sql
import sys

import unittest

from cron_paymentcheck import checker
from db_map_ticketing.mapper import Mapper

SQL_CONNECTOR = "postgresql://postgres@localhost:5432/testing"
DB = 'testing'
USR = 'postgres'
class CheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mapper(SQL_CONNECTOR)
        self.db.session.no_autoflush

        with open('drop_tables.sql') as file:
            query = sqlalchemy.text(file.read())
            self.db.session.execute(query)
        with open('create_tables.sql') as file:
            query = sqlalchemy.text(file.read())
            self.db.session.execute(query)

        self.concert = Mapper.Concert(
            concert_id=1,
            date_sale_start=datetime.datetime.today() - datetime.timedelta(days=14),
            date_sale_end=datetime.datetime.today() + datetime.timedelta(days=14),
            date_concert=datetime.datetime.today() + datetime.timedelta(days=21),
            full_price=100, student_price=1,
            duration_reminder=4, duration_cancelation=10, total_tickets=200
        )
        self.res = Mapper.Reservation(
            res_id=1,
            user_email='aschl.uli+test@gmail.com',
            user_name='test_ulrich',
            tickets_full_price=4, tickets_student_price=2,
            date_reservation_created=datetime.datetime.today(),
            date_email_activated=datetime.datetime.today(),
            status='new',
            pay_state='none',
            payment_reference='xyz'
        )
        self.res.concert = self.concert
        self.t1 = Mapper.Transaction(
            transaction_id=1,
            payment_reference='xyz',
            currency='EUR',
            amount=402,
            status='new'
        )
        self.t2 = Mapper.Transaction(
            transaction_id=2,
            payment_reference='xyz',
            currency='EUR',
            amount=399,
            status='new'
        )
        self.t3 = Mapper.Transaction(
            transaction_id=3,
            payment_reference='xyz',
            currency='EUR',
            amount=410,
            status='new'
        )
        self.t4 = Mapper.Transaction(
            transaction_id=4,
            payment_reference='unrelated',
            currency='EUR',
            amount=100,
            status='new'
        )
        self.t5 = Mapper.Transaction(
            transaction_id=5,
            payment_reference='xyz',
            currency='USD',
            amount=400,
            status='new'
        )

        self.db.session.add(self.concert)

    def tearDown(self) -> None:
        with open('drop_tables.sql') as file:
            query = sqlalchemy.text(file.read())
            self.db.session.execute(query)

        self.db.session.rollback()
        self.db.session.close()

    def test_reservation_get_expected_amount(self):
        self.assertEqual(self.res.get_paid_amount(), 0)
        self.res.transactions.append(self.t1)
        self.assertEqual(self.res.get_paid_amount(), 402)
        self.res.transactions.append(self.t2)
        self.assertEqual(self.res.get_paid_amount(), 801)

    def test_reservation_get_paid_amount(self):
        self.assertEqual(self.res.get_paid_amount(), 0)
        self.res.transactions.append(self.t1)
        self.assertEqual(self.res.get_paid_amount(), 402)
        self.res.transactions.append(self.t2)
        self.assertEqual(self.res.get_paid_amount(), 801)

    def test_reservation_reconstructor(self):
        res = Mapper.Reservation(res_id=1000)
        res.concert = self.concert

        self.assertIsNone(res.payment_reference)
        res.reconstructor() # would be called when commit usually
        self.assertEqual(res.payment_reference, "e3cbba8883")

    def test_get_reserved_tickets(self):
        self.res.status = 'open'
        self.assertListEqual(self.concert.get_reserved_tickets(), [self.res])
        self.res.status = 'canceled'
        self.assertListEqual(self.concert.get_reserved_tickets(), [])

    def test_get_reserved_tickets_amount(self):
        self.res.status = 'open'
        self.assertEqual(self.concert.get_reserved_tickets_amount(), 6)
        self.res.status = 'canceled'
        self.assertEqual(self.concert.get_reserved_tickets_amount(), 0)

    def test_get_sold_tickets(self):
        self.res.status = 'open'
        self.assertListEqual(self.concert.get_sold_tickets(), [])
        self.res.status = 'finalized'
        self.assertListEqual(self.concert.get_sold_tickets(), [self.res])

    def test_get_sold_tickets_amount(self):
        self.res.status = 'open'
        self.assertEqual(self.concert.get_sold_tickets_amount(), 0)
        self.res.status = 'finalized'
        self.assertEqual(self.concert.get_reserved_tickets_amount(), 6)

    def test_get_available_tickets_amount(self):
        self.assertEqual(self.concert.get_available_tickets_amount(), 194)
        self.res.status = 'open'
        self.assertEqual(self.concert.get_available_tickets_amount(), 194)
        self.res.status = 'finalized'
        self.assertEqual(self.concert.get_available_tickets_amount(), 194)
        self.res.status = 'disputed'
        self.assertEqual(self.concert.get_available_tickets_amount(), 194)
        self.res.status = 'open_reminded'
        self.assertEqual(self.concert.get_available_tickets_amount(), 194)
        self.res.status = 'canceled'
        self.assertEqual(self.concert.get_available_tickets_amount(), 200)

    def test_get_concerts(self):
        concerts = self.db.get_concerts()
        self.assertEqual(len(concerts), 1)
        self.assertEqual(concerts[0], self.concert)
        self.concert.date_sale_end = datetime.datetime.today() - datetime.timedelta(hours=1)
        self.assertListEqual(self.db.get_concerts(), [])

HOST = 'localhost'



if __name__ == '__main__':
    # datum = 13.05.2022
    unittest.main()

PORT = 5432
