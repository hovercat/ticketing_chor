import enum
from datetime import datetime

import sqlalchemy.sql
from flask import render_template
from sqlalchemy.orm import Session, registry, relationship
import sqlalchemy as db
from sqlalchemy import Column, String, Integer, Boolean, Date, Table, ForeignKey, Float, orm, Enum
import hashlib

from mailgod.Mailgod import Mailgod


class Mapper:
    def __init__(self, dbconnector):
        self.engine = db.create_engine(dbconnector, connect_args={'options': '-csearch_path=ticketing'})  # schema name
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
        Column('date_concert', Date),
        Column('date_sale_start', Date),
        Column('date_sale_end', Date),
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
        Column('date_reservation_created', Date),
        Column('date_email_activated', Date),
        Column('date_reminded', Date),
        Column('status', String),
        Column('pay_state', String)
    )

    class Reservation:
        @orm.reconstructor
        def reconstructor(self):
            self.payment_reference = hashlib.sha1(str(self.res_id).encode()).hexdigest()[:10]

        def get_expected_amount(self):  # TODO test
            return self.tickets_full_price * self.concert.full_price + \
                   self.tickets_student_price * self.concert.student_price

        def get_paid_amount(self):  # TODO test
            return sum(payment.amount for payment in self.transactions)

        def reserve(self, mailgod: Mailgod):
            pass

        def finalize(self, mailgod: Mailgod):
            self.status = 'finalized'
            with open("email_templates/finalize.html", 'r') as mail_template:
                mail_template_text = ''.join(mail_template.readlines())
                mail_msg = mail_template_text.format(
                    name=self.user_name,
                    tickets=self.tickets_full_price + self.tickets_student_price,
                    concert_name=self.concert.concert_title
                )
                mailgod.send_mail(
                    [self.user_email],
                    _subject='Tickets sind bezahlt!',
                    _message=mail_msg
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

    mapper_registry.map_imperatively(Transaction, transaction_table)
    mapper_registry.map_imperatively(Reservation, reservation_table, properties={
        'transactions': relationship(Transaction, backref='reservation', order_by=transaction_table.c.transaction_id)
    })
    mapper_registry.map_imperatively(Concert, concert_table, properties={
        'reservations': relationship(Reservation, backref='concert', order_by=reservation_table.c.res_id)})

    def get_concerts(self):
        concert_query = sqlalchemy.sql.select(Mapper.Concert) \
            .where(datetime.today() > Mapper.Concert.date_sale_start) \
            .where(datetime.today() < Mapper.Concert.date_sale_end)
        return [c for c, in self.session.execute(concert_query)]
