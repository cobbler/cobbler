"""
Cobbler uses Cheetah templates for lots of stuff, but there's
some additional magic around that to deal with snippets/etc.
(And it's not spelled wrong!)

Copyright 2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

import os
import os.path
import glob
from cexceptions import *
from template_api import Template
from utils import *
import utils

class Templar:

    def __init__(self,config):
        """
        Constructor
        """
        self.config      = config
        self.api         = config.api
        self.settings    = config.settings()

    def check_for_invalid_imports(self,data):
        """
        Ensure that Cheetah code is not importing Python modules
        that may allow for advanced priveledges by ensuring we whitelist
        the imports that we allow
        """
        lines = data.split("\n")
        for line in lines:
            if line.find("#import") != -1:
               rest=line.replace("#import","").replace(" ","").strip()
               if rest not in self.settings.cheetah_import_whitelist:
                   print "warning"
                   raise CX("potentially insecure import in template: %s" % rest)

    def render(self, data_input, search_table, out_path, subject=None):
        """
        Render data_input back into a file.
        data_input is either a string or a filename
        search_table is a hash of metadata keys and values
        out_path if not-none writes the results to a file
        (though results are always returned)
        subject is a profile or system object, if available (for snippet eval)
        """

        if type(data_input) != str:
           raw_data = data_input.read()
        else:
           raw_data = data_input

        self.check_for_invalid_imports(raw_data)

        # backward support for Cobbler's legacy (and slightly more readable) 
        # template syntax.
        raw_data = raw_data.replace("TEMPLATE::","$")

        # HACK:  the ksmeta field may contain nfs://server:/mount in which
        # case this is likely WRONG for kickstart, which needs the NFS
        # directive instead.  Do this to make the templates work.
        newdata = ""
        if search_table.has_key("tree") and search_table["tree"].startswith("nfs://"): 
            for line in raw_data.split("\n"):
               if line.find("--url") != -1 and line.find("url ") != -1:
                   rest = search_table["tree"][6:] # strip off "nfs://" part
                   try:
                       (server, dir) = rest.split(":",2)
                   except:
                       raise CX(_("Invalid syntax for NFS path given during import: %s" % search_table["tree"]))
                   line = "nfs --server %s --dir %s" % (server,dir)
                   # but put the URL part back in so koan can still see
                   # what the original value was
                   line = line + "\n" + "#url --url=%s" % search_table["tree"]
               newdata = newdata + line + "\n"
            raw_data = newdata 

        # tell Cheetah not to blow up if it can't find a symbol for something
        raw_data = "#errorCatcher Echo\n" + raw_data

        table_copy = search_table.copy()
 
        # for various reasons we may want to call a module inside a template and pass
        # it all of the template variables.  The variable "template_universe" serves
        # this purpose to make it easier to iterate through all of the variables without
        # using internal Cheetah variables

        search_table.update({
           "template_universe" : table_copy
        })

        # now do full templating scan, where we will also templatify the snippet insertions
        t = Template(source=raw_data, errorCatcher="Echo", searchList=[search_table])
        try:
            data_out = str(t)
        except Exception, e:
            if out_path is None:
               return utils.cheetah_exc(e)
            else:
               # FIXME: log this
               print utils.cheetah_exc(e)
               raise CX("Error templating file: %s" % out_path)

        # now apply some magic post-filtering that is used by cobbler import and some
        # other places, but doesn't use Cheetah.  Forcing folks to double escape
        # things would be very unwelcome.

        hp = search_table.get("http_port","80")
        server = search_table.get("server","server.example.org")
        repstr = "%s:%s" % (server, hp)
        search_table["http_server"] = repstr

        for x in search_table.keys():
           data_out = data_out.replace("@@%s@@" % str(x), str(search_table[str(x)]))
 
        # remove leading newlines which apparently breaks AutoYAST ?
        if data_out.startswith("\n"):
            data_out = data_out.strip() 

        if out_path is not None:
            utils.mkdir(os.path.dirname(out_path))
            fd = open(out_path, "w+")
            fd.write(data_out)
            fd.close()

        return data_out
