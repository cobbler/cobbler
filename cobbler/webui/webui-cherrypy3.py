#!/usr/bin/env python

from CobblerWeb import CobblerWeb
import cherrypy

cherrypy.tree.mount( CobblerWeb(server="http://localhost:25151", base_url=''), script_name='/', config='webui-cherrypy.cfg' )
cherrypy.server.quickstart()
cherrypy.engine.start()
cherrypy.engine.block()

