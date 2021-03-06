import smtplib
from datetime import datetime, timedelta

import sqlalchemy.sql
from sqlalchemy.orm import Session, registry, relationship, sessionmaker
import sqlalchemy as db
from sqlalchemy import Column, String, Integer, Date, Table, ForeignKey, Float, TIMESTAMP, Boolean, func
import hashlib

from Mailgod import Mailgod
from constants import DB_OPTIONS
import locale

#locale.setlocale(locale.LC_ALL, locale.getdefaultlocale())  # TODO boese hier
locale.setlocale(locale.LC_ALL, 'de_AT.UTF-8')
mailgod = Mailgod()


class Mapper:
    def __init__(self, dbconnector, dboptions=DB_OPTIONS):
        # raise Exception(dbconnector, DB_OPTIONS)

        self.engine = db.create_engine(dbconnector, connect_args={'options': DB_OPTIONS})  # schema name
        self.session_factory = sessionmaker(self.engine)
        self.connection = self.engine.connect()
        self.metadata = db.MetaData()
        self.session = Session(self.engine, autoflush=False)

    engine = None
    connection = None
    metadata = None
    session = None
    mapper_registry = registry()

    concert_table = Table(
        'concert',
        mapper_registry.metadata,
        Column('concert_id', Integer, primary_key=True),
        Column('concert_title', String),
        Column('concert_location', String),
        Column('full_price', Float(2)),
        Column('student_price', Float(2)),
        Column('duration_reminder', Integer),
        Column('duration_cancelation', Integer),
        Column('date_concert', TIMESTAMP),
        Column('date_sale_start', TIMESTAMP),
        Column('date_sale_end', TIMESTAMP),
        Column('total_tickets', Integer)
    )

    class Concert:
        def __repr__(self):
            return f'{self.concert_title}: {self.get_concert_date()} at {self.get_concert_time()}'

        def get_reserved_tickets(self):
            return list(filter(lambda res: res.status in ['open', 'open_reminded', 'finalized', 'new', 'disputed', 'activated'],
                               self.reservations))

        @property
        def reserved_tickets_amount(self):
            return self.get_reserved_tickets_amount()

        def get_reserved_tickets_amount(self):
            return sum(res.tickets_full_price + res.tickets_student_price for res in self.get_reserved_tickets())

        def get_reserved_tickets_amount_money(self):
            return sum(res.tickets_full_price * res.concert.full_price + res.tickets_student_price * res.concert.student_price for res in self.get_reserved_tickets())

        def get_sold_tickets(self):
            return list(filter(lambda res: res.status in ['finalized'], self.reservations))

        @property
        def sold_tickets_amount(self):
            return self.get_sold_tickets_amount()

        def get_sold_tickets_amount(self):
            return sum(res.tickets_full_price + res.tickets_student_price for res in self.get_sold_tickets())

        @property
        def sold_tickets_money(self):
            return self.get_sold_tickets_amount_money()

        def get_sold_tickets_amount_money(self):
            return sum(res.tickets_full_price * res.concert.full_price + res.tickets_student_price * res.concert.student_price for res in self.get_sold_tickets())

        @property
        def available_tickets(self):
            return self.get_available_tickets_amount()

        def get_available_tickets_amount(self):
            return self.total_tickets - self.get_reserved_tickets_amount()

        def get_concert_date(self):
            return self.date_concert.strftime('%d.%m.%Y')

        def get_concert_time(self):
            return self.date_concert.strftime('%H:%M')

        def get_student_price_eur(self):
            return locale.currency(self.student_price)

        def get_full_price_eur(self):
            return locale.currency(self.full_price, '???')

    reservation_table = Table(
        'reservation',
        mapper_registry.metadata,
        Column('res_id', Integer, primary_key=True),
        Column('concert_id', Integer, ForeignKey('concert.concert_id')),
        Column('user_email', String),
        Column('user_name', String),
        Column('tickets_full_price', Integer),
        Column('tickets_student_price', Integer),
        Column('payment_reference', String),
        Column('date_reservation_created', TIMESTAMP, server_default=func.now()),
        Column('date_email_activated', TIMESTAMP),
        Column('date_reminded', TIMESTAMP),
        Column('status', String),
        Column('pay_state', String)
    )

    class Reservation:
        def __repr__(self):
            return f'{str(self.res_id)}: {self.user_name}/{self.user_email} kauft {str(self.tickets_full_price)} VP und {str(self.tickets_student_price)} SP Tickets.'
        # @orm.reconstructor
        # def reconstructor(self):
        #     self.payment_reference = self.get_payment_reference()

        def set_payment_reference(self):
            dt_creation = self.date_reservation_created
            dt_1970 = datetime(1970, 1, 1)
            seconds = (dt_creation - dt_1970).total_seconds()
            pre_hash = hashlib.sha1(str(seconds).encode()).digest()
            true_hash = hashlib.sha1(
                str(int.from_bytes(self.res_id * pre_hash, byteorder='little')).encode()).hexdigest()

            self.payment_reference = true_hash[:7]

        def get_payment_reference(self): # TODO test
            if not self.payment_reference:
                self.set_payment_reference()
            return self.payment_reference

        def get_expected_amount(self):
            return self.tickets_full_price * self.concert.full_price + \
                   self.tickets_student_price * self.concert.student_price

        @property
        def expected_amount(self):
            return self.get_expected_amount()

        def get_expected_amount_eur(self):
            return locale.currency(self.get_expected_amount(), '???')

        def get_paid_amount(self):
            return sum(payment.amount for payment in self.transactions)

        @property
        def paid_amount(self):
            return self.get_paid_amount()

        def get_reservation_date(self):
            return self.date_reservation_created.strftime('%d.%m.%Y')

        def get_latest_possible_payment_date(self):
            latest_date_duration = self.date_reservation_created + timedelta(days=self.concert.duration_cancelation)
            latest_date_concert = self.concert.date_concert - timedelta(days=2)

            latest_date_possible = latest_date_duration if latest_date_duration <= latest_date_concert else latest_date_concert

            return latest_date_possible.strftime(
                '%d.%m.%Y')

        def send_mail(self, message, subject, receivers, file_name=None):
            try:
                mailgod.send_mail(
                    receivers,
                    _message=message,
                    _subject=subject,
                    file_name=file_name
                )
            except smtplib.SMTPRecipientsRefused as e:
                raise e

        def send_mail_user(self, mail_template_path, subject, extra_msg=None, file_name=None):
            with open(mail_template_path, 'r', encoding='utf-8') as f:
                mail_template = ''.join(f.readlines())

            mail_msg = mail_template.format(
                user_name=self.user_name,
                concert_title=self.concert.concert_title,
                concert_date=self.concert.get_concert_date(),
                concert_time=self.concert.get_concert_time(),
                concert_location=self.concert.concert_location,
                tickets_full_price=self.tickets_full_price,
                tickets_student_price=self.tickets_student_price,
                concert_full_price=self.concert.get_full_price_eur(),
                concert_student_price=self.concert.get_student_price_eur(),
                latest_date=self.get_latest_possible_payment_date(),
                latest_payment_date=self.get_latest_possible_payment_date(),
                reservation_date=self.get_reservation_date(),  # TODO MAKE BEATIFUL
                payment_reference=self.get_payment_reference(),
                total=self.get_expected_amount_eur()
            )
            try:
                self.send_mail(mail_msg, subject, [self.user_email], file_name=file_name)
            except smtplib.SMTPRecipientsRefused as e:
                raise e

            if extra_msg:
                self.send_mail_managers(extra_msg, extra_msg)

        def send_mail_managers(self, message, subject):
            self.send_mail(message, subject, mailgod.mail_sale_managers)

        def reserve(self):
            self.status = 'new'

            try:
                self.send_mail_user(
                    "email_templates/activate.html",
                    subject='TU Wien Chor Konzert: Ihre Buchung vom {date} - Bitte best??tigen'.format(
                        date=self.get_reservation_date()),
                    file_name='NeueReservierung_{}_{}'.format(
                        #self.user_name,
                        self.payment_reference,
                        datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    )
                )
            except smtplib.SMTPRecipientsRefused as e:
                self.status = 'closed'  # email doesnt work!
                raise e

        def sight_new_res(self):
            self.status = 'new_seen'

        def set_to_open(self):
            self.status = 'open'

        def activate(self):
            self.status = 'activated'
            self.date_email_activated = datetime.now()

            self.send_mail_user(
                "email_templates/activated.html",
                subject='TU Wien Chor Konzert: Ihre Buchung vom {date} - Bezahlung'.format(
                    date=self.get_reservation_date()),
                file_name='Bezahlt_{}_{}'.format(
                    #self.user_name,
                    self.payment_reference,
                    datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                )
            )

        def finalize(self, extra_msg=''):
            self.status = 'finalized'
            self.send_mail_user(
                "email_templates/finalize.html",
                subject='TU Wien Chor Konzert: Ihre Buchung vom {date} - Zahlung erfolgt'.format(
                    date=self.get_reservation_date()),
                extra_msg=extra_msg,
                file_name='Finalisiert_{}_{}'.format(
                    #self.user_name,
                    self.payment_reference,
                    datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                )
            )

        def remind(self):
            self.status = 'open_reminded'
            self.date_reminded = datetime.now()
            self.send_mail_user(
                "email_templates/reminder.html",
                subject='Erinnerung: TU Wien Chor Konzert: Ihre Buchung vom {date} - Bezahlung'.format(
                    date=self.get_reservation_date()),
                file_name='Erinnerung_{}_{}'.format(
                    #self.user_name,
                    self.payment_reference,
                    datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                )
            )

        def cancel(self):
            self.status = 'canceled'
            self.send_mail_user(
                "email_templates/cancelation.html",
                subject='TU Wien Chor Konzert: Ihre Buchung vom {date} - Reservierung verfallen'.format(
                    date=self.get_reservation_date()),
                file_name='Canceled_{}_{}'.format(
                    #self.user_name,
                    self.payment_reference,
                    datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                )
            )

        def cancel_24h(self):
            self.status = 'canceled'
            self.send_mail_user(
                "email_templates/cancelation_24h.html",
                subject='TU Wien Chor Konzert: Ihre Buchung vom {date} - Reservierung verfallen'.format(
                    date=self.get_reservation_date()),
                file_name='Canceled24h_{}_{}'.format(
                    #self.user_name,
                    self.payment_reference,
                    datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                )
            )

        def dispute(self, msg: str, send_mail=False, status='disputed'):
            self.status = status
            if send_mail and len(mailgod.mail_sale_managers) > 0:
                mailgod.send_mail(
                    mailgod.mail_sale_managers,
                    _subject='Disputed Reservation',
                    _message=msg,
                    file_name='DISPUTE_{}_{}'.format(
                        #self.user_name,
                        self.payment_reference,
                        datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    )
                )

        def to_csv(self, sep=' ', header=False):
            return sep.join([
                str(self.res_id),
                self.payment_reference,
                str(self.get_expected_amount()),
                str(self.get_paid_amount()),
                str(self.concert_id),
                self.user_email,
                self.user_name,
                str(self.tickets_full_price),
                str(self.tickets_student_price),
                self.get_reservation_date(),
                self.get_latest_possible_payment_date(),
                self.status]
            )

    transaction_table = Table(
        'transaction',
        mapper_registry.metadata,
        Column('transaction_id', Integer, primary_key=True),
        Column('res_id', Integer, ForeignKey('reservation.res_id')),
        Column('payment_reference', String),
        Column('currency', String),
        Column('amount', Float(2)),
        Column('debtor_iban', String),
        Column('debtor_name', String),
        Column('payment_date', Date),
        Column('bank_transaction_id', String),
        # Column('status', Integer, ForeignKey('payment_status.ps_id'))
        Column('status', String)
    )

    class Transaction:
        def __repr__(self):
            if self.reservation:
                return f'Transaction {self.transaction_id}: by {self.debtor_name}, amount: {self.amount} for Reservation: {self.reservation}'
            else:
                return f'Transaction {self.transaction_id}: by {self.debtor_name}, amount: {self.amount}; no reservation found'


    mapper_registry.map_imperatively(Reservation, reservation_table, properties={
        'transactions': relationship(Transaction, backref='reservation', order_by=transaction_table.c.transaction_id),
        'concert': relationship(Concert, backref='reservations', order_by=reservation_table.c.res_id)
    })
    mapper_registry.map_imperatively(Transaction, transaction_table)  # ), properties={
    #    'reservation': relationship(Reservation, backref='transactions', order_by=transaction_table.c.transaction_id)
    # })

    mapper_registry.map_imperatively(Concert, concert_table )#, properties={
        #'reservations': relationship(Reservation, backref='concert', order_by=reservation_table.c.res_id)}
    #)

    def get_concerts(self):
        concert_query = sqlalchemy.sql.select(Mapper.Concert) #\
#            .where(datetime.today() > Mapper.Concert.date_sale_start) \
#            .where(datetime.today() < Mapper.Concert.date_sale_end)
        return [c for c, in self.session.execute(concert_query)]

    def get_reservation_by_payment_reference(self, payment_reference):
        res_query = sqlalchemy.sql.select(Mapper.Reservation) \
            .where(Mapper.Reservation.payment_reference == payment_reference)
        reservations = [r for r, in self.session.execute(res_query)]
        if len(reservations) > 0:
            return reservations[0]
        else:
            return None

    post_token_table = Table(
        'post_tokens',
        mapper_registry.metadata,
        Column('pt_id', Integer, primary_key=True),
        Column('token', String),
        Column('token_time', TIMESTAMP),
        Column('what_for', String),
        Column('used', Boolean)
    )

    class Post_Token:
        def gen_token(self):
            if not self.token:
                self.token = hashlib.sha1(str(datetime.now()).encode()).hexdigest()[:20]
            return self.token

        def is_valid(self):
            return not self.used and self.token_time + timedelta(hours=2) > datetime.now()

        def invalidate(self):
            self.used = True

    mapper_registry.map_imperatively(Post_Token, post_token_table)

    def invalidate_token(self, token):
        tokens = self.session.execute(sqlalchemy.sql.select(Mapper.Post_Token).where(Mapper.Post_Token.token==token))
        tokens = [t[0] for t in tokens]
        if len(tokens) <= 0:
            return False

        t = tokens[0]
        if not t.is_valid():
            return False

        t.invalidate()
        self.session.commit()
        return True

        return False
