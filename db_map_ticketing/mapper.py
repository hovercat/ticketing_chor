from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session, registry, relationship
import sqlalchemy as db
from sqlalchemy import Column, String, Integer, Boolean, Date, Table, ForeignKey, Float, orm
import hashlib


class Mapper:
    engine = None
    connection = None
    metadata = None
    session = None
    #Base = declarative_base()

    mapper_registry = registry()

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
        Column('date_paid', Date),
        Column('finalized', Boolean),
        Column('canceled', Boolean)
    )

    class Reservation:
        @orm.reconstructor
        def reconstructor(self):
            self.payment_reference = hashlib.sha1(str(self.res_id).encode()).hexdigest()[:10]

    mapper_registry.map_imperatively(Reservation, reservation_table)

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

    mapper_registry.map_imperatively(Concert, concert_table, properties={'reservations':relationship(Reservation, backref='concert', order_by=reservation_table.c.res_id)})


        # res_id = Column(Integer, primary_key=True)
        # concert_id = Column(Integer)
        # user_email = Column(String)
        # user_name = Column(String)
        # tickets_full_price = Column(Integer)
        # tickets_student_price = Column(Integer)
        # payment_reference = Column(String)
        # date_reservation_created = Column(Date)
        # date_email_activated = Column(Date)
        # date_paied = Column(Date)
        # finalized = Column(Boolean)
        # canceled = Column(Boolean)
        #
        # payment_reference = Column('payment_reference', String)
        #
        # def __init__(self, concert_id, user_email, user_name, tickets_full_price, tickets_student_price):
        #     self.concert_id = concert_id
        #     self.user_email = user_email
        #     self.user_name = user_name
        #     self.tickets_full_price = tickets_full_price
        #     self.tickets_student_price = tickets_student_price
        #    # self.payment_reference = hashlib.sha1(self.res_id)[:10]
        #
        # def generate_reference_value(self):
        #     try:
        #         self.payment_reference = hashlib.sha1(self.res_id.encode())[:10]
        #     except:
        #         print('Reservation ID not assigned yet')
        #         raise

    def __init__(self, dbconnector):
        self.engine = db.create_engine(dbconnector, connect_args={'options': '-csearch_path=ticketing'})  # schema name
        self.connection = self.engine.connect()
        self.metadata = db.MetaData()


       # self.Concert = self.Base.classes.concert
       # self.Reservation = self.Base.classes.reservation

        self.session = Session(self.engine)
