from frontend.CustomModelView import CustomModelView
from mapper import Mapper


class ConcertModelView(CustomModelView):
    column_list = [
        'concert_title',
        'concert_location',
        'date_concert',
        'date_sale_start',
        'date_sale_end',
        'full_price',
        'student_price',
        'duration_reminder',
        'duration_cancelation',
        'total_tickets',
        'available_tickets',
        'reserved_tickets_amount',
        'sold_tickets_amount',
        'sold_tickets_money',
    ]
    column_searchable_list = [
        'concert_title',
        'concert_location'
    ]
    column_filters = tuple(Mapper.concert_table.c.keys())
