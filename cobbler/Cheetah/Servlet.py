#!/usr/bin/env python
# $Id: Servlet.py,v 1.40 2006/02/04 23:06:15 tavis_rudd Exp $
"""Provides an abstract Servlet baseclass for Cheetah's Template class

Meta-Data
================================================================================
Author: Tavis Rudd <tavis@damnsimple.com>
License: This software is released for unlimited distribution under the
         terms of the MIT license.  See the LICENSE file.
Version: $Revision: 1.40 $
Start Date: 2001/10/03
Last Revision Date: $Date: 2006/02/04 23:06:15 $
""" 
__author__ = "Tavis Rudd <tavis@damnsimple.com>"
__revision__ = "$Revision: 1.40 $"[11:-2]

import sys
import os.path

isWebwareInstalled = False
try:
    if 'ds.appserver' in sys.modules.keys():
        from ds.appserver.Servlet import Servlet as BaseServlet
    else:
        from WebKit.Servlet import Servlet as BaseServlet
    isWebwareInstalled = True

    if not issubclass(BaseServlet, object):
        class NewStyleBaseServlet(BaseServlet, object): pass
        BaseServlet = NewStyleBaseServlet
except:
    class BaseServlet(object): 
        _reusable = 1
        _threadSafe = 0
    
        def __init__(self):
            pass
            
        def awake(self, transaction):
            pass
            
        def sleep(self, transaction):
            pass

        def shutdown(self):
            pass

##################################################
## CLASSES

class Servlet(BaseServlet):
    
    """This class is an abstract baseclass for Cheetah.Template.Template.

    It wraps WebKit.Servlet and provides a few extra convenience methods that
    are also found in WebKit.Page.  It doesn't do any of the HTTP method
    resolution that is done in WebKit.HTTPServlet
    """
    
    transaction = None
    application = None
    request = None
    session = None
    
    def __init__(self):
        BaseServlet.__init__(self)
       
        # this default will be changed by the .awake() method
        self._CHEETAH__isControlledByWebKit = False 
        
    ## methods called by Webware during the request-response
        
    def awake(self, transaction):
        BaseServlet.awake(self, transaction)
        
        # a hack to signify that the servlet is being run directly from WebKit
        self._CHEETAH__isControlledByWebKit = True
        
        self.transaction = transaction        
        #self.application = transaction.application
        self.response = response = transaction.response
        self.request = transaction.request

        # Temporary hack to accomodate bug in
        # WebKit.Servlet.Servlet.serverSidePath: it uses 
        # self._request even though this attribute does not exist.
        # This attribute WILL disappear in the future.
        self._request = transaction.request()

        
        self.session = transaction.session
        self.write = response().write
        #self.writeln = response.writeln
        
    def respond(self, trans=None):
        raise NotImplementedError("""\
couldn't find the template's main method.  If you are using #extends
without #implements, try adding '#implements respond' to your template
definition.""")

    def sleep(self, transaction):
        BaseServlet.sleep(self, transaction)
        self.session = None
        self.request  = None
        self._request  = None        
        self.response = None
        self.transaction = None

    def shutdown(self):
        pass

    def serverSidePath(self, path=None,
                       normpath=os.path.normpath,
                       abspath=os.path.abspath
                       ):
        
        if self._CHEETAH__isControlledByWebKit:
            return BaseServlet.serverSidePath(self, path)
        elif path:
            return normpath(abspath(path.replace("\\",'/')))
        elif hasattr(self, '_filePath') and self._filePath:
            return normpath(abspath(self._filePath))
        else:
            return None

# vim: shiftwidth=4 tabstop=4 expandtab
