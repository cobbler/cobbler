from mod_python import apache

import xmlrpclib, time, simplejson, string

my_uri = "http://127.0.0.1/cobbler_api"
remote = None
token = None
username = None

def authenhandler(req):
    global remote
    global token
    global username

    password = req.get_basic_auth_pw()
    username = req.user     
    try:
        remote = xmlrpclib.Server(my_uri, allow_none=True)
        token = remote.login(username, password)
        remote.update(token)
        return apache.OK
    except:
        return apache.HTTP_UNAUTHORIZED

