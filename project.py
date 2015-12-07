from flask import Flask, render_template, request, redirect, jsonify
from flask import make_response, send_from_directory, url_for, flash
from flask import session as login_session
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Artist, Painting, User, Comments
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from werkzeug import secure_filename
import random
import string
import os
import json
import httplib2
import requests

#Configuration for Flask server
app = Flask(__name__)

#Setup for upload directory for painting images
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/images')

ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg', 'gif'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Artist Community"

# Dictionary to control which menuitem is visible in the banner
showMenu = {'showArtist': False, 'showAddArtist': False,
            'editDeleteArtist': False, 'showAddPainting': False}

# Check to see if filename is a file with an allowed extension and if of
# the image type


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/<path:filename>')
def send_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# Connect to Database and create database session
engine = create_engine('sqlite:///artists.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = ("https://graph.facebook.com/oauth/access_token?grant_type="
           "fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_"
           "token=%s" % (app_id, app_secret, access_token))
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]

    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly
    # logout, let's strip out the information before the equals sign in our
    # token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = ("https://graph.facebook.com/v2.4/me/picture?%s&"
           "redirect=0&height=200&width=200" % token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;'
    output += 'border-radius: 150px;-webkit-border-radius: '
    output += '150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (
        facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user '
                                            'is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;'
    output += 'border-radius: 150px;-webkit-border-radius: 150px;'
    output += '-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Artist Information
@app.route('/artist/<int:artist_id>/painting/JSON')
def artistPaintingJSON(artist_id):
    artist = session.query(Artist).filter_by(id=artist_id).one()
    items = session.query(Painting).filter_by(
        artist_id=artist_id).all()
    return jsonify(Paintings=[i.serialize for i in items])


@app.route('/artist/<int:artist_id>/painting/<int:painting_id>/JSON')
def paintingJSON(artist_id, painting_id):
    painting = session.query(Painting).filter_by(id=painting_id).one()
    return jsonify(Painting=painting.serialize)


@app.route('/artist/JSON')
def artistsJSON():
    artists = session.query(Artist).all()
    return jsonify(artists=[r.serialize for r in artists])


# Show all Artists
@app.route('/')
@app.route('/artist/')
def showArtists():

    showMenu['showArtist'] = True
    showMenu['showAddArtist'] = False
    showMenu['editDeleteArtist'] = False
    showMenu['showAddPainting'] = False

    artists = session.query(Artist).order_by(asc(Artist.name))
    latestPaintings = session.query(Painting).order_by(Painting.id.asc())
    if 'username' in login_session:
        showMenu['showAddArtist'] = True
    return render_template('publicartists.html', artists=artists,
                           paintings=latestPaintings, showMenu=showMenu)


# Create a new artist
@app.route('/artist/new/', methods=['GET', 'POST'])
def newArtist():

    showMenu['showArtist'] = True
    showMenu['showAddArtist'] = False
    showMenu['editDeleteArtist'] = False
    showMenu['showAddPainting'] = False

    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newArtist = Artist(name=request.form['name'],
                           description=request.form['description'],
                           user_id=login_session['user_id'])
        session.add(newArtist)

        flash('New Artist %s Successfully Created' % newArtist.name)
        session.commit()
        showMenu['showArtist'] = False
        showMenu['showAddArtist'] = True
        return redirect(url_for('showArtists', showMenu=showMenu))
    else:
        return render_template('newArtist.html', showMenu=showMenu)


# Edit a artist
@app.route('/restaurant/<int:artist_id>/edit/', methods=['GET', 'POST'])
def editArtist(artist_id):

    showMenu['showArtist'] = True
    showMenu['showAddArtist'] = False
    showMenu['editDeleteArtist'] = False
    showMenu['showAddPainting'] = False

    editedArtist = session.query(
        Artist).filter_by(id=artist_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if editedArtist.user_id != login_session['user_id']:
        return ("<script>function myFunction() {alert('You are not "
                "authorized to edit this artist. Please create your own artist"
                " in order to edit.');}</script><body onload='myFunction()''>")
    if request.method == 'POST':
        if request.form['name']:
            editedArtist.name = request.form['name']
        if request.form['description']:
            editedArtist.decription = request.form['description']
        session.add(editedArtist)
        session.commit()
        flash('Artist Successfully Edited %s' % editedArtist.name)
        showMenu['showAddArtist'] = True
        showMenu['showArtist'] = False
        return redirect(url_for('showArtists', showMenu=showMenu))
    else:
        return render_template('editArtist.html',
                               artist=editedArtist, showMenu=showMenu)


# Delete a artist
@app.route('/artist/<int:artist_id>/delete/', methods=['GET', 'POST'])
def deleteArtist(artist_id):

    showMenu['showArtist'] = True
    showMenu['showAddArtist'] = False
    showMenu['editDeleteArtist'] = False
    showMenu['showAddPainting'] = False

    artistToDelete = session.query(
        Artist).filter_by(id=artist_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if artistToDelete.user_id != login_session['user_id']:
        return ("<script>function myFunction() {alert('You are not "
                "authorized to delete this artist. Please create your "
                "own artist in order to delete.');}</script>"
                "<body onload='myFunction()''>")
    if request.method == 'POST':
        session.delete(artistToDelete)
        flash('%s Successfully Deleted' % artistToDelete.name)
        session.commit()
        showMenu['showArtist'] = False
        showMenu['showAddArtist'] = True
        return redirect(url_for('showArtists',
                        artist_id=artist_id,
                        showMenu=showMenu))
    else:
        return render_template('deleteArtist.html',
                               artist=artistToDelete,
                               showMenu=showMenu)

# Show a painting


@app.route('/artist/<int:artist_id>/')
@app.route('/artist/<int:artist_id>/painting/')
def showPainting(artist_id):

    showMenu['showArtist'] = True
    showMenu['showAddArtist'] = False
    showMenu['editDeleteArtist'] = False
    showMenu['showAddPainting'] = False

    artist = session.query(Artist).filter_by(id=artist_id).one()
    creator = getUserInfo(artist.user_id)
    items = session.query(Painting).filter_by(
        artist_id=artist_id).all()
    if ('username' not in login_session or
            creator.id != login_session['user_id']):
        return render_template('publicpainting.html',
                               items=items, artist=artist,
                               creator=creator, showMenu=showMenu)
    else:
        showMenu['showAddArtist'] = True
        showMenu['showAddPainting'] = True
        showMenu['editDeleteArtist'] = True
        return render_template('painting.html', items=items,
                               artist=artist, creator=creator,
                               showMenu=showMenu)


# Create a new painting
@app.route('/artist/<int:artist_id>/painting/new/', methods=['GET', 'POST'])
def newPainting(artist_id):

    showMenu['showArtist'] = True
    showMenu['showAddArtist'] = False
    showMenu['editDeleteArtist'] = False
    showMenu['showAddPainting'] = False

    if 'username' not in login_session:
        return redirect('/login')
    artist = session.query(Artist).filter_by(id=artist_id).one()
    if login_session['user_id'] != artist.user_id:
        return ("<script>function myFunction() {alert('You are not"
                " authorized to add paintings to this artist. Please "
                "create your own artist in order to add paintings.');}"
                "</script><body onload='myFunction()''>")
    if request.method == 'POST':

        file = request.files['filename']
        if file and allowed_file(file.filename):
            imagefilename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], imagefilename))
            flash("Painting Image file Successfully Uploaded.")
            newItem = Painting(name=request.form['name'],
                               description=request.form['description'],
                               price=request.form['price'],
                               category=request.form['category'],
                               filename=imagefilename,
                               artist_id=artist_id, user_id=artist.user_id)
        else:
            newItem = Painting(name=request.form['name'],
                               description=request.form['description'],
                               price=request.form['price'],
                               category=request.form['category'],
                               filename='placeholder.png',
                               artist_id=artist_id, user_id=artist.user_id)

        session.add(newItem)
        session.commit()
        flash('New Painting %s Item Successfully Created' % (newItem.name))
        showMenu['editDeleteArtist'] = True
        showMenu['showAddPainting'] = True
        return redirect(url_for('showPainting',
                                artist_id=artist_id,
                                showMenu=showMenu))
    else:
        return render_template('newpainting.html',
                               artist_id=artist_id,
                               showMenu=showMenu)

# Edit a painting


@app.route('/artist/<int:artist_id>/menu/<int:painting_id>/edit',
           methods=['GET', 'POST'])
def editPainting(artist_id, painting_id):

    showMenu['showArtist'] = True
    showMenu['showAddArtist'] = False
    showMenu['editDeleteArtist'] = False
    showMenu['showAddPainting'] = False

    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(Painting).filter_by(id=painting_id).one()
    artist = session.query(Artist).filter_by(id=artist_id).one()
    if login_session['user_id'] != artist.user_id:
        return ("<script>function myFunction() {alert('You are not "
                "authorized to edit paintings of this artist. Please "
                "create your own artist in order to edit paintings.');}"
                "</script><body onload='myFunction()''>")
    if request.method == 'POST':
        file = request.files['filename']
        if file and allowed_file(file.filename):
            imagefilename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], imagefilename))
            flash("Painting Image file Successfully Uploaded.")
            editedItem.filename = imagefilename

        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['category']:
            editedItem.category = request.form['category']
        session.add(editedItem)
        session.commit()
        flash('Painting Successfully Edited')
        showMenu['editDeleteArtist'] = True
        showMenu['showAddPainting'] = True
        return redirect(url_for('showPainting',
                        artist_id=artist_id,
                        showMenu=showMenu))
    else:
        return render_template('editpainting.html', artist_id=artist_id,
                               painting_id=painting_id, item=editedItem,
                               showMenu=showMenu)


# Delete a painting
@app.route('/artist/<int:artist_id>/painting/<int:painting_id>/delete',
           methods=['GET', 'POST'])
def deletePainting(artist_id, painting_id):

    showMenu['showArtist'] = True
    showMenu['showAddArtist'] = False
    showMenu['editDeleteArtist'] = False
    showMenu['showAddPainting'] = False

    if 'username' not in login_session:
        return redirect('/login')
    artist = session.query(Artist).filter_by(id=artist_id).one()
    itemToDelete = session.query(Painting).filter_by(id=painting_id).one()
    if login_session['user_id'] != artist.user_id:
        return ("<script>function myFunction() {alert('You are not "
                "authorized to delete paintings of this artist. Please "
                "create your own artist in order to delete items.');}"
                "</script><body onload='myFunction()''>")
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Painting Successfully Deleted')
        showMenu['editDeleteArtist'] = True
        showMenu['showAddPainting'] = True
        return redirect(url_for('showPainting', artist_id=artist_id,
                                showMenu=showMenu))
    else:
        return render_template('deletepainting.html',
                               item=itemToDelete, showMenu=showMenu)

# Add a Comment


@app.route('/artist/<int:artist_id>/menu/<int:painting_id>/newcomment',
           methods=['GET', 'POST'])
def newComment(artist_id, painting_id):

    showMenu['showArtist'] = True
    showMenu['showAddArtist'] = False
    showMenu['editDeleteArtist'] = False
    showMenu['showAddPainting'] = False
    if 'username' not in login_session:
        return redirect('/login')
    painting = session.query(Painting).filter_by(id=painting_id).one()
    artist = session.query(Artist).filter_by(id=artist_id).one()
    creator = login_session['username']
    comments = session.query(Comments).filter_by(
        painting_id=painting_id).order_by(desc(Comments.time))

    if request.method == 'POST':
        newComment = Comments(content=request.form['content'],
                              painting_id=painting.id, creator=creator)
        session.add(newComment)
        flash('New Comment Successfully Added.')
        session.commit()
        comments = session.query(Comments).filter_by(
            painting_id=painting_id).order_by(desc(Comments.time))

    return render_template('newComment.html', artist_id=artist_id,
                           painting=painting, comments=comments,
                           showMenu=showMenu)


# Delete a Comment
@app.route(('/artist/<int:artist_id>/painting/<int:painting_id>/deleteComment/'
            '<int:comment_id>'), methods=['GET', 'POST'])
def deleteComment(artist_id, painting_id, comment_id):

    showMenu['showArtist'] = True
    showMenu['showAddArtist'] = False
    showMenu['editDeleteArtist'] = False
    showMenu['showAddPainting'] = False

    if 'username' not in login_session:
        return redirect('/login')
    artist = session.query(Artist).filter_by(id=artist_id).one()
    painting = session.query(Painting).filter_by(id=painting_id).one()
    comments = session.query(Comments).filter_by(
        painting_id=painting_id).order_by(desc(Comments.time))

    itemToDelete = session.query(Comments).filter_by(id=comment_id).one()

    if login_session['user_id'] != artist.user_id:
        return ("<script>function myFunction() {alert('You are not "
                "authorized to delete comments on this painting.');}"
                "</script><body onload='myFunction()''>")
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Comment Successfully Deleted')
        return redirect(url_for('newComment', artist_id=artist_id,
                        painting_id=painting_id, showMenu=showMenu))
    else:
        return render_template('deletecomment.html', item=itemToDelete,
                               showMenu=showMenu)


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    showMenu['showArtist'] = True
    showMenu['showAddArtist'] = False
    showMenu['editDeleteArtist'] = False
    showMenu['showAddPainting'] = False

    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['credentials']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showArtists', showMenu=showMenu))
    else:
        flash("You were not logged in")
        return redirect(url_for('showArtists', showMenu=showMenu))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
