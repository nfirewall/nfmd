from flask.views import MethodView
from flask import request

class BaseResource(MethodView):
    _allowed_content_types = ['application/json']

    def dispatch_request(self, *args, **kwargs):
        if not self._check_method():
            return "Invalid Content-Type", 400
        return super(BaseResource, self).dispatch_request(*args, **kwargs)

    def _check_method(self):
        meth = request.method.lower()
        if meth in ['get', 'head', 'delete']:
            return True
        if request.content_type in self._allowed_content_types:
            return True
        return False