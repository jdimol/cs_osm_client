#
from flask import Flask
from flask_restx import Api, fields
import os

# Init app
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

# api
api = Api(app, version='1.0', title="Cross Service Orchestration API")
client_api = api.namespace('client_api',
                           description="Cross Service Orchestration API"
                           )

