from flask import Flask
from flask_restful import Api
from flask_marshmallow import Marshmallow
from os import getenv
from importlib import import_module

app = Flask(__name__)

api = Api(app)
ma = Marshmallow(app)

from nfmd.resources import submodules as resources

def gen_url(path):
    if path[:1] != "/":
        path = "/{}".format(path)
    return path

for resource in resources:
    res = import_module("nfmd.resources.{}".format(resource))
    path = gen_url(res.path)
    api.add_resource(getattr(res, resource), path, endpoint=res.endpoint)

@app.route(gen_url("/doc"))
def api_doc():
    return """
    <html>
        <head>
            <title>ReDoc</title>
            <!-- needed for adaptive design -->
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
        
            <!--
            ReDoc doesn't change outer page styles
            -->
            <style>
            body {
                margin: 0;
                padding: 0;
            }
            </style>
        </head>
        <body>
            <redoc spec-url="/spec.json"></redoc>
            <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"> </script>
        </body>
    </html>"""