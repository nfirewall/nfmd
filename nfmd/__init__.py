import requests
import os

def convert_hostnet_object(obj, type):
    outobj = {"name": obj["uuid"]}
    if obj["ipv4"] and obj["ipv6"]:
        outobj["type"] = "{}v4v6".format(type)
        outobj["valuev4"] = obj["ipv4"]
        outobj["valuev6"] = obj["ipv6"]
    elif obj["ipv4"]:
        outobj["type"] = "{}v4".format(type)
        outobj["valuev4"] = obj["ipv4"]
    elif obj["ipv6"]:
        outobj["type"] = "{}v6".format(type)
        outobj["valuev6"] = obj["ipv6"]
    
    return outobj

def convert_network_object(obj):
    return convert_hostnet_object(obj, "network")
    
def convert_host_object(obj):
    return convert_hostnet_object(obj, "host")

def parse_network_object(uuid):
    # Host Objects
    r = requests.get("{}/host_objects/{}".format(os.getenv("NMAPI_URI"), uuid))
    if r.status_code == 200:
        host = r.json()
        return "host", host
    
    # Network Objects
    r = requests.get("{}/network_objects/{}".format(os.getenv("NMAPI_URI"), uuid))
    if r.status_code == 200:
        network = r.json()
        return "network", network
    
    # Network Group Objects
    r = requests.get("{}/network_groups/{}".format(os.getenv("NMAPI_URI"), uuid))
    if r.status_code == 200:
        group = r.json()
        return "network_group", group
    
    raise KeyError("Invalid UUID: {}".format(uuid))

def parse_service_object(uuid):
    # Service Objects
    r = requests.get("{}/service_objects/{}".format(os.getenv("NMAPI_URI"), uuid))
    if r.status_code == 200:
        service = r.json()
        return "service_object", service
    
    # Service Group Objects
    r = requests.get("{}/service_groups/{}".format(os.getenv("NMAPI_URI"), uuid))
    if r.status_code == 200:
        group = r.json()
        return "service_group", group
    
    raise KeyError("Invalid UUID: {}".format(uuid))

def recurse_service(group):
    services = []
    for child in group["children"]:
        r = requests.get("{}/service_groups/{}".format(os.getenv("NMAPI_URI"), child))
        if r.status_code == 200:
            services = services + recurse_service(r.json())
        
        r = requests.get("{}/service_objects/{}".format(os.getenv("NMAPI_URI"), child))
        if r.status_code == 200:
            service = r.json()
            services.append(service)
    
    return services

    
def recurse_network(group):
    hostobjects = []
    networkobjects = []
    for child in group["children"]:
        r = requests.get("{}/network_groups/{}".format(os.getenv("NMAPI_URI"), child))
        if r.status_code == 200:
            hosts, nets = recurse_service(r.json())
            hostobjects = hostobjects + hosts
            networkobjects = networkobjects + nets
        
        r = requests.get("{}/network_objects/{}".format(os.getenv("NMAPI_URI"), child))
        if r.status_code == 200:
            service = r.json()
            networkobjects.append(service)
            
        r = requests.get("{}/host_objects/{}".format(os.getenv("NMAPI_URI"), child))
        if r.status_code == 200:
            service = r.json()
            hostobjects.append(service)
    
    return hostobjects, networkobjects

def sign_text(text):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import hashes
    import base64

    with open("{}/management_key.pem".format(os.getenv("CONFIG_DIR")), "r") as fh:
        pem = fh.readlines()
        key = serialization.load_pem_private_key("".join(pem).encode("utf-8"), password=None, backend=default_backend())

    sig = key.sign(data=text.encode("utf-8"), signature_algorithm=ec.ECDSA(hashes.SHA256()))
    return base64.b64encode(sig)