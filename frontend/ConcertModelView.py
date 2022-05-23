from flask_admin.contrib.sqla import ModelView

from mapper import Mapper


class ConcertModelView(ModelView):
    can_delete = False
    can_edit = True
    can_create = True
    can_export = True

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



