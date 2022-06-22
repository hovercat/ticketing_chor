import datetime

from flask import flash, request, redirect
from flask_admin import expose
from flask_admin.actions import action
from flask_admin.model import typefmt
from flask_admin.model.template import LinkRowAction
from sqlalchemy import and_
from sqlalchemy.sql.functions import coalesce, func

from frontend.CustomModelView import CustomModelView
from mapper import Mapper
from wtforms import validators as v


class ReservationModelView(CustomModelView):
    def get_query(self):
        q = self.session.query(
            Mapper.Reservation
        ).join(Mapper.Concert).outerjoin(Mapper.Transaction).group_by(Mapper.Reservation, Mapper.Concert)

        exp_amount = Mapper.Concert.full_price * Mapper.Reservation.tickets_full_price + Mapper.Concert.student_price * Mapper.Reservation.tickets_student_price
        paid_amount = coalesce(func.sum(Mapper.Transaction.amount), 0).label("paid")

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
        'date_reservation_created',
        'user_email',
        'user_name',
        'payment_reference',
        'tickets_full_price',
        'tickets_student_price',
        'status',
        'date_reminded',
        'expected_amount',
        'paid_amount'
    ]

    def date_format(view, value):
        return value.strftime('%d.%m.%Y %H:%S')

    column_type_formatters = dict(typefmt.BASE_FORMATTERS)
    column_type_formatters.update({datetime.date: date_format})

    column_sortable_list = column_list

    column_default_sort = ('res_id', True)

    named_filter_urls = True

    #  Gets called right when model has been updated/created
    def after_model_change(self, form, reservation: Mapper.Reservation, is_created):
        if is_created and reservation.status == 'finalized':
            reservation.set_payment_reference()
            for t in reservation.transactions:
                t.payment_reference = reservation.get_payment_reference()
                t.currency = 'EUR'
                t.payment_date = datetime.datetime.now()
            self.session.commit()
            reservation.finalize()
        else:
            pass

    @action('finalize_list', 'Finalize Reservations')
    def finalize_list(self, res_ids):
        for res_id in res_ids:
            flash(res_id)

    @expose('/mail', methods=['GET'])
    def mail_methods(self):
        id = request.args.get('id', None)
        if id is None:
            return 'No id given'

        qry = self.session.query(Mapper.Reservation).filter(Mapper.Reservation.res_id == id)
        result = self.session.execute(qry)
        res = result.first()[0]

        func = request.args.get('func')
        if func == 'activation_again':
            res.reserve()
        if func == 'activate':
            res.activate()
        elif func == 'finalize':
            res.finalize()
        elif func == 'cancel' and (res.status == 'new' or res.status == 'new_seen'):
            res.cancel_24h()
        elif func == 'cancel':
            res.cancel()
        elif func == 'remind':
            res.remind()
        self.session.commit()
        return redirect('/admin/reservation')

    column_extra_row_actions = [
        LinkRowAction('glyphicon glyphicon-asterisk', 'mail?func=activation_again&id={row_id}', title='Send "Please activate"-Mail again'),
        LinkRowAction('glyphicon glyphicon-euro', 'mail?func=activate&id={row_id}', title='Activate AND Send Payment Details'),
        LinkRowAction('glyphicon glyphicon-question-sign', 'mail?func=remind&id={row_id}', title='Send Reminder Mail'),
        LinkRowAction('glyphicon glyphicon-check', 'mail?func=finalize&id={row_id}', title='Finalize AND Send Tickets'),
        LinkRowAction('glyphicon glyphicon-remove', 'mail?func=cancel&id={row_id}', title='Cancel AND Send Cancelation Mail')
    ]

    column_searchable_list = list(Mapper.reservation_table.c.keys())
    column_filters = tuple(Mapper.reservation_table.c.keys())

    form_choices = {
        'status':[
            ('open', 'Open Reservation'),
            ('finalized', 'Finalized Reservation'),
            ('new', '* New Reservation'),
            ('new_seen', '* Seen new Reservation'),
            ('activated', '* Email activated reservation'),
            ('canceled', '* Canceled Reservation'),
            ('disputed', '* Disputed Reservation'),
            ('*', '* DO NOT CHOOSE STARRED *'),
        ]
    }

    form_args = {
        'user_email': { 'validators': [v.DataRequired(), v.Email()] },
        'user_name': { 'validators': [v.DataRequired()] },
        'tickets_full_price':  { 'default': 0, 'validators': [v.InputRequired(), v.NumberRange(0, 50)]},
        'tickets_student_price':  { 'default': 0, 'validators': [v.InputRequired(), v.NumberRange(0, 50)]},
        'status': { 'validators': [v.DataRequired()]},
        'concert': { 'validators': [v.DataRequired()]},
        'transactions': { 'validators': []},
    }

    form_ajax_refs = {
        'transactions': {
            'fields':  ['amount', 'payment_reference'],
            'page_size': 10
        }
    }

    form_excluded_columns = [
        'date_reservation_created', # todo set to today somehow? db?
        'date_email_activated',
        'date_reminded',
        'pay_state',
        'payment_reference'
    ]

    inline_models = [(
        Mapper.Transaction,
        dict(
            form_columns=['transaction_id', 'amount', 'debtor_name'],
            form_args=dict(
                amount={'validators': [v.DataRequired(), v.NumberRange(0)]},
                debtor_name={'default': 'barzahlung', 'validators': [v.DataRequired()]}
            )
        )
    )]



