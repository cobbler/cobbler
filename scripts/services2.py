import yaml

from cobbler.services import CobblerSvc

def application(environ, start_response):
    print environ

    my_uri = environ['REQUEST_URI']
    print("Checkout my URI: %s" % my_uri)
    
 #   req.add_common_vars()

 #   # process form and qs data, if any
 #   fs = util.FieldStorage(req)
    form = {}
 #   for x in fs.keys():
 #       form[x] = str(fs.get(x,'default'))
 #   
    if my_uri.find("?") == -1:
       # support fake query strings
       # something log /cobbler/web/op/ks/server/foo
       # which is needed because of xend parser errors
       # not tolerating ";" and also libvirt on 5.1 not
       # tolerating "&amp;" (nor "&").

       tokens = my_uri.split("/")
       tokens = tokens[3:]
       label = True
       field = ""
       for t in tokens:
          if label:
             field = t
          else:
             form[field] = t
          label = not label

    print(form)

 #   # TESTING..
 #   form.update(req.subprocess_env)

    # This MAC header is set by anaconda during a kickstart booted with the 
    # kssendmac kernel option. The field will appear here as something 
    # like: eth0 XX:XX:XX:XX:XX:XX
    form["REMOTE_MAC"]  = form.get("HTTP_X_RHN_PROVISIONING_MAC_0", None)
    print("REMOTE_MAC = %s" % form["REMOTE_MAC"])

    # Read config for the XMLRPC port to connect to:
    fd = open("/etc/cobbler/settings")
    data = fd.read()
    fd.close()
    ydata = yaml.load(data)
    remote_port = ydata.get("xmlrpc_port",25151)

    # instantiate a CobblerWeb object
    cw = CobblerSvc(server = "http://127.0.0.1:%s" % remote_port)

    # check for a valid path/mode
    # handle invalid paths gracefully
    mode = form.get('op','index')

    # Execute corresponding operation on the CobblerSvc object:
    func = getattr( cw, mode )
    content = func( **form )
    print("content = %s" % content)

    content = unicode(content).encode('utf-8')
 #   
 #   if content.find("# *** ERROR ***") != -1:
 #       req.write(content)
 #       apache.log_error("possible cheetah template error")
 #       return apache.HTTP_INTERNAL_SERVER_ERROR
 #   elif content.find("# profile not found") != -1 or content.find("# system not found") != -1 or content.find("# object not found") != -1:
 #       req.content_type = "text/html;charset=utf-8"
 #       req.write(" ")
 #       apache.log_error("content not found")
 #       return apache.HTTP_NOT_FOUND
 #   else:
 #       req.write(content)
 #       return apache.OK

 #   req.content_type = "text/plain;charset=utf-8"
    status = '200 OK'
    response_headers = [('Content-type', 'text/plain;charset=utf-8'),
                        ('Content-Length', str(len(content)))]
    start_response(status, response_headers)

    return [content]
