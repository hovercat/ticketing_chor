# from db_map_ticketing.mapper import Mapper
#
# map = Mapper("postgresql://postgres@localhost:5432/choir_ticketing")
#
# concerts = map.session.query(map.Concert).all()
# concert = concerts[0]
# r = map.Reservation()
# r.user_name='asfd'
# r.user_email='asfd'
# r.concert = concert
# map.session.add(r)
# map.session.commit()
# r.reconstructor()
# map.session.commit()
# print(1)