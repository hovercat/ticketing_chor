from datetime import datetime, timedelta


import sqlalchemy.sql
from sqlalchemy.orm import Session, registry, relationship, sessionmaker
import sqlalchemy as db
from sqlalchemy import Column, String, Integer, Date, Table, ForeignKey, Float, TIMESTAMP
import hashlib

from Mailgod import Mailgod
from constants import DB_OPTIONS
import locale

locale.setlocale(locale.LC_ALL, locale.getdefaultlocale())  # TODO boese hier
#locale.setlocale(locale.LC_ALL, 'de_AT.UTF-8')
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
        Column('concert_id', Integer, primary_key=True, nullable=False, autoincrement=False),
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
        def get_reserved_tickets(self):
            return list(filter(lambda res: res.status in ['open', 'open_reminded', 'finalized', 'new', 'disputed'],
                               self.reservations))

        def get_reserved_tickets_amount(self):
            return sum(res.tickets_full_price + res.tickets_student_price for res in self.get_reserved_tickets())

        def get_sold_tickets(self):
            return list(filter(lambda res: res.status in ['finalized'], self.reservations))

        def get_sold_tickets_amount(self):
            return sum(res.tickets_full_price + res.tickets_student_price for res in self.get_sold_tickets())

        def get_available_tickets_amount(self):
            return self.total_tickets - self.get_reserved_tickets_amount()

        def get_concert_date(self):
            return self.date_concert.strftime('%d.%m.%Y')

        def get_concert_time(self):
            return self.date_concert.strftime('%H:%M')

        def get_latest_possible_payment_date(self):
            # TODO!
            pass

        def get_student_price_eur(self):
            return locale.currency(self.student_price)

        def get_full_price_eur(self):
            return locale.currency(self.full_price, '€')

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
        Column('date_reservation_created', TIMESTAMP),
        Column('date_email_activated', TIMESTAMP),
        Column('date_reminded', TIMESTAMP),
        Column('status', String),
        Column('pay_state', String)
    )

    class Reservation:

        # @orm.reconstructor
        # def reconstructor(self):
        #     self.payment_reference = self.get_payment_reference()

        def set_payment_reference(self):
            self.payment_reference = self.get_payment_reference()

        def get_payment_reference(self):
            return hashlib.sha1(str(self.res_id).encode()).hexdigest()[:10]

        def get_expected_amount(self):
            return self.tickets_full_price * self.concert.full_price + \
                   self.tickets_student_price * self.concert.student_price

        def get_expected_amount_eur(self):
            return locale.currency(self.get_expected_amount(), '€')

        def get_paid_amount(self):
            return sum(payment.amount for payment in self.transactions)

        def get_reservation_date(self):
            return self.date_reservation_created.strftime('%d.%m.%Y')

        def get_latest_possible_payment_date(self):
            return (self.date_reservation_created + timedelta(days=self.concert.duration_cancelation)).strftime(
                '%d.%m.%Y')

        def send_mail(self, message, subject, receivers):
            mailgod.send_mail(
                receivers,
                _message=message,
                _subject=subject
            )

        def send_mail_user(self, mail_template_path, subject, extra_msg = None):
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
                latest_date=self.concert.get_latest_possible_payment_date(),
                latest_payment_date=self.concert.get_latest_possible_payment_date(),
                reservation_date=self.get_reservation_date(),  # TODO MAKE BEATIFUL
                payment_reference=self.get_payment_reference(),
                total=self.get_expected_amount_eur()
            )
            self.send_mail(mail_msg, subject, [self.user_email])

            if extra_msg:
                self.send_mail_managers(extra_msg, extra_msg)


        def send_mail_managers(self, message, subject):
            self.send_mail(message, subject, mailgod.mail_sale_managers)

        def reserve(self):
            self.status = 'new'
            self.send_mail_user(
                "email_templates/activate.html",
                subject='Ihre Buchung TU Wien Chor Konzert am {date} - Bitte bestätigen'.format(date=self.get_reservation_date())
            )

        def sight_new_res(self):
            self.status = 'new_seen'

        def set_to_open(self):
            self.status = 'open'

        def activate(self):
            self.status = 'activated'
            self.send_mail_user(
                "email_templates/activated.html",
                subject='Ihre Buchung TU Wien Chor Konzert am {date} - Bezahlung'.format(date=self.get_reservation_date())
            )

        def finalize(self, extra_msg =''):
            self.status = 'finalized'
            self.send_mail_user(
                "email_templates/finalize.html",
                subject='Ihre Buchung TU Wien Chor Konzert am {date} - Zahlung erfolgt'.format(date=self.get_reservation_date()),
                extra_msg = extra_msg
            )

        def remind(self):
            self.status = 'open_reminded'
            self.send_mail_user(
                "email_templates/reminder.html",
                subject='Erinnerung: Ihre Buchung TU Wien Chor Konzert am {date} - Bezahlung'.format(date=self.get_reservation_date())
            )

        def cancel(self):
            self.status = 'canceled'
            self.send_mail_user(
                "email_templates/cancelation.html",
                subject='Ihre Buchung TU Wien Chor Konzert am {date} - Reservierung verfallen'.format(date=self.get_reservation_date())
            )

        def cancel_24h(self):
            self.status = 'canceled'
            self.send_mail_user(
                "email_templates/cancelation_24h.html",
                subject='Ihre Buchung TU Wien Chor Konzert am {date} - Reservierung verfallen'.format(date=self.get_reservation_date())
            )

        def dispute(self, msg: str, send_mail=False, status='disputed'):
            self.status = status
            if send_mail and len(mailgod.mail_sale_managers) > 0:
                mailgod.send_mail(
                    mailgod.mail_sale_managers,
                    _subject='Disputed Reservation',
                    _message=msg
                )

        def to_csv(self, sep=' ', header=False):
            return sep.join(
                self.res_id,
                self.payment_reference,
                self.get_expected_amount(),
                self.get_paid_amount(),
                self.concert_id,
                self.user_email,
                self.user_name,
                self.tickets_full_price,
                self.tickets_student_price,
                self.get_reservation_date(),
                self.get_latest_possible_payment_date(),
                self.status
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
        pass

    mapper_registry.map_imperatively(Reservation, reservation_table, properties={
        'transactions': relationship(Transaction, backref='reservation', order_by=transaction_table.c.transaction_id),
        'concert': relationship(Concert, backref='reservations', order_by=transaction_table.c.transaction_id)
    })
    mapper_registry.map_imperatively(Transaction, transaction_table)#), properties={
    #    'reservation': relationship(Reservation, backref='transactions', order_by=transaction_table.c.transaction_id)
    #})

    mapper_registry.map_imperatively(Concert, concert_table)#, properties={
    #    'reservations': relationship(Reservation, backref='concert', order_by=reservation_table.c.res_id)})

    def get_concerts(self):
        concert_query = sqlalchemy.sql.select(Mapper.Concert) \
            .where(datetime.today() > Mapper.Concert.date_sale_start) \
            .where(datetime.today() < Mapper.Concert.date_sale_end)
        return [c for c, in self.session.execute(concert_query)]

    def get_reservation_by_payment_reference(self, payment_reference):
        res_query = sqlalchemy.sql.select(Mapper.Reservation) \
            .where(Mapper.Reservation.payment_reference == payment_reference)
        reservations = [r for r, in self.session.execute(res_query)]
        if len(reservations) > 0:
            return reservations[0]
        else:
            return None
