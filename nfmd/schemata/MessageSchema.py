from marshmallow import fields, Schema

class MessageSchema(Schema):
    messages = fields.List(fields.String(), description='Response messages')