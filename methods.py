# Methods for the API

# Imports
import decouple as dc
import requests
import yaml
import json
import sys
import time


# measure time
start_time = time.time()


# Add Services from Provider's NetSlice Template

# OSM base url

base_url = dc.config("BASE_URL")

# Authentication

url = base_url + "/admin/v1/tokens"

API_USERNAME = dc.config("OSM_USER")
API_KEY = dc.config("OSM_PASSWD")
API_PROJECT = dc.config("OSM_PROJECT")
payload = {"username": API_USERNAME, "password": API_KEY, "project_id": API_PROJECT}

payload = json.dumps(payload)

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload, verify=False)

response_data = response.json()
session_id = response_data["id"]

# Cookie
cookie = 'session_id=' + str(session_id)

# Update headers
headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Cookie': cookie,
    'Authorization': "Bearer " + session_id
}

# Get NSTs

# Test variable !! TODO: Read this from API
c_nst_id = sys.argv[1]

url = base_url + "/nst/v1/netslice_templates"

ns_templates = requests.request("GET", url, headers=headers, verify=False)
# print(ns_templates.text)
ns_templates = ns_templates.json()

c_nst = None
# Search nst c_nst
# In the templates search for the corresponding 'id' (as a string)
for nst in ns_templates:

    if nst["id"] == c_nst_id:
        c_nst = nst
        break
# print(json.dumps(c_nst, indent=2))

if not c_nst:
    print("This NST does not exist!")

# Get NST | Search by _id value
_id = c_nst["_id"]
headers = {
    'Content-Type': 'application/json',
    'Accept': 'text/plain',
    'Cookie': cookie,
    'Authorization': "Bearer " + session_id
}
url = base_url + '/nst/v1/netslice_templates/' + str(_id) + '/nst'
nst_req = requests.request("GET", url, headers=headers, verify=False)
nst = yaml.load(nst_req.text, Loader=yaml.SafeLoader)


# Provider's NST

# Define a python dictionary with the provider's nst data
services = nst["nst"][0]["netslice-subnet"]     # List of services
# print(services)

vlds = nst["nst"][0]["netslice-vld"]

prov_services = []
for serv in services:
    if serv["is-shared-nss"] == "true":
        mgmt_flag = False
        data_flag = False
        for vld in vlds:
            if "mgmt-network" in vld and vld["mgmt-network"] == 'true':
                for cp in vld["nss-connection-point-ref"]:
                    if cp["nss-ref"] == serv["id"]:
                        mgmt_connector = cp
                        mgmt_flag = True

            if "mgmt-network" not in vld or vld["mgmt-network"] == 'false':
                # find a data connector
                for cp in vld["nss-connection-point-ref"]:
                    if cp["nss-ref"] == serv["id"]:
                        data_connector = cp
                        data_flag = True

            if mgmt_flag and data_flag:
                break

        prov_service = {"netslice-subnet": serv, "mgmt-connector": mgmt_connector, "data-connector": data_connector}
        prov_services.append(prov_service)

payload = json.dumps(prov_services, indent=2)
print(payload)

print("exec time: ", time.time() - start_time)
