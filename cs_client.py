# OSM cs client

import requests
import json
import decouple as dc
import yaml
import time
# OSM base url


start_time = time.time()

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
# print(cookie)

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Cookie': cookie,
    'Authorization': "Bearer " + session_id
}

# Get NSTs

# Test variable !! TODO: Read this from API
c_nst_id = "slice1_nstd"

url = base_url + "/nst/v1/netslice_templates"

ns_templates = requests.request("GET", url, headers=headers, verify=False)
# print(ns_templates.text)
ns_templates = ns_templates.json()

c_nst = None
# Search nst c_nst
for nst in ns_templates:

    if nst["id"] == c_nst_id:
        c_nst = nst
        break
# print(json.dumps(c_nst, indent=2))

if not c_nst:
    print("This NST does not exist!")

# Get consumer's NST
_id = c_nst["_id"]
headers = {
    'Content-Type': 'application/json',
    'Accept': 'text/plain',
    'Cookie': cookie,
    'Authorization': "Bearer " + session_id
}
url = base_url + '/nst/v1/netslice_templates/' + str(_id) + '/nst'
nst_req = requests.request("GET", url, headers=headers, verify=False)
c_nst = yaml.load(nst_req.text, Loader=yaml.SafeLoader)

c_nst = c_nst["nst"][0]  # NST BODY ONLY !!!!!

# Read provider's CS Descriptor pr_csd TODO: Read this from API

filename = 'provider_slice.json'
with open(filename) as f:
    pr_csd = json.load(f)

# c_nst_subnets = c_nst["netslice-subnet"]
# print(json.dumps(c_nst_subnets, indent=2))


# Add Netslice-Subnet for CSC

c_nst["netslice-subnet"].append(pr_csd["netslice-subnet"])
# print(json.dumps(c_nst["netslice-subnet"], indent=2))


# Add the corresponding Connection Points
mgmt_slice_network = None   # attache mgmt network in vim network mgmt for slicing
data_slice_network = None   # attache data network in vim network data for slicing
mgmt_flag = 0
data_flag = 0
for vld in c_nst["netslice-vld"]:
    # Add mgmt csc interface
    if "mgmt-network" in vld and vld["mgmt-network"]:
        vld["nss-connection-point-ref"].append(pr_csd["mgmt-connector"])
        mgmt_flag = 1
        mgmt_slice_network = vld["name"]

    # Add data csc interface
    if "mgmt-network" not in vld or not vld["mgmt-network"]:
        vld["nss-connection-point-ref"].append(pr_csd["data-connector"])
        data_flag = 1
        data_slice_network = vld["name"]

    if mgmt_flag and data_flag:
        break

# Construct NSTD structure (nst: ...)
temp = [c_nst]
c_nst = temp
c_nst = {"nst": c_nst}

# print(json.dumps(c_nst, indent=2))
yaml_cnst = yaml.dump(c_nst, allow_unicode=True)
# print(yaml_cnst)


# PUT updated Consumer's NST

url = base_url + "/nst/v1/netslice_templates_content/" + str(_id)
headers = {
    'Content-Type': 'application/yaml',
    'Cookie': cookie,
    'Authorization': "Bearer " + session_id
}

payload = yaml_cnst

response = requests.request("PUT", url, headers=headers, data=payload, verify=False)
print(response.text)

print("Instantiating NSI... \n")

# Instantiate Consumer's slice

# Headers - URL
url = base_url + "/nsilcm/v1/netslice_instances_content"
headers["Content-Type"] = "application/json"

# Mandatory Instantiation parameters

''' TODO Read the below variables as input '''
''' 1) nsi_name: user's input
    2) nst_id: it is defined above
    3) vim_account_id: translated from vim_name into id
'''

nsi_name = "test_consumer_slice"    # str()
nst_id = str(_id)
vim_account_id = "6dc88ac7-1790-4fce-9863-0ae307977a66"
nsi_description = "Testing slice"

# add network config
if mgmt_slice_network or data_slice_network:
    vld_config = [
            {
                "name": str(mgmt_slice_network),
                "vim-network-name": "slicing_mgmt"
            },
            {
                "name": str(data_slice_network),
                "vim-network-name": "slicing_consumer_data"
            }
        ]
else:
    vld_config = []

instantiation_data = {
        "nsiName": nsi_name,
        "nstId": nst_id,
        "vimAccountId": vim_account_id,
        "nsiDescription": nsi_description,
        "netslice-vld": vld_config
}

payload = json.dumps(instantiation_data)

instantiation = requests.request("POST", url, headers=headers, data=payload, verify=False)
print(instantiation.text)

print("exec time: ", time.time() - start_time)

