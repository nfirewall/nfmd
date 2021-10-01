from flask import request
from marshmallow.exceptions import ValidationError
from flask.views import MethodView
from nfmd.schemata import PolicyInstallRequestSchema
import requests
import os
from .. import parse_network_object, parse_service_object, recurse_service, recurse_network, convert_host_object, convert_network_object, sign_text
from requests.exceptions import ConnectionError
import json
import base64

path = 'policy_install'
endpoint = 'policy_install'

class PolicyInstallResource(MethodView):
    def post(self):
        """Install a specific policy package
        ---
        description: Install a specific policy package
        requestBody:
          content:
            application/json:
              schema: PolicyInstallRequestSchema
        responses:
          200:
            content:
              application/json:
                schema: 
                  type: object

        """
        
        json_data = request.get_json()
        try:
            data = PolicyInstallRequestSchema().load(json_data)
        except ValidationError as err:
            messages = []
            for msg in err.messages:
                messages.append("{}: {}".format(msg, ":".join(err.messages[msg])))
            return messages, 422
        uuid = data['policy_uuid']
        

        url = "{}/policies/{}".format(os.getenv("NMAPI_URI"), uuid)
        try:
            r = requests.get(url)
        except ConnectionError:
            return {"messages": ["Cannot contact nfmapi"]}, 504
        if r.status_code != 200:
            return {"messages": ["Invalid policy UUID: {}".format(uuid)]}
        
        policy = r.json()
        
        for firewall in data['target_uuid']:
            url = "{}/firewall_objects/{}".format(os.getenv("NMAPI_URI"), firewall)
            try:
                r = requests.get(url)
            except ConnectionError:
                return {"messages": ["Cannot contact nmapi"]}, 422
            if r.status_code != 200:
                return {"messages": ["Invalid firewall UUID: {}".format(firewall)]}
        
        service_objects = {}
        host_objects = {}
        network_objects = {}
        rulebase = []
        natrules = []

        # Get filter rules
        for rule_uuid in policy['filter_rules']:
            r = requests.get("{}/filter_rules/{}".format(os.getenv("NMAPI_URI"), rule_uuid))
            rule = r.json()
            use = {"tcp": False, "udp": False}
            newrule = {}
            newrule["tcp"] = {"protocol": "tcp", "sport": "any", "dport": [], "src": [], "dst": [], "interface": "any", "action": rule["action"], "id": rule_uuid}
            newrule["udp"] = {"protocol": "udp", "sport": "any", "dport": [], "src": [], "dst": [], "interface": "any", "action": rule["action"], "id": rule_uuid}
            if rule["service"]:
                for ruleservice in rule["service"]:
                    typ, obj = parse_service_object(ruleservice)
                    if typ == "service_group":
                        objs = recurse_service(obj)
                        for service in objs:
                            newrule[service["protocol"]]["protcol"] = service["protocol"]
                            newrule[service["protocol"]]["dport"].append(service["uuid"])
                            use[service["protocol"]] = True
                            service_objects[service["uuid"]] = {"name": service["uuid"], "type": service["protocol"], "value": service["dport"]}

                    else:
                        newrule[obj["protocol"]]["protocol"] = obj["protocol"]
                        newrule[obj["protocol"]]["dport"].append(obj["uuid"])
                        service_objects[obj["uuid"]] = {"name": obj["uuid"], "type": obj["protocol"], "value": obj["dport"]}
                        use[obj["protocol"]] = True
            else:
                use["tcp"] = True
                use["udp"] = True

            if rule["source"]:
                for rulesource in rule["source"]:
                    typ, obj = parse_network_object(rulesource)
                    if typ == "network_group":
                        hosts, nets = recurse_network(obj)
                        for hostobject in hosts:
                            host_objects[hostobject["uuid"]] = convert_host_object(hostobject)
                            newrule["tcp"]["src"].append(hostobject["uuid"])
                            newrule["udp"]["src"].append(hostobject["uuid"])
                        for networkobject in nets:
                            network_objects[networkobject["uuid"]] = convert_network_object(networkobject)
                            newrule["tcp"]["src"].append(networkobject["uuid"])
                            newrule["udp"]["src"].append(networkobject["uuid"])
                    elif typ == "host":
                        host_objects[obj["uuid"]] = convert_host_object(obj)
                        newrule["tcp"]["src"].append(obj["uuid"])
                        newrule["udp"]["src"].append(obj["uuid"])
                    elif typ == "network":
                        network_objects[obj["uuid"]] = convert_network_object(obj)
                        newrule["tcp"]["src"].append(obj["uuid"])
                        newrule["udp"]["src"].append(obj["uuid"])
                    
                
            if rule["destination"]:
                for ruledestination in rule["destination"]:
                    typ, obj = parse_network_object(ruledestination)
                    if typ == "network_group":
                        hosts, nets = recurse_network(obj)
                        for hostobject in hosts:
                            host_objects[hostobject["uuid"]] = convert_host_object(hostobject)
                            newrule["tcp"]["dst"].append(hostobject["uuid"])
                            newrule["udp"]["dst"].append(hostobject["uuid"])
                        for networkobject in nets:
                            network_objects[networkobject["uuid"]] = convert_network_object(networkobject)
                            newrule["tcp"]["dst"].append(networkobject["uuid"])
                            newrule["udp"]["dst"].append(networkobject["uuid"])
                    elif typ == "host":
                        host_objects[obj["uuid"]] = convert_host_object(obj)
                        newrule["tcp"]["dst"].append(obj["uuid"])
                        newrule["udp"]["dst"].append(obj["uuid"])
                    elif typ == "network":
                        network_objects[obj["uuid"]] = convert_network_object(obj)
                        newrule["tcp"]["dst"].append(obj["uuid"])
                        newrule["udp"]["dst"].append(obj["uuid"])
            
            if use["tcp"]:
                if newrule["tcp"]["src"] == []:
                    newrule["tcp"]["src"] = "any"
                if newrule["tcp"]["dst"] == []:
                    newrule["tcp"]["dst"] = "any"
                if newrule["tcp"]["dport"] == []:
                    newrule["tcp"]["dport"] = "any"
                rulebase.append(newrule["tcp"])
            if use["udp"]:
                if newrule["udp"]["src"] == []:
                    newrule["udp"]["src"] = "any"
                if newrule["udp"]["dst"] == []:
                    newrule["udp"]["dst"] = "any"
                if newrule["udp"]["dport"] == []:
                    newrule["udp"]["dport"] = "any"
                rulebase.append(newrule["udp"])
        
        for rule_uuid in policy["nat_rules"]:
            r = requests.get("{}/nat_rules/{}".format(os.getenv("NMAPI_URI"), rule_uuid))
            rule = r.json()

            target = rule["target"]
            r = requests.get("{}/host_objects/{}".format(os.getenv("NMAPI_URI"), target))
            if r.status_code == 200:
                rule["target"] = r.json()["ipv6"] or r.json()["ipv4"]

            r = requests.get("{}/network_objects/{}".format(os.getenv("NMAPI_URI"), target))
            if r.status_code == 200:
                rule["target"] = r.json()["ipv6"] or r.json()["ipv4"]

            natrule = {"id": rule["uuid"], "type": rule["type"], "dport": rule["service"] or "any", "src": rule["source"] or "any", "dst": rule["destination"] or "any", "proto": "any", "target": rule["target"]}
            natrules.append(natrule)

        response = json.dumps({"rulebase": rulebase, "objects": {"services": service_objects, "hosts": host_objects, "networks": network_objects, "groups": {}}, "nat": natrules, "options": {"stateful": True, "default_drop": False, "allow_pings": True, "allow_local_pings": True}})
        sig = sign_text(response)
        return {"policy": base64.b64encode(response.encode("utf-8")).decode("utf-8"), "signature": sig.decode("utf-8")}
