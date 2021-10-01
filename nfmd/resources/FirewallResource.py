from nfmd.schemata import FirewallOnboardRequestSchema
from marshmallow.exceptions import ValidationError
from .BaseResource import BaseResource
from flask import request
from ipaddress import ip_address
import requests
import os
from requests.exceptions import ConnectionError
from netifaces import interfaces, ifaddresses, AF_INET, AF_INET6

path = 'firewalls'
endpoint = 'firewalls'


class FirewallResource(BaseResource):
    def post(self):
        """Onboard a firewall
        ---
        description: Onboard a firewall into the system
        tags:
          - Firewalls
        requestBody:
          content:
            application/json:
              schema: FirewallOnboardRequestSchema
        responses:
          201:
            description: Created
            content:
              application/json:
                schema: FirewallOnboardSchema
          422:
            description: Unprocessable Entity
            content:
              application/json:
                schema: MessageSchema
          500:
            description: Error
            content:
              application/json:
                schema: MessageSchema
        """
        messages = []
        error = False
        json_data = request.get_json()
        try:
            data = FirewallOnboardRequestSchema().load(json_data)
        except ValidationError as err:
            return err.messages, 422
        
        try:
            ip_address(data['address'])
        except ValueError:
            error = True
            messages.append("Invalid address specified")
        
        if error:
            return {"messages": messages}, 422

            
        ip_list = []
        for interface in interfaces():
            for link in ifaddresses(interface)[AF_INET] + ifaddresses(interface)[AF_INET6]:
                if link['addr'] not in ("127.0.0.1", "::1") and link['addr'][:4] != "fe80":
                    ip_list.append(link['addr'])
        
        # Now do the clever stuff and onboard the firewall
        url = "http://{}:18080/status".format(data['address'])
        try:
            r = requests.get(url)
        except ConnectionError:
            return {"messages": ["Unable to contact the firewall on {}".format(data['address'])]}, 422

        jsn = r.json()
        hostname = jsn["hostname"]

        try:
            with open("{}management_certificate.pem".format(os.getenv("CONFIG_DIR"))) as fh:
                management_cert = "\n".join(fh.readlines())
        except FileNotFoundError:
            return {"messages": ["management server not initialised"]}, 500

        postdata = {
            "name": data["name"],
            "primary_address": data["address"]
        }

        try:
            postdata["description"] = data["description"],
        except KeyError:
            data['description'] = None
        try:
            r = requests.post("{}/firewall_objects".format(os.getenv("NMAPI_URI")), json=postdata, headers={"Content-Type": "application/json"})
        except ConnectionError:
            return {"messages": ["Unable to contact nfmapi"]}, 400
        jsn = r.json()
        if r.status_code == 422:
            error = True
            for msg in jsn["messages"]:
                messages.append(msg)
        elif r.status_code == 200:
            pass
        else:
            error = True
            messages.append("Failed to onboard firewall object")

        if error:
            return {"messages": messages}, 422
        
        firewall_id = jsn["uuid"]
        print(data["passphrase"])


        jsn = {
            "management_addresses": ip_list,
            "secret": data["passphrase"],
            "management_certificate": management_cert
        }
        r = requests.post("http://{}:18080/onboarding".format(data['address']), json=jsn)
        
        if r.status_code != 200:
            print("Failing")
            requests.delete("{}/firewall_objects/{}".format(os.getenv("NMAPI_URI"), firewall_id))
            messages = ["unable to onboard firewall"]
            for msg in r.json()["messages"]:
                messages.append(msg)
            return {"messages": messages}, 422
        
        return {"messages": ["OK"]}