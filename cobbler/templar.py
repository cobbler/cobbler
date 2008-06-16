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
from Cheetah.Template import Template
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

        # replace snippets with the proper Cheetah include directives prior to processing.
        # see Wiki for full details on how snippets operate.
        snippet_results = ""
        for line in raw_data.split("\n"):
             line = self.replace_snippets(line,subject)
             snippet_results = "\n".join((snippet_results, line))
        raw_data = snippet_results

        # HACK:  the ksmeta field may contain nfs://server:/mount in which
        # case this is likely WRONG for kickstart, which needs the NFS
        # directive instead.  Do this to make the templates work.
        newdata = ""
        if search_table.has_key("tree") and search_table["tree"].startswith("nfs://"): 
            for line in data.split("\n"):
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

    def replace_snippets(self,line,subject):
        """
        Replace all SNIPPET:: syntaxes on a line with the
        results of evaluating the snippet, taking care not
        to replace tabs with spaces or anything like that
        """
        tokens = line.split(None)
        for t in tokens:
           if t.startswith("SNIPPET::"):
               snippet_name = t.replace("SNIPPET::","")
               line = line.replace(t,self.eval_snippet(snippet_name,subject))
        return line

    def eval_snippet(self,name,subject):
        """
        Replace SNIPPET::foo with contents of files:
            Use /var/lib/cobbler/snippets/per_system/$name/$sysname
                /var/lib/cobbler/snippets/per_profile/$name/$proname
                /var/lib/cobbler/snippets/$name
            in order... (first one wins)
        """

        sd = self.settings.snippetsdir
        default_path = "%s/%s" % (sd,name)  

        if subject is None:
            if os.path.exists(default_path):
                return self.slurp(default_path)
            else:
                return self.slurp(None)
            

        if subject.COLLECTION_TYPE == "system":
            profile  = self.api.find_profile(name=subject.profile)
            sys_path = "%s/per_system/%s/%s" % (sd,name,subject.name) 
            pro_path = "%s/per_profile/%s/%s" % (sd,name,profile.name) 
            if os.path.exists(sys_path):
                return self.slurp(sys_path)
            elif os.path.exists(pro_path):
                return self.slurp(pro_path)
            elif os.path.exists(default_path):
                return self.slurp(default_path)
            else:
                return self.slurp(None)

        if subject.COLLECTION_TYPE == "profile":
            pro_path = "%s/per_profile/%s/%s" % (sd,name,subject.name) 
            if os.path.exists(pro_path):
                return self.slurp(pro_path)
            elif os.path.exists(default_path):
                return self.slurp(default_path)
            else:
                return self.slurp(None)

        return self.slurp(None)

    def slurp(self,filename):
        """
        Get the contents of a filename but if none is specified
        just include some generic error text for the rendered
        template.
        """

        if filename is None:
            return "# error: no snippet data found"

        # disabling this as it requires restarting cobblerd after
        # making changes to snippets.  not good.  Since kickstart
        # templates are now generated dynamically and we don't need
        # to load all snippets to parse any given template, this should
        # be ok, leaving this in as a footnote should we need it later.
        #
        ## potentially eliminate a ton of system calls if syncing
        ## thousands of systems that use the same template
        #if self.cache.has_key(filename):
        #    
        #    return self.cache[filename]

        fd = open(filename,"r")
        data = fd.read()
        # self.cache[filename] = data
        fd.close()

        return data

