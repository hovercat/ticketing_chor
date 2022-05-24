from flask_admin import expose

from constants import *
from frontend.CustomModelView import CustomModelView
from mapper import Mapper
from checker import Checker


class TransactionModelView(CustomModelView):
    form_ajax_refs = {
        'reservation': {
            'fields': ['user_name', 'user_email', 'tickets_full_price', 'tickets_student_price', 'payment_reference'],
            'page_size': 10
        }
    }

    form_choices = {
        'status':[
            ('valid', 'Valid'),
            ('invalid', 'Invalid (unrelated)')
        ]
    }

    column_searchable_list = (
        Mapper.transaction_table.c.keys()
    )

    column_filters = tuple(Mapper.transaction_table.c.keys())

    @expose('/call_bank_api')
    def add_transactions_to_bank(self):
        checker = Checker(ng_id=API_SECRETS['SECRET_ID'], ng_key=API_SECRETS['SECRET_KEY'],
                          ng_refresh_token=API_SECRETS['REFRESH_TOKEN'], ng_account=API_SECRETS['ACCOUNT_TOKEN'],
                          db_connector=DB_URL, log_file_path=CHECKER_LOG_FILE)
        nordigen_trans = checker.get_transactions_from_nordigen()
        new_transactions = checker.add_transactions_to_db(nordigen_trans)

        return self.render(
            'admin/nordigen_transactions.jinja.html',
            t_valid=[trans for trans in new_transactions if trans.status == 'valid'],
            t_invalid=[trans for trans in new_transactions if trans.status == 'invalid']
        )
