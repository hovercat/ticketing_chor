import datetime

import sqlalchemy
from sqlalchemy.orm import close_all_sessions

import unittest

from checker import Checker
MAIL_TEST = True
from mapper import Mapper
from constants import *

SQL_CONNECTOR = "postgresql://postgres@localhost:5432/testing"
class CheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        import mail_secrets as ms

        close_all_sessions()
        self.db = Mapper(SQL_CONNECTOR)
        self.db.session.no_autoflush

        with open('db/drop_tables.sql') as file:
            query = sqlalchemy.text(file.read())
            self.db.session.execute(query)
        with open('db/create_tables.sql') as file:
            query = sqlalchemy.text(file.read())
            self.db.session.execute(query)

        self.concert = Mapper.Concert(
            concert_id=1,
            date_sale_start=(datetime.datetime.today() - datetime.timedelta(days=14)).strftime('%Y-%m-%d %H:%M:%S'),
            date_sale_end=(datetime.datetime.today() + datetime.timedelta(days=14)).strftime('%Y-%m-%d %H:%M:%S'),
            date_concert=(datetime.datetime.today() + datetime.timedelta(days=21)).strftime('%Y-%m-%d %H:%M:%S'),
            full_price=100, student_price=1,
            duration_reminder=4, duration_cancelation=10, total_tickets=200
        )
        self.res = Mapper.Reservation(
            res_id=1,
            user_email='aschl.uli+test@gmail.com',
            user_name='test_ulrich',
            tickets_full_price=4, tickets_student_price=2,
            date_reservation_created=datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
            date_email_activated=datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
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
        self.db.session.commit()

        self.checker = Checker(ng_id=API_SECRETS['SECRET_ID'],
                               ng_key=API_SECRETS['SECRET_KEY'],
                               ng_refresh_token=API_SECRETS['REFRESH_TOKEN'],
                               ng_account=API_SECRETS['ACCOUNT_TOKEN'],
                               db_connector=SQL_CONNECTOR,
                               log_file_path="checker_tests.log")

    def tearDown(self) -> None:
        close_all_sessions()
        with open('db/drop_tables.sql') as file:
            query = sqlalchemy.text(file.read())
            self.db.session.execute(query)

        self.db.session.rollback()
        self.db.session.close()

    def test_add_transaction_to_db(self):
        nordigen_transactions = {
                                    "transactions":{
                                        "booked":[
                                            {"additionalInformation":"address: HOME1",
                                             "bookingDate":"2022-05-11",
                                             "debtorAccount":{"iban":"AT29292"},
                                             "debtorName":"Hubert Mörtenhuber",
                                             "remittanceInformationStructured":"unrelated",
                                             "transactionAmount":{"amount":"2.50","currency":"EUR"},
                                             "transactionId":"12312312",
                                             "valueDate":"2022-05-11"},
                                            {"additionalInformation":"address: HOME2",
                                             "bookingDate":"2022-05-11",
                                             "debtorAccount":{"iban":"AT2929234"},
                                             "debtorName":"Simon Mustermensch",
                                             "remittanceInformationStructured":self.res.payment_reference,
                                             "transactionAmount":{"amount":self.res.get_expected_amount(),"currency":"EUR"},
                                             "transactionId":"8",
                                             "valueDate":"2022-05-11"}
                                        ],"pending":[]}}
        ts = self.checker.add_transactions_to_db(nordigen_transactions)
        self.assertEqual(ts[0].status, 'invalid')
        self.assertEqual(ts[1].status, 'valid')
        ts2 = self.checker.add_transactions_to_db(nordigen_transactions)
        self.assertListEqual(ts2, [])

    def test_finalize_paid_reservations(self):
        self.res.status = 'open'
        self.db.session.commit()
        f_res = self.checker.finalize_paid_reservations()
        self.assertEqual(f_res, [])

        self.res.status = 'open_reminded'
        self.db.session.commit()
        f_res = self.checker.finalize_paid_reservations()
        self.assertEqual(f_res, [])

        self.res.status = 'new_seen'
        self.db.session.commit()
        f_res = self.checker.finalize_paid_reservations()
        self.assertEqual(f_res, [])

        self.res.transactions.append(self.t1)
        self.res.status = 'open'
        self.db.session.commit()
        f_res = self.checker.finalize_paid_reservations()
        self.assertNotEqual(f_res, [])
        self.assertEqual(f_res[0].res_id, self.res.res_id)

        self.res.status = 'open_reminded'
        self.db.session.commit()
        f_res = self.checker.finalize_paid_reservations()
        self.assertNotEqual(f_res, [])
        self.assertEqual(f_res[0].res_id, self.res.res_id)

        self.res.status = 'new_seen'
        self.db.session.commit()
        f_res = self.checker.finalize_paid_reservations()
        self.assertNotEqual(f_res, [])
        self.assertEqual(f_res[0].res_id, self.res.res_id)

        self.res.status = 'canceled'
        self.db.session.commit()
        f_res = self.checker.finalize_paid_reservations()
        self.assertEqual(f_res, [])

    def test_finalize_overpaid_reservations(self):
        self.res.transactions.append(self.t1)
        self.res.status = 'open'
        self.db.session.commit()
        f_res = self.checker.finalize_overpaid_reservations()
        self.assertEqual(f_res, [])

        self.res.status = 'open'
        self.res.transactions = []
        self.res.transactions.append(self.t2) # not enough
        self.db.session.commit()
        f_res = self.checker.finalize_overpaid_reservations()
        self.assertEqual(f_res, [])

        self.res.transactions.append(self.t3) # too much
        self.db.session.commit()
        f_res = self.checker.finalize_overpaid_reservations()
        self.assertNotEqual(f_res, [])
        self.assertEqual(f_res[0].res_id, self.res.res_id)



    def test_remind_reservations(self):
        self.res.status = 'open'
        self.res.date_reservation_created = self.res.date_reservation_created - datetime.timedelta(days=5)
        self.db.session.commit()

        self.checker.remind_reservations()
        self.db.session.refresh(self.res)
        self.assertEqual(self.res.status, 'open_reminded')

    def test_close_old_unpaid_reservations(self):
        self.res.status = 'open_reminded'
        self.res.date_reservation_created = self.res.date_reservation_created - datetime.timedelta(days=self.res.concert.duration_cancelation+1)
        self.db.session.commit()

        self.checker.close_old_unpaid_reservations()
        self.db.session.refresh(self.res)
        self.assertEqual(self.res.status, 'canceled')

    def test_check_payment_of_canceled_res(self):
        self.res.status = 'canceled'
        self.t1.reservation = self.res
        self.db.session.commit()

        self.checker.check_payment_of_canceled_res()
        self.db.session.refresh(self.res)
        self.assertEqual(self.res.status, 'canceled')


    def test_close_unconfirmed_reservations(self):
        self.res.status = 'new_seen'
        self.db.session.commit()

        self.checker.close_unconfirmed_reservations()
        self.assertEqual(self.res.status, 'new_seen')

        self.res.status = 'new_seen'
        self.res.date_reservation_created = self.res.date_reservation_created - datetime.timedelta(hours=25)
        self.db.session.commit()
        self.checker.close_unconfirmed_reservations()
        self.db.session.refresh(self.res)
        self.assertEqual(self.res.status, 'canceled')

    def test_sight_new_reservations(self):
        self.res.status = 'new'
        self.db.session.commit()

        self.checker.sight_new_reservations()
        self.assertEqual(self.res.status, 'new_seen')

        r = self.checker.sight_new_reservations()
        self.assertEqual(r, [])

    def test_set_activated_reservations_to_open(self):
        self.res.status = 'new'
        self.db.session.commit()
        self.checker.set_activated_reservations_to_open()
        self.assertEqual(self.res.status, 'new')

        self.res.status = 'activated'
        self.db.session.commit()
        self.checker.set_activated_reservations_to_open()
        self.db.session.refresh(self.res)
        self.assertEqual('open', self.res.status)


if __name__ == '__main__':
    # datum = 13.05.2022
    unittest.main()
