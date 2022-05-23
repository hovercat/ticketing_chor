import datetime

from sqlalchemy.engine import Transaction

from frontend.CustomModelView import CustomModelView
from mapper import Mapper
from wtforms import validators as v


class ReservationModelView(CustomModelView):
    can_delete = True
    can_edit = True
    can_create = True
    can_export = True
    #can_view_details = True

    def create_form(self):
        form = super(ReservationModelView, self).create_form()

        return form

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



