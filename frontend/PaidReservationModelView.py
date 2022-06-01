import datetime

import sqlalchemy
from flask import flash, request, redirect
from flask_admin import expose
from flask_admin.actions import action
from flask_admin.model.template import LinkRowAction
from sqlalchemy import func, and_
from sqlalchemy.sql.functions import coalesce

from frontend.CustomModelView import CustomModelView
from frontend.ReservationModelView import ReservationModelView
from mapper import Mapper
from wtforms import validators as v


class PaidReservationModelView(ReservationModelView):
    def get_query(self):
        q = self.session.query(
            Mapper.Reservation
        ).join(Mapper.Concert).outerjoin(Mapper.Transaction).group_by(Mapper.Reservation, Mapper.Concert)


        exp_amount = Mapper.Concert.full_price * Mapper.Reservation.tickets_full_price + Mapper.Concert.student_price * Mapper.Reservation.tickets_student_price
        paid_amount = coalesce(func.sum(Mapper.Transaction.amount),0).label("paid")

        payment_filter = request.args.get('payment', None)
        if payment_filter == 'paid':
            q = q.having(exp_amount == paid_amount)
        elif payment_filter == 'unpaid':
            q = q.having(paid_amount == 0)
        elif payment_filter == 'strange':
            q = q.having(and_(paid_amount > 0, exp_amount != paid_amount))

        return q

    column_list = [
        'res_id',
        'concert_id',
        'user_email',
        'user_name',
        'payment_reference',
        'tickets_full_price',
        'tickets_student_price',
        'status',
        'expected_amount',
        'paid_amount'
    ]

    named_filter_urls = True
