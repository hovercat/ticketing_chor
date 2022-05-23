from flask_admin.contrib.sqla import ModelView

class ReservationModelView(ModelView):
    can_delete = False
    can_edit = True
    can_create = True
    can_export = True
    #can_view_details = True

    form_ajax_refs = {
        'transactions': {
            'fields':  ['amount', 'payment_reference'],
            'page_size': 10
        }
    }



