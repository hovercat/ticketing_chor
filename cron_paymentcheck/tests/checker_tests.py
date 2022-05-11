import datetime

from sqlalchemy.orm import Session
import sqlalchemy as db
from psycopg2 import connect, sql

import unittest

from cron_paymentcheck import checker
from db_map_ticketing.mapper import Mapper

SQL_CONNECTOR = "postgresql://postgres@localhost:5432/testing"
DB = 'testing'
USR = 'postgres'
HOST = 'localhost'
PORT = 5432


class CheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mapper(SQL_CONNECTOR)
        self.db.session.no_autoflush  # TODO WAT
        self.concert = Mapper.Concert(
            concert_id=1,
            date_sale_start=datetime.datetime.today() - datetime.timedelta(days=14),
            date_sale_end=datetime.datetime.today() + datetime.timedelta(days=14),
            date_concert=datetime.datetime.today() + datetime.timedelta(days=21),
            full_price=100, student_price=1,
            duration_reminder=4, duration_cancelation=10, tickets_available=200
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
        self.db.session.rollback()
        self.db.session.close()

    def test_spot_and_assign_transactions(self):
        checker.spot_and_assign_transactions(self.db, [self.t1, self.t4])
        self.assertIs(self.t1.status, 'valid')
        self.assertIs(self.t4.status, 'unrelated')

    def test_check_reservation_finalize(self):
        self.res.status = 'open'
        self.t1.reservation = self.res
        checker.check_payment_reservation(self.db, self.res)
        self.assertIs(self.res.status, 'finalized')

    def test_check_reservation_too_little(self):
        self.res.status = 'open'
        self.t2.reservation = self.res
        checker.check_payment_reservation(self.db, self.res)
        self.assertIs(self.res.status, 'disputed')

    def test_check_reservation_too_much(self):
        self.res.status = 'open'
        self.t2.reservation = self.res
        checker.check_payment_reservation(self.db, self.res)
        self.assertIs(self.res.status, 'finalized')
        self.assertIs(self.t2.status, 'disputed')

    def test_check_overdue_reservation_remind(self):
        self.res.status = 'open'
        self.res.date_reservation_created = self.res.date_reservation_created - datetime.timedelta(days=5)
        checker.check_payment_reservation(self.db, self.res)
        self.assertIs(self.res.status, 'open_reminded')

    def test_check_overdue_reservation_cancel(self):
        self.res.status = 'open_reminded'
        self.res.date_reservation_created = self.res.date_reservation_created - datetime.timedelta(days=11)
        checker.check_payment_reservation(self.db, self.res)
        self.assertIs(self.res.status, 'canceled')

    def test_check_reservation_canceled_then_paid(self):
        self.res.status = 'canceled'
        self.t1.reservation = self.res
        checker.check_payment_reservation(self.db, self.res)
        self.assertIs(self.res.status, 'canceled')
        self.assertIs(self.t1.status, 'disputed')


if __name__ == '__main__':
    # datum = 13.05.2022
    unittest.main()
