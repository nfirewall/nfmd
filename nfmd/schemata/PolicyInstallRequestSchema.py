from marshmallow import fields, validate

from app import ma

class PolicyInstallRequestSchema(ma.Schema):
    policy_uuid = fields.UUID(required=True, description="Policy UUID")
    target_uuid = fields.List(fields.UUID(), required=True, description="Installation Targets")
    