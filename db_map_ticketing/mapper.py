import enum

from sqlalchemy.orm import Session, registry, relationship
import sqlalchemy as db
from sqlalchemy import Column, String, Integer, Boolean, Date, Table, ForeignKey, Float, orm, Enum
import hashlib


class Mapper:
    engine = None
    connection = None
    metadata = None
    session = None
    mapper_registry = registry()

    class Reservation_Status(enum.Enum):
        open = 1
        canceled = 2
        finalized = 3
        open_reminded = 4
        disputed = 5

    class Reservation_Payment_Status(enum.Enum):
        none = 1
        exact = 2
        too_little = 3
        too_much = 4
        too_late = 5

    payment_status_table = Table(
        'payment_status',
        mapper_registry.metadata,
        Column('ps_id', Integer, primary_key=True, nullable=False),
        Column('status', String)
    )

    class Payment_Status:
        pass

    reservation_status_table = Table(
        'reservation_status',
        mapper_registry.metadata,
        Column('rs_id', Integer, primary_key=True, nullable=False),
        Column('status', String)
    )

    class Reservation_Status:
        pass

    reservation_payment_status_table = Table(
        'reservation_payment_status',
        mapper_registry.metadata,
        Column('rps_id', Integer, primary_key=True, nullable=False),
        Column('status', String)
    )

    class Reservation_Payment_Status:
        pass

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
        Column('tickets_available', Integer)
    )

    class Concert:
        pass

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
        # Column('status', Integer, ForeignKey('reservation_status.rs_id')),
        # Column('pay_state', Integer, ForeignKey('reservation_payment_status.rps_id'))
        Column('status', String),
        Column('pay_state', String)
    )

    class Reservation:
        @orm.reconstructor
        def reconstructor(self):
            self.payment_reference = hashlib.sha1(str(self.res_id).encode()).hexdigest()[:10]

        def get_expected_amount(self):  # TODO test
            return self.tickets_full_price * self.concert.full_price + \
                   self.tickets_students_price * self.concert.student_price

        def get_paid_amount(self):  # TODO test
            return sum(payment.amount for payment in self.transactions)

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

    mapper_registry.map_imperatively(Payment_Status, payment_status_table)
    mapper_registry.map_imperatively(Reservation_Status, reservation_status_table)
    mapper_registry.map_imperatively(Reservation_Payment_Status, reservation_payment_status_table)
    mapper_registry.map_imperatively(Transaction, transaction_table) #properties={
    #    'payment_status': relationship(Payment_Status, backref='transactions')
    #})
    mapper_registry.map_imperatively(Reservation, reservation_table, properties={
        'transactions': relationship(Transaction, backref='reservation', order_by=transaction_table.c.transaction_id)#,
      #  'reservation_status': relationship(Reservation_Status, backref='reservations'),
      #  'reservation_payment_status': relationship(Reservation_Payment_Status, backref='reservations')
    })
    mapper_registry.map_imperatively(Concert, concert_table, properties={
        'reservations': relationship(Reservation, backref='concert', order_by=reservation_table.c.res_id)})

    def __init__(self, dbconnector):
        self.engine = db.create_engine(dbconnector, connect_args={'options': '-csearch_path=ticketing'})  # schema name
        self.connection = self.engine.connect()
        self.metadata = db.MetaData()
        self.session = Session(self.engine, autoflush=False)
