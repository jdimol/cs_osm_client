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


#
def get_auth_parameters():
    #
    api_username = dc.config("OSM_USER")
    api_key = dc.config("OSM_PASSWD")
    api_project = dc.config("OSM_PROJECT")
    payload = {"username": api_username,
               "password": api_key,
               "project_id": api_project}

    return payload


#
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
    response = requests.request(
        "POST",
        url, headers=headers,
        data=auth_payload,
        verify=False
    )

    response_data = response.json()
    session_id = response_data["id"]
    bearer = "Bearer " + session_id
    return bearer


#
# Headers
def make_headers(accept_type, token):
    #
    accept_object = {
        'json': 'application/json',
        'yaml': 'text/plain'
    }

    headers = {
        'Content-Type': 'application/json',
        'Accept': accept_object[accept_type],
        'Authorization': token
    }
    return headers


#
# Get on-boarded NSTs
def get_nsts(token):
    #

    url = base_url + "/nst/v1/netslice_templates"
    headers = make_headers('json', token)
    ns_templates = requests.request(
        "GET", url,
        headers=headers,
        verify=False
    )
    ns_templates = ns_templates.json()

    return ns_templates


#
# Get NST descriptor in json (Request from OSM)
def get_nst(nst_id, token):
    #
    nst = None
    nsts = get_nsts(token)
    for t in nsts:

        if t["id"] == nst_id:
            nst = t
            break
    if not nst:
        print("This NST does not exist!")

    return nst


#
# Returns the Descriptor of a nst, in JSON format
def get_nst_descriptor(nst_id, token):
    #
    nst = get_nst(nst_id, token)

    # Define headers
    headers = make_headers('yaml', token)
    _id = nst["_id"]
    url = base_url + "/nst/v1/netslice_templates/" + str(_id) + "/nst"

    # Create the request
    nst_req = requests.request(
        "GET",
        url,
        headers=headers,
        verify=False
    )
    nst_json = yaml.load(nst_req.text, Loader=yaml.SafeLoader)

    # Parse descriptor info in a dictionary
    nst_descriptor = nst_json["nst"][0]

    return nst_descriptor, _id


#
# Create provided service record for data store in JSON format
def create_prov_service_record(p_nst_id, shared_service_id, token):
    # TODO: Adding multiple services from various providers

    # Get the p_nst descriptor
    p_nstd, p_id = get_nst_descriptor(p_nst_id, token)

    # Define a python dictionary with the provider's nst data
    services = p_nstd["netslice-subnet"]  # List of services

    # Retrieve vlds
    vlds = p_nstd["netslice-vld"]

    prov_services = extract_shared_services(services, vlds)

    # find the demanded service
    p_service = list(filter(
        lambda service:
        service["netslice-subnet"]["id"] == shared_service_id,
        prov_services
        )
    )

    return p_service[0]


#
# Convert nst descriptor for instantiation
# Convert nst in YAML format as a list
def nst_yaml(c_nst):
    # Return a consumer slice in YAML format

    # Construct nst descriptor structure (nst: ...)
    temp = [c_nst]
    c_nst = temp
    c_nst = {"nst": c_nst}

    # convert into YAML
    yaml_cnst = yaml.dump(c_nst, allow_unicode=True)

    return yaml_cnst


"""
TODO: Create instantiation parameters object for consumer slice
      Based on instantiation parameters of provider's slice
      1) vim-network-name for mgmt and data network
      2) network connectivity establishment for slice-vlds
         using vim-networks configuration.
      3) Access for consumer in specific VNFs 
"""


# # Define Instantiation Parameters
# def instantiation_config():
#     #
#     inst_parameters = {}
#
#     return inst_parameters


#
# Update nst descriptor with a shared service
# Define Management and Data network for configuration
def add_shared_service(p_service, c_nst_id, token):
    # TODO: Adding multiple services from various providers

    # Get consumer's nst descriptor
    c_nst, _id = get_nst_descriptor(c_nst_id, token)

    # Adding a netslice subnet into the descriptor
    c_nst["netslice-subnet"].append(p_service["netslice-subnet"])

    # Add the corresponding Connection Points
    """ 
        -----------------------------------------------------
        Mgmt and data slice networks definition is optional.
        It depends on the VIM configuration for Network Slicing
        Comment the  corresponding lines to disable specific 
        network attachments with vim-networks.
        
        1) mgmt_slice_network = None  
        2) data_slice_network = None  
        3) vld_config 
        -----------------------------------------------------
    """
    mgmt_slice_network = None  # attache mgmt network in vim network
    data_slice_network = None  # attache data network in vim network

    mgmt_flag = 0
    data_flag = 0

    vld_config = []

    # Configure connection points for each vld
    for vld in c_nst["netslice-vld"]:
        # Add mgmt csc interface
        if "mgmt-network" in vld and vld["mgmt-network"] == 'true':
            vld["nss-connection-point-ref"].append(p_service["mgmt-connector"])
            mgmt_flag = 1
            mgmt_slice_network = vld["name"]

        # Add data csc interface
        if "mgmt-network" not in vld or vld["mgmt-network"] == 'false':
            vld["nss-connection-point-ref"].append(p_service["data-connector"])
            data_flag = 1
            data_slice_network = vld["name"]

        if mgmt_flag and data_flag:
            break

    # VLDs configuration object
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

    return c_nst, vld_config, _id


#
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


# /------------------------ / testing code /------------------------ /
#
#
# # basic input
# consumer_nst_id = 'slice1_nstd'
# pr_nst_id = 'cosmos_slice_nstd'
# provided_service = 'tensorflow_big'
#
# key = get_api_key()
#
# # retrieve data
# pr_service = create_prov_service_record(pr_nst_id, provided_service, key)
#
#
# # update c_nstd for shared slice
# c2_nst, vld_conf, _id = add_shared_service(pr_service, consumer_nst_id, key)
#
# c_nst_to_yaml = nst_yaml(c2_nst)
# print(c_nst_to_yaml)
#
# # /------------------------ / testing code /------------------------ /
