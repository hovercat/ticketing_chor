from argparse import ArgumentParser
from datetime import datetime, timedelta
from uuid import uuid4

import sqlalchemy
from Mailgod import Mailgod
from api_secrets import *
from mapper import Mapper
from nordigen import NordigenClient

parser = ArgumentParser()
# parser.add_argument('--secret_key', type=str, required=True)
# parser.add_argument('--secret_id', type=str, required=True)
# parser.add_argument('--account_token', type=str, required=True)
# parser.add_argument('--refresh_token', type=str, required=True)
parser.add_argument('--sql_connector', type=str, required=True)
parser.add_argument('--log_file', type=str, required=True)


class Checker:  # sorry kanon, es hat fucking gebuggt, nix ging
    def __init__(self, ng_id, ng_key, ng_refresh_token, ng_account, db_connector, log_file_path):
        self.ng_id = ng_id
        self.ng_key = ng_key
        self.ng_refresh_token = ng_refresh_token
        self.ng_account = ng_account
        self.db_connector = db_connector
        self.log_file_path = log_file_path

        # setup nordigen client
        self.nordigen_client = self.establish_api()
        # connect to sql-db
        self.db = Mapper(self.db_connector)

    def establish_api(self):
        # setup nordigen client
        nordigen_client = NordigenClient(secret_key=self.ng_key, secret_id=self.ng_id)
        # refresh tokens
        new_tokens = nordigen_client.exchange_token(self.ng_refresh_token)
        nordigen_client.token = new_tokens['access']
        return nordigen_client

    def get_transactions_from_nordigen(self):
        #  get bank account
        bank_account = self.nordigen_client.account_api(self.ng_account)
        return bank_account.get_transactions()

    def add_transactions_to_db(self, nordigen_transactions):
        ng_trans = nordigen_transactions['transactions']['booked']
        transactions = []

        for ng_t in ng_trans:
            # check if already exists (stupid but works)
            query = sqlalchemy.sql.select(Mapper.Transaction).where(
                ng_t['transactionId'] == Mapper.Transaction.bank_transaction_id)
            query_result = self.db.session.execute(query)
            if query_result.first() is not None:
                continue

            # create transaction
            t = Mapper.Transaction()
            t.bank_transaction_id = ng_t['transactionId']
            t.payment_reference = ng_t.get('remittanceInformationStructured',
                                           ng_t.get('remittanceInformationUnstructured', None))
            t.currency = ng_t['transactionAmount']['currency']
            t.amount = ng_t['transactionAmount']['amount']
            t.payment_date = datetime.strptime(ng_t['bookingDate'], '%Y-%m-%d')
            t.debtor_iban = ng_t.get('debtorAccount', {'iban': None})['iban']
            t.debtor_name = ng_t.get('debtorName', None)

            # connect with reservation
            reservation_query = sqlalchemy.sql.select(Mapper.Reservation).where(
                t.payment_reference == Mapper.Reservation.payment_reference)
            reservation_result = self.db.session.execute(reservation_query)
            reservation = reservation_result.first()
            if reservation is None:
                t.status = 'invalid'
            else:
                t.status = 'valid'
                t.reservation = reservation[0]

            transactions.append(t)
            self.db.session.add(t)

        self.db.session.commit()
        for t in transactions:
            self.db.session.refresh(t)

        return transactions

    def sight_new_reservations(self):
        reservations = self.db.session.execute(
            sqlalchemy.sql.select(Mapper.Reservation).where(Mapper.Reservation.status == 'new'))
        reservations = [r[0] for r in reservations]
        for r in reservations:
            r.sight_new_res()
        if reservations:
            self.db.session.commit()
        return reservations

    def set_activated_reservations_to_open(self):
        reservations = self.db.session.execute(
            sqlalchemy.sql.select(Mapper.Reservation).where(Mapper.Reservation.status == 'activated'))
        reservations = [r[0] for r in reservations]
        for r in reservations:
            r.set_to_open()  # kind of bad but consistent
        if reservations:
            self.db.session.commit()
        return reservations

    def finalize_reservations(self):
        res = self.db.session.execute(
            sqlalchemy.sql.select(Mapper.Reservation).where(
                Mapper.Reservation.status.in_(['open', 'open_reminded', 'new_seen'])).join(
                Mapper.Reservation.transactions
            )
        )

        reservations = [r[0] for r in res]
        for r in reservations:
            # finalize if all correct
            if r.get_paid_amount() == r.get_expected_amount():
                r.finalize(self.db.mailgod)
            # disputed if smaller than expected and TODO tell someone
            elif 0 < r.get_paid_amount() < r.get_expected_amount():
                # send_mail to person in charge'
                r.dispute('Paid too litte.', self.db.mailgod)
            # finalized if paid is bigger than expected and TODO tell someone!
            elif r.get_paid_amount() > r.get_expected_amount():
                # send_mail
                r.dispute('Paid too much.', self.db.mailgod)
                r.finalize(self.db.mailgod)
        if reservations:
            self.db.session.commit()
        return reservations

    def close_unconfirmed_reservations(self):
        reservations = self.db.session.execute(
            sqlalchemy.sql.select(Mapper.Reservation).where(
                Mapper.Reservation.status == 'new_seen').filter(
                Mapper.Reservation.date_reservation_created <= datetime.now() - timedelta(hours=24)
            )
        )
        reservations = [r[0] for r in reservations]
        for r in reservations:
            r.cancel_24h(self.db.mailgod)
        if reservations:
            self.db.session.commit()
        return reservations

    def check_payment_of_canceled_res(self):
        reservations = self.db.session.execute(
            sqlalchemy.sql.select(Mapper.Reservation).where(Mapper.Reservation.status == 'closed').join(
                Mapper.Reservation.transactions))
        reservations = [r[0] for r in reservations]
        for r in reservations:
            r.dispute('Was canceled but already paid!', self.db.mailgod)
        if reservations:
            self.db.session.commit()
        return reservations

    def remind_reservations(self):
        reservations = self.db.session.execute(
            sqlalchemy.sql.select(Mapper.Reservation).where(
                Mapper.Reservation.status == 'open' and
                (Mapper.Reservation.date_reservation_created <= datetime.now() - timedelta(days=Mapper.Reservation.concert.duration_reminder))
            )
        )
        reservations = [r[0] for r in reservations]
        for r in reservations:
            r.remind(self.db.mailgod)
        if reservations:
            self.db.session.commit()
        return reservations

    def close_old_unpaid_reservations(self):
        reservations = self.db.session.execute(
            sqlalchemy.sql.select(Mapper.Reservation).where(
                Mapper.Reservation.status == 'open_reminded' and Mapper.Reservation.date_reservation_created <= datetime.now() - timedelta(
                    days=Mapper.Reservation.concert.duration_cancelation)
            )
        )
        reservations = [r[0] for r in reservations]
        for r in reservations:
            r.cancel(self.db.mailgod)
        if reservations:
            self.db.session.commit()
        return reservations

    def log_new_movements(self, reservation_dict: [], transaction_dict: []):
        log_file_path = open(self.log_file_path, 'wa')

        for reason, reservations in reservation_dict:
            for r in reservations:
                log_file_path.write("RESERVATION\t")
                log_file_path.write(reason)
                log_file_path.write('\t')
                log_file_path.write(r.to_csv('\t'))
                log_file_path.write('\n')
        # for reason, t in transaction_dict: # todo
        #     log_file_path.write("TRANSACTION\t")
        #     log_file_path.write(reason)
        #     log_file_path.write('\t')
        #     log_file_path.write(t.to_csv('\t'))


def main(args):
    checker = Checker(ng_id=SECRET_ID, ng_key=SECRET_KEY, ng_refresh_token=REFRESH_TOKEN, ng_account=ACCOUNT_TOKEN,
                      db_connector=args.sql_connector, log_file_path=args.log_file)
    # get newly opened reservations
    res_new = checker.sight_new_reservations()
    # get freshly activated reservations
    res_open = checker.set_activated_reservations_to_open()

    # get transactions
    nordigen_transactions = checker.get_new_transactions()
    new_valid_transactions = checker.add_transaction_to_db(nordigen_transactions)

    # finalize paid reservations
    res_finalized = checker.finalize_reservations()
    # close non-confirmed reservations after 24hours
    res_not_confirmed = checker.close_unconfirmed_reservations()
    # check whether canceled has been paid
    res_canceled_paid = checker.check_payments_of_canceled_res()
    # remind reservations that are not paid
    res_reminded = checker.remind_reservations()
    # cancel too old reservations
    res_closed = checker.close_old_reservations()

    checker.log_new_movements(
        {
            "New Reservation": res_new,
            "Activated Reservation": res_open,
            "Finalized Reservation": res_finalized,
            "Rejected Reservation 24h": res_not_confirmed,
            "Already closed, but paid Res": res_canceled_paid,
            "Reminded Reservation": res_reminded,
            "Closed Reservation": res_closed
        },
        {}
    )


if __name__ == '__main__':
    args = parser.parse_args()
    main(args)
