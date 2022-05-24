from flask import url_for, request
from flask_admin import AdminIndexView
from flask_httpauth import HTTPBasicAuth
from werkzeug.utils import redirect


class AuthAdminIndexView(AdminIndexView):
    def __init__(self, auth: HTTPBasicAuth):
        super().__init__()
        self.auth=auth

    def is_accessible(self):
        return self.auth.get_auth()

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('login'))

    pass
