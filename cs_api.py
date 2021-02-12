#
from flask import Flask, request
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
# allow both GET and POST requests
@app.route('/form-example', methods=['GET', 'POST'])
def form_example():
    # handle the POST request
    if request.method == 'POST':
        nstd = request.form.get('nstd')
        prov_service_id = request.form.get('prov_id')
        return '''
                  <h1>Your nstd that will be used is: {}</h1>
                  <h1>Requested service ID: {}</h1>'''.format(nstd, prov_service_id)

    # otherwise handle the GET request
    return '''
           <form method="POST">
               <div><label>Your NS Template: <input type="text" name="nstd"></label></div>
               <div><label>Requested Service ID: <input type="text" name="prov_id"></label></div>
               <input type="submit" value="Submit">
           </form>'''

if __name__ == '__main__':
    # run app in debug mode on port 5000
    app.run(debug=True, port=5000)

