from marshmallow import fields, validate

from app import ma

class FirewallOnboardRequestSchema(ma.Schema):
    name = fields.String(required=True, description="Firewall Name")
    description = fields.String(required=False, description="Description")
    address = fields.String(required=True, description="IP address")
    passphrase = fields.String(required=True, description="Secret passphrase configured on the firewall")
    