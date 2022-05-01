from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
import sqlalchemy as db


class Mapper:
    engine = None
    connection = None
    metadata = None
    session = None
    Base = None
    Concert = None
    Reservation = None

    def __init__(self, dbconnector):
        self.engine = db.create_engine(dbconnector, connect_args={'options': '-csearch_path=ticketing'}) # schema name
        self.connection = self.engine.connect()
        self.metadata = db.MetaData()

        self.Base = automap_base()
        self.Base.prepare(self.engine, reflect=True)

        self.Concert = self.Base.classes.concert
        self.Reservation = self.Base.classes.reservation

        self.session = Session(self.engine)
