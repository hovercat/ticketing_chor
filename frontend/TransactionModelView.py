from frontend.CustomModelView import CustomModelView


class TransactionModelView(CustomModelView):
    can_delete = False
    can_edit = True
    can_create = True
    can_export = True
    #can_view_details = True

    form_ajax_refs = {
        'reservation': {
            'fields':  ['user_name', 'user_email', 'tickets_full_price', 'tickets_student_price', 'payment_reference'],
            'page_size': 10
        }
    }



