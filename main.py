"""`main` is the top level module for your Flask application."""

import json
from apiclient import discovery
from apiclient.http import MediaIoBaseUpload
from oauth2client.client import GoogleCredentials
from flask import request, Response, abort, Flask, render_template, url_for, flash, redirect
import cloudstorage as gcs
from filemanager import handler
from flask.ext.login import UserMixin, LoginManager, login_user, logout_user, login_required
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)

app = Flask(__name__)
# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

# Flask's default handling of 
app.url_map.strict_slashes = False

app.secret_key = 'nevergonnaguessit' # Required for session management

FILE_BUCKET = 'zig'
PUBLISH_BUCKET = 'all.spiffthings.com'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

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

#
# User login stuff
#

class User(UserMixin):
    user_database = {
        'darrin': ( 'darrin', 'abcdef', 'Darrin Massena' ),
        'test': ( 'test', 'abcdef', 'Test Account' ),
        'fakeuser': ( 'fakeuser', 'abcdef', 'Fake User' )
    }

    def __init__(self, id, password, fullname=''):
        self.id = id
        self.password = password
        self.fullname = fullname

    def generate_auth_token(self, expiration=600):
        s = Serializer(app.secret_key, expires_in=expiration)
        return s.dumps({ 'id': self.id })

    @classmethod
    def get(cls, id):
        user_record =  cls.user_database.get(id)
        if not user_record:
            return None
        return User(user_record[0], user_record[1], user_record[2])

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(app.secret_key)
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None # valid token, but expired
        except BadSignature:
            return None # invalid token
        user = User.get(data['id'])
        return user

@login_manager.user_loader
def user_loader(user_id):
    return User.get(user_id)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', next=request.args.get('next'))
    elif request.method == 'POST':
        username = request.form['txtUsername']
        password = request.form['txtPassword']

        user = User.get(username)
        if user.password == password:
            login_user(user)
            #g.user = user  # TODO: Needed?
            flash('Welcome back {0}'.format(username)) # TODO: escape or whatever
            try:
                next = request.form['next']
                return redirect(next)
            except:
                return redirect(url_for('index'))
        else:
            flash('Invalid login')
            return redirect(url_for('login'))
    else:
        return abort(405)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    elif request.method == 'POST':
        pass
    else:
        abort(405)

    # TODO: validate these!
    # TODO: be sure they won't cause problems injected into HTML
    username = request.form['txtUsername']
    password = request.form['txtPassword']

    user = User.get(username)
    if user:
        flash('The username {0} is already in use.  Please try a new username.'.format(username)) # TODO: escape or whatever
        return redirect(url_for('register'))
    else:
        # TODO: fullname
        user = User(id=username, password=password)
        # TODO: save it somewhere
        #db.session.add(user)
        #db.session.commit()

        flash('You have registered the username {0}. Please login'.format(username)) # TODO: escape or whatever
        return redirect(url_for('login'))

@app.route('/secret')
@login_required
def secret():
    return render_template('secret.html')

#
# API
#
'''
@app.route('/api/token')
@auth.login_required
def get_auth_token():
    token = g.user.generate_auth_token()
    return jsonify({ 'token': token.decode('ascii') })
'''

# Return a list of the current user's projects.

# TODO: @auth.login_required (w/ api-token)
@app.route('/api/project')
def list_projects():
    # TODO: automated
    auth_token = request.headers['authorization']
    user = User.verify_auth_token(auth_token)
    credentials = GoogleCredentials.get_application_default()
    service = discovery.build('storage', 'v1', credentials=credentials)
    #fields_to_return = 'nextPageToken,items(name,size,contentType,metadata(my-key))'
    req = service.objects().list(bucket=FILE_BUCKET, prefix=user.id + '/', delimiter='/')
    prefixes = []
    while req:
        resp = req.execute()
        # TODO: error handling
        if 'prefixes' in resp:
            prefixes.extend(resp['prefixes'])
        req = service.objects().list_next(req, resp)
        # TODO: error handling

    return json.dumps(prefixes, indent=2)

# HEAD - get project info
# POST - create project (w/ many files as multipart/form-data)
# DELETE - delete project
# ?GET - return entire project zipped
# ?PUT - accept entire project zipped
# 
#@app.route('/api/project/<project_name>')
#def project(project_name):
#    pass

# GET - list all the files in the project
# POST - add multiple files to the proejct (received as multipart/form-data)
# TODO: @auth.login_required (w/ api-token)
@app.route('/api/project/<project_name>/', methods=['GET', 'POST'])
def files(project_name):
    # TODO: automated
    auth_token = request.headers['authorization']
    user = User.verify_auth_token(auth_token)

    if request.method == 'GET':
        credentials = GoogleCredentials.get_application_default()
        service = discovery.build('storage', 'v1', credentials=credentials)
        #fields_to_return = 'nextPageToken,items(name,size,contentType,metadata(my-key))'
        req = service.objects().list(bucket=FILE_BUCKET, prefix=user.id + '/' + project_name + '/')
        files = []
        while req:
            resp = req.execute()
            # TODO: error handling
            if 'items' in resp:
                files.extend(resp['items'])
            req = service.objects().list_next(req, resp)
            # TODO: error handling

        return json.dumps(files, indent=2)
    elif request.method == 'POST':
        print request.files
        fil = request.files['file']
        file_name = user.id + '/' + project_name + '/' + fil.filename
        credentials = GoogleCredentials.get_application_default()
        service = discovery.build('storage', 'v1', credentials=credentials)
        media = MediaIoBaseUpload(fil, fil.content_type)
        insert = service.objects().insert(bucket=FILE_BUCKET, name=file_name, media_body=media)
        insert.execute()

        return json.dumps(request.files['file'].filename)

# PUT - create the file (replace if already exists)
# GET - return the file
# DELETE - delete the file
@app.route('/api/project/<project_name>/<file_path>', methods=['GET', 'POST', 'DELETE'])
def file(project_name, file_path):
    if request.method == 'GET':
        pass
    elif request.method == 'POST':
        print request.files
        pass
    elif request.method == 'DELETE':
        pass

# TODO: @auth.login_required (w/ api-token)
@app.route('/api/template')
def list_templates():
    # TODO: automated
    auth_token = request.headers['authorization']
    user = User.verify_auth_token(auth_token)
    credentials = GoogleCredentials.get_application_default()
    service = discovery.build('storage', 'v1', credentials=credentials)
    #fields_to_return = 'nextPageToken,items(name,size,contentType,metadata(my-key))'
    req = service.objects().list(bucket=FILE_BUCKET, prefix='project-templates/', delimiter='/')
    prefixes = []
    while req:
        resp = req.execute()
        # TODO: error handling
        if 'prefixes' in resp:
            for prefix in resp['prefixes']:
                prefixes.append(prefix[:-1])
        req = service.objects().list_next(req, resp)
        # TODO: error handling

    return json.dumps(prefixes, indent=2)

# TODO: @auth.login_required (w/ api-token)
@app.route('/api/publish/<project_name>')
def publish_project(project_name):
    # TODO: use task queue (and/or have watchAll trigger updates)
    # TODO: clear out deleted files/dirs
    # TODO: no rename: can't do atomic update (e.g. copy to temp, rename current old, rename temp current)
    # TODO: only copy changes

    # TODO: automate token verification
    auth_token = request.headers['authorization']
    user = User.verify_auth_token(auth_token)
    credentials = GoogleCredentials.get_application_default()
    service = discovery.build('storage', 'v1', credentials=credentials)
    req = service.objects().list(bucket=FILE_BUCKET, prefix=user.id + '/' + project_name + '/')
    while req:
        resp = req.execute()
        # TODO: error handling
        json_items = resp['items']
        for item in json_items:
            file_name = item['name']
            print file_name
            req2 = service.objects().copy(
                    sourceBucket=FILE_BUCKET,
                    sourceObject=file_name,
                    destinationBucket=PUBLISH_BUCKET,
                    destinationObject=file_name,
                    body={})
            # TODO: error handling
            resp2 = req2.execute()
            # TODO: error handling

        req = service.objects().list_next(req, resp)
        # TODO: error handling

    return '{}'

#
#
#

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
    user = User.verify_auth_token(user_token)

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
            req2 = service.objects().copy(
                    sourceBucket=FILE_BUCKET,
                    sourceObject=item['name'],
                    destinationBucket=FILE_BUCKET,
                    destinationObject=user.id + '/' + destination + '/' + file_name,
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
