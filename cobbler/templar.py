"""
Cobbler uses Cheetah templates for lots of stuff, but there's
some additional magic around that to deal with snippets/etc.
(And it's not spelled wrong!)

Copyright 2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
import os.path
import glob
from cexceptions import *
from templateapi import Template
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

        # now do full templating scan, where we will also templatify the snippet insertions
        t = Template(source=raw_data, searchList=[search_table])
        try:
            data_out = str(t)
        except:
            print "There appears to be an formatting error in the template file."
            print "For completeness, the traceback from Cheetah has been included below."
            raise

        # now apply some magic post-filtering that is used by cobbler import and some
        # other places, but doesn't use Cheetah.  Forcing folks to double escape
        # things would be very unwelcome.

        for x in search_table:
           if type(search_table[x]) == str:
               data_out = data_out.replace("@@%s@@" % x, search_table[x])
        
        # remove leading newlines which apparently breaks AutoYAST ?
        if data_out.startswith("\n"):
            data_out = data_out.strip() 

        if out_path is not None:
            utils.mkdir(os.path.dirname(out_path))
            fd = open(out_path, "w+")
            fd.write(data_out)
            fd.close()

        return data_out
