from flask_admin.contrib.sqla import ModelView

class CustomModelView(ModelView):
    can_delete = False
    can_edit = True
    can_create = True
    can_export = True
    #can_view_details = True




