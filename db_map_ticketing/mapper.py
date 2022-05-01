import sqlalchemy as db

engine = None
connection = None
metadata = None

def create_engine(dbconnector):
    global engine
    engine = db.create_engine(dbconnector)
    global connection
    connection = engine.connect()
    global metadata
    metadata = db.MetaData()

