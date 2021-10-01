from apispec import APISpec, BasePlugin
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
import json
from app import app
from pprint import pprint

from importlib import import_module
from nfmd.schemata import submodules as schemata
from app import gen_url
from flask import Flask


from nfmd.resources import submodules as resources

def gen_spec():
    app = Flask(__name__)
    spec = APISpec(
        title="nfmd",
        version="1.0.0",
        openapi_version="3.0.2",
        info=dict(
            description="nfmd.\n"
            ""
            "# Introduction\n"
            "This API provides management functions for nfirewall",
            license=dict(
                name="MIT",
                url="https://www.mit.edu/~amini/LICENSE.md"
            ),
            contact=dict(
                name="API Support",
                url="https://github.com/nfirewall"
            )
        ),
        plugins=[FlaskPlugin(), MarshmallowPlugin()],
    )

    for schema in schemata:
        sch = import_module("nfmd.schemata.{}".format(schema))
        spec.components.schema(schema, schema=getattr(sch, schema))

    resource_views = {}
    for resource in resources:
        res = import_module("nfmd.resources.{}".format(resource))
        try:
            if (res.exclude_from_doc):
                continue
        except AttributeError:
            pass
        res_view = getattr(res, resource).as_view(gen_url(res.path))
        app.add_url_rule(gen_url(res.path), view_func=res_view)
        resource_views[resource] = res_view

    with app.test_request_context():
        for resource_name in resource_views:
            spec.path(view=resource_views[resource_name])

    return spec


if __name__ == "__main__":
    spec = gen_spec()
    f = open("spec.json", "w")
    f.write(json.dumps(spec.to_dict()))
    f.close()