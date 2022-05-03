from sqlalchemy.orm import Session, registry, relationship
import sqlalchemy as db
from sqlalchemy import Column, String, Integer, Boolean, Date, Table, ForeignKey, Float, orm
import hashlib


class Mapper:
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
        Column('date_concert', Date)
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
        Column('finalized', Boolean),
        Column('canceled', Boolean),
    )

    class Reservation:
        @orm.reconstructor
        def reconstructor(self):
            self.payment_reference = hashlib.sha1(str(self.res_id).encode()).hexdigest()[:10]

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
        Column('handled', Boolean),
        Column('bank_transaction_id', String)
    )

    class Transaction:
        pass

    mapper_registry.map_imperatively(Transaction, transaction_table)
    mapper_registry.map_imperatively(Reservation, reservation_table, properties={'transactions':relationship(Transaction, backref='reservation', order_by=transaction_table.c.transaction_id)})
    mapper_registry.map_imperatively(Concert, concert_table, properties={'reservations':relationship(Reservation, backref='concert', order_by=reservation_table.c.res_id)})


    def __init__(self, dbconnector):
        self.engine = db.create_engine(dbconnector, connect_args={'options': '-csearch_path=ticketing'})  # schema name
        self.connection = self.engine.connect()
        self.metadata = db.MetaData()
        self.session = Session(self.engine)
