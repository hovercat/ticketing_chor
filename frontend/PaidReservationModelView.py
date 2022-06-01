import datetime

from flask import flash, request, redirect
from flask_admin import expose
from flask_admin.actions import action
from flask_admin.model.template import LinkRowAction

from frontend.CustomModelView import CustomModelView
from mapper import Mapper
from wtforms import validators as v


class ReservationModelView(CustomModelView):
    def get_query(self):
        query = self.session.query(self.model)
        status_filter = request.args.get('status', None)
        if status_filter == 'finalized':
            query = query.filter(self.model.status == 'finalized')
        elif status_filter == 'closed':
            query = query.filter(self.model.status == 'closed')
        elif status_filter == 'disputed':
            query = query.filter(self.model.status == 'disputed')
        elif status_filter == 'open':
            query = query.filter(self.model.status.in_(['open', 'open_reminded', 'new', 'activated', 'new_seen']))

        return query

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
        if func == 'activate':
            res.activate()
        elif func == 'finalize':
            res.finalize()
        elif func == 'cancel' and (res.status == 'new' or res.status == 'new_seen') and (datetime.datetime.now() - res.date_reservation_created) > datetime.timedelta(hours=24):
            res.cancel_24h()
        elif func == 'cancel':
            res.cancel()
        elif func == 'remind':
            res.remind()
        self.session.commit()
        return redirect('/admin/reservation')

    column_extra_row_actions = [
        LinkRowAction('glyphicon glyphicon-euro', 'mail?func=activate&id={row_id}', title='Activate AND Send Payment Details'),
        LinkRowAction('glyphicon glyphicon-question-sign', 'mail?func=remind&id={row_id}', title='Send Reminder Mail'),
        LinkRowAction('glyphicon glyphicon-check', 'mail?func=finalize&id={row_id}', title='Finalize AND Send Tickets'),
        LinkRowAction('glyphicon glyphicon-remove', 'mail?func=cancel&id={row_id}', title='Cancel AND Send Cancelation Mail')
    ]

    column_searchable_list = list(Mapper.reservation_table.c.keys())
    column_filters = tuple(Mapper.reservation_table.c.keys())
    column_list = list(Mapper.reservation_table.c.keys()) + ['expected_amount', 'paid_amount']

    form_choices = {
        'status':[
            ('open', 'Open Reservation'),
            ('finalized', 'Finalized Reservation')
        ]
    }

    form_args = {
        'user_email': { 'validators': [v.DataRequired(), v.Email()] },
        'user_name': { 'validators': [v.DataRequired()] },
        'tickets_full_price':  { 'default': 0, 'validators': [v.InputRequired(), v.NumberRange(0, 50)]},
        'tickets_student_price':  { 'default': 0, 'validators': [v.InputRequired(), v.NumberRange(0, 50)]},
        'status': { 'validators': [v.DataRequired()]},
        'concert': { 'validators': [v.DataRequired()]},
        'transactions': { 'validators': [v.DataRequired()]},
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



