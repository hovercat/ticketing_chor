from flask import url_for, request
from flask_admin.contrib.sqla import ModelView
from flask_httpauth import HTTPBasicAuth
from werkzeug.utils import redirect


class CustomModelView(ModelView):
    def __init__(self, model, session, auth: HTTPBasicAuth, **kwargs):
        super().__init__(model, session, **kwargs)
        self.auth = auth

    def is_accessible(self):
        return self.auth.get_auth()

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('login'))

    can_delete = False
    can_edit = True
    can_create = True
    can_export = True
    # can_view_details = True
