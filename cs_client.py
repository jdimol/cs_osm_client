# OSM cs client

import requests
import json
import decouple as dc
import time
import methods as csm


start_time = time.time()

# Define Base url
base_url = dc.config("BASE_URL")

# Test basic input
consumer_nst_id = 'slice1_nstd'
pr_nst_id = 'cosmos_slice_nstd'
provided_service = 'tensorflow_big'


# Authentication
token = csm.get_api_key()

# Retrieve provider's service config
pr_service = csm.create_prov_service_record(pr_nst_id, provided_service, token)

# Update consumer's descriptor
c_nst, vld_config, _id = csm.add_shared_service(pr_service, consumer_nst_id, token)

# Descriptor to YAML format
c_nst = csm.nst_yaml(c_nst)
print(c_nst)

print("Instantiating NSI... \n")

# Instantiate Consumer's slice

# Headers - URL
url = base_url + "/nsilcm/v1/netslice_instances_content"
headers = csm.make_headers('json', token)


# Mandatory Instantiation parameters
#  TODO Read the below variables as input
#     1) nsi_name: user's input
#     2) nst_id: it is defined above
#     3) vim_account_id: translated from vim_name into id

nsi_name = "test_consumer_slice"    # str()
nst_id = str(_id)
vim_account_id = "6dc88ac7-1790-4fce-9863-0ae307977a66"
nsi_description = "Testing slice"


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

