#!/usr/bin/env python

from functools import wraps, update_wrapper
from datetime import timedelta

import re

# Zarafa-specific
import zarafa
from MAPI.Tags import *

# Flask
from flask import Flask, jsonify, request, Response, make_response, current_app


app = Flask(__name__)
# TODO: auth with username/password
server = zarafa.Server()
username = "kiffing"
user = server.user(username)

def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            else:
                h['Access-Control-Allow-Headers'] = 'Authorization, Origin, X-Requested-With, Content-Type, Accept'
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator

def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    global user # TODO: this is ugly
    print "username=" + username
    print "password=" + password
    if password == '':
        try:
            user = server.user(username)
        except zarafa.ZarafaException:
            return False
        return True
    return False

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
#        auth = request.authorization
#        if not auth or not check_auth(auth.username, auth.password):
#            print "here"
#            return authenticate()
        return f(*args, **kwargs)
    return decorated

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def get_adddresslist(address):
    return {'name': address.name, 'email': address.email}

def get_importance(item):
    try:
        prop = item.prop(PR_IMPORTANCE)
    except:
        return 'none'
    val = prop.value
    if val == 0:
      return 'low'
    elif val == 1:
      return 'normal'
    elif val == 2:
        return 'high'
    else:
      return 'unknown (' + str(val) + ')'

def get_flag(item):
    try:
        prop = item.prop(PR_MESSAGE_FLAGS)
    except:
        return 'none'
    val = prop.value
    if val == 0:
      return 'clear'
    elif val == 1:
      return 'purple'
    elif val == 2:
      return 'orange'
    elif val == 3:
      return 'green'
    elif val == 4:
      return 'yellow'
    elif val == 5:
      return 'blue'
    elif val == 6:
      return 'red'
    else:
      return 'unknown (' + str(val) + ')'

@app.route('/folders', methods=['GET', 'OPTIONS'])
@crossdomain(origin='*')
@requires_auth
def folders():
    folderlist = []
    for folder in user.store.folders():
        folderlist.append({
            'id': folder.entryid,
            'name': folder.name,
            'count': folder.count,
            'links': {'items': '/folder/'+folder.entryid+'/items'}
        })
    return jsonify({'folders': folderlist})
    # TODO: hierachy
    # return jsonify({folder.name: folder.entryid for folder in user.store.folders()})

@app.route('/folder/<string:foldername>/items', methods=['GET', 'OPTIONS'])
@crossdomain(origin='*')
@requires_auth
def folder(foldername):
    # TODO: store.entryid()?
    #print foldername
    #folder = user.store.folder(foldername)
    itemlist = []
    try:
        folder = user.store.folder(foldername)
    except zarafa.ZarafaException:
        return jsonify({'error': 'Folder does not exist'})
    x = 0
    for item in folder.items():
        if x == 5:
            break
        itemlist.append({
            'id': item.entryid,
            'name': item.subject,
            'folder': folder.entryid,
            'count': len(item.props()),
#            'subject': item.subject,
#            'received': str(item.received),
            'links': {'keys': '/folder/'+folder.entryid+'/item/'+item.entryid}
        })
        x = x + 1
    return jsonify({'items': itemlist})

@app.route('/folder/<string:folderid>/item/<string:itemid>', methods=['GET', 'OPTIONS'])
@requires_auth
@crossdomain(origin='*')
def item(folderid, itemid):
    try:
        folder = user.store.folder(folderid)
    except zarafa.ZarafaException:
        return jsonify({'error': 'Folder does not exist'})
    try:
        item = folder.item(itemid)
    except:
        return jsonify({'error': 'Item does not exist'})

    #print [hex(prop.proptag), prop.idname or prop.name,  prop.strval().decode('utf-8')]

    proplist = []
    for prop in item.props():
#        name = prop.idname or prop.name
#        value = prop.strval().decode('utf-8')
#        if name and value and re.match('^PR_', name):
        proplist.append({
            'id': prop.proptag,
            'name': prop.idname or prop.name,
            'value': prop.strval().decode('utf-8')
        })
    return jsonify({ 'keys' : proplist })
#        res = prop.__unicode__()
#        match = re.search('Property\(([^,]*), (.*)\)$', res)
#        name = match.group(1)
#        value = match.group(2)
#        match = re.search('u\'(.*)\'$', value)
#        if match:
#            value = match.group(1)
#        proplist.append({
#            'id': prop.proptag,
#            'name': name,
#            'value': value
#        })

#    itemobj = {
#        'id': item.entryid,
#        'subject': item.subject,
#        'received': str(item.received),
#        'sent': item.prop(PR_CLIENT_SUBMIT_TIME).strval(),
#        'size': item.prop(PR_MESSAGE_SIZE).value, # Kb?
#        'importance': get_importance(item),
#        'flags': get_flag(item),
##        'sender': get_adddresslist(item.sender),
##        'recipients': [get_adddresslist(recip) for recip in item.recipients()],
##        'headers': item.headers().items(),
#        'html': item.body.html,
#        'text': item.body.text
#    }
#    return jsonify({ 'item' : itemobj })

if __name__ == '__main__':
    app.run(host='0.0.0.0',threaded=True,debug=False)
