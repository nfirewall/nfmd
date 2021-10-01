from flask import jsonify
from flask.views import MethodView

path = '/spec.json'
endpoint = 'api_spec'
exclude_from_doc = True

class SpecificationResource(MethodView):
    def get(self):
        """Get API Specification
        ---
        description: Get the specification of the API
        responses:
          200:
            content:
              application/json:
                schema: 
                  type: object

        """
        from genapispec import gen_spec
        
        return jsonify(gen_spec().to_dict())