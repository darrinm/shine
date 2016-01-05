"""`main` is the top level module for your Flask application."""

import json
from apiclient import discovery
from oauth2client.client import GoogleCredentials
from flask import request, Response
import cloudstorage as gcs
from filemanager import handler

# Import the Flask Framework
from flask import Flask, render_template
app = Flask(__name__)
# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.


FILE_BUCKET = 'zig'
PUBLISHED_BUCKET = 'all.spiffthings.com'

@app.route('/')
def index():
    """Return the home page."""
    return render_template('index.html')

@app.route('/<user_name>')
def person(user_name):
    """Return the person page for the specified user."""
    return render_template('person.html', user_name=user_name)

@app.route('/<user_name>/<project_name>')
def project(user_name, project_name):
    """Return the project page for the specified user's specified project."""
    return render_template('project.html', user_name=user_name, project_name=project_name)

@app.route('/fm/connectors/py/filemanager.py')
def filemanager():
    content, whatever, content_type = handler(request)
    return Response(content, mimetype=content_type)

# copy?src=templates/project&dst=project&user-token=token
@app.route('/copy')
def copy():
    source = request.args.get('src', '')
    destination = request.args.get('dst', '')
    user_token = request.args.get('user-token', '')
    print 'source: %s, destination: %s, user_token: %s' % (source, destination, user_token)

    # Get the application default credentials. When running locally, these are
    # available after running `gcloud init`. When running on compute
    # engine, these are available from the environment.
    credentials = GoogleCredentials.get_application_default()
    # TODO: error handling

    # Construct the service object for interacting with the Cloud Storage API -
    # the 'storage' service, at version 'v1'.
    # You can browse other available api services and versions here:
    #     https://developers.google.com/api-client-library/python/apis/
    service = discovery.build('storage', 'v1', credentials=credentials)
    # TODO: error handling

    fields_to_return = \
            'nextPageToken,items(name,size,contentType,metadata(my-key))'
    req = service.objects().list(bucket=FILE_BUCKET, fields=fields_to_return, prefix=source + '/')
    # TODO: error handling

    while req:
        resp = req.execute()
        # TODO: error handling
        json_items = resp['items']
        for item in json_items:
            print item['name']
            file_name = item['name'][len(source) + 1:]
            print file_name
            # TODO: use authenticated username
            req2 = service.objects().copy(
                    sourceBucket=FILE_BUCKET,
                    sourceObject=item['name'],
                    destinationBucket=FILE_BUCKET,
                    destinationObject='fakeuser/' + destination + '/' + file_name,
                    body={})
            # TODO: error handling
            resp2 = req2.execute()
            # TODO: error handling

        req = service.objects().list_next(req, resp)
        # TODO: error handling

    return ""

#@app.route('/<user_name>/<project_name>/play')
#def play(user_name, project_name):
#    # 307 = Temporary Redirect (keep requesting from original URI)
#    return redirect('https://storage.cloud.google.com/zig/%s/%s/index.html' % (user_name, project_name), code=307)\

@app.route('/<user_name>/<project_name>/play/<path:file_path>')
def play(user_name, project_name, file_path):
    # 307 = Temporary Redirect (keep requesting from original URI)
    # TODO: GoogleCredentials.get_access_token
    gcs.common.set_access_token('ya29.WAI_M3etQTXEBtUUKdpnoZPJhFzBHZ2LoAaJ9hMdDQmDf1LoKVlViwZurHv4E2NthlY4dQ')
    gcs_file = gcs.open('/%s/%s/%s/%s' % (FILE_BUCKET, user_name, project_name, file_path))
    data = gcs_file.read()
    gcs_file.close()
    return data


@app.route('/projects')
def projects():
    """Return a list of the hosted projects."""
    return list_objects(FILE_BUCKET)


@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Nothing at this URL.', 404


@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Unexpected error: {}'.format(e), 500


def list_objects(bucket):
    # Get the application default credentials. When running locally, these are
    # available after running `gcloud init`. When running on compute
    # engine, these are available from the environment.
    credentials = GoogleCredentials.get_application_default()
    # TODO: error handling

    # Construct the service object for interacting with the Cloud Storage API -
    # the 'storage' service, at version 'v1'.
    # You can browse other available api services and versions here:
    #     https://developers.google.com/api-client-library/python/apis/
    service = discovery.build('storage', 'v1', credentials=credentials)
    # TODO: error handling

    # Create a request to objects.list to retrieve a list of objects.
    fields_to_return = \
            'nextPageToken,items(name,size,contentType,metadata(my-key))'
    req = service.objects().list(bucket=bucket, fields=fields_to_return)
    # TODO: error handling

    # If you have too many items to list in one request, list_next() will
    # automatically handle paging with the pageToken.
    list_string = ''
    while req:
        resp = req.execute()
        # TODO: error handling
        #list_string = list_string + json
        json_items = resp['items']
        for item in json_items:
            if item['name'].endswith('/index.html'):
                list_string = (list_string + '<a href="https://storage.googleapis.com/zig/' + 
                        item['name'] + '">' + item['name'][:-11] + 
                        '</a> <a href="three.js/editor/index.html#app=https://storage.googleapis.com/zig/' + 
                        item['name'][:-11] + '/app.json">(edit)</a><p>\n')
        #list_string = list_string + json.dumps(resp, indent=2)
        req = service.objects().list_next(req, resp)
        # TODO: error handling

    return list_string
