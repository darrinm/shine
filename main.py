"""`main` is the top level module for your Flask application."""

import json
from apiclient import discovery
from oauth2client.client import GoogleCredentials

# Import the Flask Framework
from flask import Flask
app = Flask(__name__)
# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.


@app.route('/')
def hello():
    """Return a list of the hosted projects."""
    return list_objects('zig')


@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404


@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Sorry, unexpected error: {}'.format(e), 500


def list_objects(bucket):
    # Get the application default credentials. When running locally, these are
    # available after running `gcloud init`. When running on compute
    # engine, these are available from the environment.
    credentials = GoogleCredentials.get_application_default()

    # Construct the service object for interacting with the Cloud Storage API -
    # the 'storage' service, at version 'v1'.
    # You can browse other available api services and versions here:
    #     https://developers.google.com/api-client-library/python/apis/
    service = discovery.build('storage', 'v1', credentials=credentials)

    # Make a request to buckets.get to retrieve a list of objects in the
    # specified bucket.
    req = service.buckets().get(bucket=bucket)
    resp = req.execute()
    #list_string = json.dumps(resp, indent=2)

    # Create a request to objects.list to retrieve a list of objects.
    fields_to_return = \
        'nextPageToken,items(name,size,contentType,metadata(my-key))'
    req = service.objects().list(bucket=bucket, fields=fields_to_return)

    # If you have too many items to list in one request, list_next() will
    # automatically handle paging with the pageToken.
    list_string = ''
    while req:
        resp = req.execute()
        #list_string = list_string + json
        json_items = resp['items']
        for item in json_items:
            if item['name'].endswith('/index.html'):
                list_string = (list_string + '<a href="https://storage.googleapis.com/zig/' + 
                        item['name'] + '">' + item['name'][:-11] + 
                        '</a> <a href="http://threejs.org/editor#app=https://storage.googleapis.com/zig/' + 
                        item['name'][:-11] + '/app.json">(edit)</a><p>\n')
        #list_string = list_string + json.dumps(resp, indent=2)
        req = service.objects().list_next(req, resp)

    return list_string
