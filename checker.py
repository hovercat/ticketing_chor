import csv
from datetime import datetime, timedelta

from requests import HTTPError
from sqlalchemy import func, sql, text
from mapper import Mapper

from nordigen import NordigenClient
from constants import *


class Checker:
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
        try:
            bank_account = self.nordigen_client.account_api(self.ng_account)
        except HTTPError as e:
            raise e
        return bank_account.get_transactions()

    def add_transactions_to_db(self, nordigen_transactions):
        ng_trans = nordigen_transactions['transactions']['booked']
        transactions = []

        for ng_t in ng_trans:
            # check if already exists (stupid but works)
            query = sql.select(Mapper.Transaction).where(
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
            reservation_query = sql.select(Mapper.Reservation).where(
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
        SQL_NEW_RESERVATIONS=sql.select(Mapper.Reservation).where(Mapper.Reservation.status == 'new')
        return self.handle_reservations(SQL_NEW_RESERVATIONS, Mapper.Reservation.sight_new_res)


    def set_activated_reservations_to_open(self):
        SQL_ACTIVATED=sql.select(Mapper.Reservation).where(Mapper.Reservation.status == 'activated')
        return self.handle_reservations(SQL_ACTIVATED, Mapper.Reservation.set_to_open)

    def handle_reservations(self, reservation_query, func, args=None):
        reservations = self.db.session.execute(reservation_query)
        reservations = [r[0] for r in reservations]
        for r in reservations:
            if args:
                func(r, args)
            else:
                func(r)
        if reservations:
            self.db.session.commit()
        return reservations

    SQL_HANDLE_TRANSACTIONS = sql.select(Mapper.Reservation) \
        .join(Mapper.Reservation.transactions) \
        .join(Mapper.Reservation.concert) \
        .where(Mapper.Reservation.status.in_(['open', 'open_reminded', 'new_seen'])) \
        .group_by(Mapper.Reservation)

    def finalize_paid_reservations(self):
        SQL_FINALIZE = Checker.SQL_HANDLE_TRANSACTIONS.having(
            func.sum(Mapper.Transaction.amount) ==
            func.sum(
                Mapper.Concert.full_price * Mapper.Reservation.tickets_full_price +
                Mapper.Concert.student_price * Mapper.Reservation.tickets_student_price)
        )
        return self.handle_reservations(SQL_FINALIZE, Mapper.Reservation.finalize)

    def finalize_overpaid_reservations(self):
        SQL_OVERPAID = Checker.SQL_HANDLE_TRANSACTIONS.having(
            func.sum(Mapper.Transaction.amount) >
            func.sum(
                Mapper.Concert.full_price * Mapper.Reservation.tickets_full_price +
                Mapper.Concert.student_price * Mapper.Reservation.tickets_student_price)
        )
        return self.handle_reservations(SQL_OVERPAID, Mapper.Reservation.finalize, 'paid too much')

    def dispute_underpaid_reservations(self):
        SQL_UNDERPAID = Checker.SQL_HANDLE_TRANSACTIONS.having(
            func.sum(Mapper.Transaction.amount) <
            func.sum(
                Mapper.Concert.full_price * Mapper.Reservation.tickets_full_price +
                Mapper.Concert.student_price * Mapper.Reservation.tickets_student_price)
        )
        return self.handle_reservations(SQL_UNDERPAID, Mapper.Reservation.dispute, 'paid too little')

    def close_unconfirmed_reservations(self):
        SQL_UNCONFIRMED_CASES = sql.select(
            Mapper.Reservation,
        ).where(
            Mapper.Reservation.status == 'new_seen',
            datetime.now() - Mapper.Reservation.date_reservation_created > func.make_interval(0, 0, 0, 0, 24, 0)
        )

        return self.handle_reservations(SQL_UNCONFIRMED_CASES, Mapper.Reservation.cancel_24h)

    def check_payment_of_canceled_res(self):
        SQL_CHECK_CANCELED_BUT_PAID = sql.select(Mapper.Reservation)\
            .where(Mapper.Reservation.status == 'closed')\
            .join(Mapper.Reservation.transactions)

        return self.handle_reservations(SQL_CHECK_CANCELED_BUT_PAID, Mapper.Reservation.dispute, 'canceled but paid')

    def remind_reservations(self):
        SQL_REMINDER = sql.select(
            Mapper.Reservation,
        ).where(
            Mapper.Reservation.status == 'open',
            datetime.now() - Mapper.Reservation.date_reservation_created > func.make_interval(0,0,0,Mapper.Concert.duration_reminder,0,0)
        )
        return self.handle_reservations(SQL_REMINDER, Mapper.Reservation.remind)

    def close_old_unpaid_reservations(self):
        SQL_CLOSE_UNPAID = sql.select(
            Mapper.Reservation,
        ).where(
            Mapper.Reservation.status == 'open_reminded',
            datetime.now() - Mapper.Reservation.date_reservation_created > func.make_interval(0, 0, 0, Mapper.Concert.duration_cancelation, 0, 0)
        )
        return self.handle_reservations(SQL_CLOSE_UNPAID, Mapper.Reservation.cancel)

    def log_new_movements(self, reservation_dict: [], transaction_dict: []):
        log_file_path = open(self.log_file_path, 'a')

        for reason, reservations in reservation_dict.items():
            for r in reservations:
                log_file_path.write(reason)
                log_file_path.write('\t')
                log_file_path.write(r.to_csv('\t'))
                log_file_path.write('\n')


    def log_current_states_to_file(self):
        if not os.path.isdir(SNAPSHOT_FOLDER):
            os.mkdir(SNAPSHOT_FOLDER)

        with open(os.path.join(SNAPSHOT_FOLDER, 'RESERVATIONS_{}.csv'.format(datetime.now().strftime('%Y_%m_%d.%H.%M'))), 'w') as res_dump:
            res = self.db.session.execute(sql.select(Mapper.Reservation))
            out_csv = csv.writer(res_dump, delimiter='\t')
            [out_csv.writerow(Mapper.Reservation.__table__.columns.keys())]
            [out_csv.writerow([getattr(curr, column.name) for column in Mapper.Reservation.__mapper__.columns]) for curr, in res]

        with open(os.path.join(SNAPSHOT_FOLDER, 'TRANSACTION_{}.csv'.format(datetime.now().strftime('%Y_%m_%d.%H.%M'))), 'w') as res_dump:
            res = self.db.session.execute(sql.select(Mapper.Transaction))
            out_csv = csv.writer(res_dump, delimiter='\t')
            [out_csv.writerow(Mapper.Transaction.__table__.columns.keys())]
            [out_csv.writerow([getattr(curr, column.name) for column in Mapper.Transaction.__mapper__.columns]) for curr, in res]

        with open(os.path.join(SNAPSHOT_FOLDER, 'CONCERTS_{}.csv'.format(datetime.now().strftime('%Y_%m_%d.%H.%M'))), 'w') as res_dump:
            res = self.db.session.execute(sql.select(Mapper.Concert))
            out_csv = csv.writer(res_dump, delimiter='\t')
            [out_csv.writerow(Mapper.Concert.__table__.columns.keys())]
            [out_csv.writerow([getattr(curr, column.name) for column in Mapper.Concert.__mapper__.columns]) for curr, in res]



def main():
    checker = Checker(ng_id=API_SECRETS['SECRET_ID'], ng_key=API_SECRETS['SECRET_KEY'], ng_refresh_token=API_SECRETS['REFRESH_TOKEN'], ng_account=API_SECRETS['ACCOUNT_TOKEN'],
                      db_connector=DB_URL, log_file_path=CHECKER_LOG_FILE)
    # get newly (non-activated) opened reservations
    res_new = checker.sight_new_reservations()
    # set activated reservations to open reservations # this is kinda stupid.
    res_open = checker.set_activated_reservations_to_open()

    # get transactions from nordigen_db
    try:
        nordigen_transactions = checker.get_transactions_from_nordigen()
        new_valid_transactions = checker.add_transactions_to_db(nordigen_transactions)
    except HTTPError as http_error:
        nordigen_transactions = []
        new_valid_transactions = []
        print(http_error)

    # finalize and handle open reservations
    res_finalized = checker.finalize_paid_reservations()
    res_overpaid = checker.finalize_overpaid_reservations()
    res_underpaid = checker.dispute_underpaid_reservations()
    res_not_confirmed = checker.close_unconfirmed_reservations()
    res_canceled_paid = checker.check_payment_of_canceled_res()
    res_reminded = checker.remind_reservations()
    res_closed = checker.close_old_unpaid_reservations()

    checker.log_new_movements(
        {
            "New Reservations": res_new,
            "Activated Reservations": res_open,
            "Finalized Reservations": res_finalized,
            "Overpaid Reservations": res_overpaid,
            "Underpaid Reservations": res_underpaid,
            "Rejected Reservations 24h": res_not_confirmed,
            "Already closed, but paid Res": res_canceled_paid,
            "Reminded Reservations": res_reminded,
            "Closed Reservations": res_closed
        },
        {}
    )

    checker.log_current_states_to_file()


if __name__ == '__main__':
    main()
