# Methods for the API

# Imports
import decouple as dc
import requests
import yaml
import json
# import sys
# import time

# Define Base url
base_url = dc.config("BASE_URL")


# Headers
def make_headers(accept_type):
    #
    accept_object = {
        'json': 'application/json',
        'yaml': 'text/plain'
    }

    headers = {
        'Content-Type': 'application/json',
        'Accept': accept_object[accept_type],
        'Authorization': get_api_key()
    }
    return headers


def get_auth_parameters():
    #
    api_username = dc.config("OSM_USER")
    api_key = dc.config("OSM_PASSWD")
    api_project = dc.config("OSM_PROJECT")
    payload = {"username": api_username,
               "password": api_key,
               "project_id": api_project}

    return payload


# Authentication for NBI of OSM
def get_api_key():
    #
    url = base_url + "/admin/v1/tokens"
    auth_payload = get_auth_parameters()
    auth_payload = json.dumps(auth_payload)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=auth_payload, verify=False)

    response_data = response.json()
    session_id = response_data["id"]
    bearer = "Bearer " + session_id
    return bearer


# Get on-boarded NSTs
def get_nsts():
    #
    url = base_url + "/nst/v1/netslice_templates"
    headers = make_headers('json')
    ns_templates = requests.request("GET", url, headers=headers, verify=False)
    ns_templates = ns_templates.json()

    return ns_templates


# Get NST descriptor in json (Request from OSM)
def get_nst(nst_id):
    #
    nst = None
    nsts = get_nsts()
    for t in nsts:

        if t["id"] == nst_id:
            nst = t
            break
    if not nst:
        print("This NST does not exist!")

    return nst


# Returns the Descriptor of a nst, in JSON format
def get_nst_descriptor(nst_id):
    #
    nst = get_nst(nst_id)

    headers = make_headers('yaml')
    url = base_url + '/nst/v1/netslice_templates/' + str(nst["_id"]) + '/nst'

    nst_req = requests.request("GET", url, headers=headers, verify=False)
    nst_json = yaml.load(nst_req.text, Loader=yaml.SafeLoader)
    nst_descriptor = nst_json["nst"][0]

    return nst_descriptor


# Create objects of netslice-subnets and vld connectors
# for shared services
def extract_shared_services(services, vlds):
    #
    prov_services = []
    for serv in services:

        prov_service = {}

        if serv["is-shared-nss"] == "true":
            mgmt_flag = False
            data_flag = False
            data_connector = None
            mgmt_connector = None

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
            if data_connector and mgmt_connector:

                prov_service = {"netslice-subnet": serv,
                                "data-connector": data_connector,
                                "mgmt-connector": mgmt_connector
                                }
            prov_services.append(prov_service)

    return prov_services


# Create provided service record for data store in JSON format
def create_prov_service_record(p_nst_id, shared_service_id):
    # TODO: Adding multiple services from various providers

    # Get the p_nst descriptor
    p_nstd = get_nst_descriptor(p_nst_id)

    # Define a python dictionary with the provider's nst data
    services = p_nstd["netslice-subnet"]  # List of services

    # Retrieve vlds
    vlds = p_nstd["netslice-vld"]

    prov_services = extract_shared_services(services, vlds)

    # find the demanded service
    p_service = next(filter(lambda service: service["netslice-subnet"]["id"] == shared_service_id, prov_services))

    return p_service


# !------------  testing code  ------------!
#
#


# print(create_prov_service_record('cosmos_slice_nstd', 'tensorflow_big'))
