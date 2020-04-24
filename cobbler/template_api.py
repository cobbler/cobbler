"""
Cobbler provides builtin methods for use in Cheetah templates. $SNIPPET is one
such function and is now used to implement Cobbler's SNIPPET:: syntax.

Written by Daniel Guernsey <danpg102@gmail.com>
Contributions by Michael DeHaan <michael.dehaan AT gmail>
US Government work; No explicit copyright attached to this file.

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

import Cheetah.Template as cheetah_template
import os.path
import re

from cobbler.cexceptions import FileNotFoundException
from cobbler import utils

CHEETAH_MACROS_FILE = '/etc/cobbler/cheetah_macros'

# This class is defined using the Cheetah language. Using the 'compile' function
# we can compile the source directly into a python class. This class will allow
# us to define the cheetah builtins.


class Template(cheetah_template.Template):
    """
    This class will allow us to include any pure python builtin functions.
    It derives from the cheetah-compiled class above. This way, we can include both types (cheetah and pure python) of
    builtins in the same base template. We don't need to override __init__
    """

    def __init__(self, **kwargs):
        """
        Constructor for this derived class. We include two additional default templates.

        :param kwargs: These arguments get passed to the super constructor of this class.
        """
        self.MacrosTemplate = Template.compile(file=CHEETAH_MACROS_FILE)
        self.BuiltinTemplate = Template.compile(source="\n".join([

            # This part (see 'Template' below
            # for the other part) handles the actual inclusion of the file contents. We
            # still need to make the snippet's namespace (searchList) available to the
            # template calling SNIPPET (done in the other part).

            # Moved the other functions into /etc/cobbler/cheetah_macros
            # Left SNIPPET here since it is very important.

            # This function can be used in two ways:
            # Cheetah syntax:
            #
            # $SNIPPET('my_snippet')
            #
            # SNIPPET syntax:
            #
            # SNIPPET::my_snippet
            #
            # This follows all of the rules of snippets and advanced snippets. First it
            # searches for a per-system snippet, then a per-profile snippet, then a
            # general snippet. If none is found, a comment explaining the error is
            # substituted.
            "#def SNIPPET($file)",
            "#set $snippet = $read_snippet($file)",
            "#if $snippet",
            "#include source=$snippet",
            "#else",
            "# Error: no snippet data for $file",
            "#end if",
            "#end def",
        ]) + "\n")
        super(Template, self).__init__(**kwargs)

    # OK, so this function gets called by Cheetah.Template.Template.__init__ to compile the template into a class. This
    # is probably a kludge, but it add a baseclass argument to the standard compile (see Cheetah's compile docstring)
    # and returns the resulting class. This argument, of course, points to this class. Now any methods entered here (or
    # in the base class above) will be accessible to all cheetah templates compiled by Cobbler.

    @classmethod
    def compile(cls, *args, **kwargs):
        """
        Compile a cheetah template with Cobbler modifications. Modifications include SNIPPET:: syntax replacement and
        inclusion of Cobbler builtin methods.

        :param args: These just get passed right to Cheetah.
        :param kwargs: We just execute our own preprocessors and remove them and let afterwards handle Cheetah the rest.
        :return: The compiled template.
        :rtype: bytes
        """
        def replacer(match):
            return "$SNIPPET('%s')" % match.group(1)

        def preprocess(source, file):
            # Normally, the cheetah compiler worries about this, but we need to preprocess the actual source.
            if source is None:
                if hasattr(file, 'read'):
                    source = file.read()
                else:
                    if os.path.exists(file):
                        with open(file, "r") as f:
                            source = "#errorCatcher Echo\n" + f.read()
                    else:
                        source = "# Unable to read %s\n" % file
                file = None     # Stop Cheetah from throwing a fit.

            rx = re.compile(r'SNIPPET::([A-Za-z0-9_\-\/\.]+)')
            results = rx.sub(replacer, source)
            return results, file
        preprocessors = [preprocess]
        if 'preprocessors' in kwargs:
            preprocessors.extend(kwargs['preprocessors'])
        kwargs['preprocessors'] = preprocessors

        # Instruct Cheetah to use this class as the base for all cheetah templates
        if 'baseclass' not in kwargs:
            kwargs['baseclass'] = Template

        # Now let Cheetah do the actual compilation
        return super(Template, cls).compile(*args, **kwargs)

    def read_snippet(self, file):
        """
        Locate the appropriate snippet for the current system and profile and read it's contents.

        This file could be located in a remote location.

        This will first check for a per-system snippet, a per-profile snippet, a distro snippet, and a general snippet.
        If no snippet is located, it returns None.

        :param file: The file to read-
        :return: None (if the snippet file was not found) or the string with the read snippet.
        :rtype: str
        """
        for snipclass in ('system', 'profile', 'distro'):
            if self.varExists('%s_name' % snipclass):
                fullpath = '%s/per_%s/%s/%s' % (self.getVar('autoinstall_snippets_dir'),
                                                snipclass, file,
                                                self.getVar('%s_name' % snipclass))
                try:
                    contents = utils.read_file_contents(fullpath, fetch_if_remote=True)
                    return contents
                except FileNotFoundException:
                    pass

        try:
            return "#errorCatcher ListErrors\n" + utils.read_file_contents('%s/%s' % (self.getVar('autoinstall_snippets_dir'), file), fetch_if_remote=True)
        except FileNotFoundException:
            return None

    def SNIPPET(self, file):
        """
        Include the contents of the named snippet here. This is equivalent to the #include directive in Cheetah, except
        that it searches for system and profile specific snippets, and it includes the snippet's namespace.

        This may be a little frobby, but it's really cool. This is a pure python portion of SNIPPET that appends the
        snippet's searchList to the caller's searchList. This makes any #defs within a given snippet available to the
        template that included the snippet.

        :param file: The snippet file to read and include in the template.
        :return: The updated template.
        """
        # First, do the actual inclusion. Cheetah (when processing #include) will track the inclusion in
        # self._CHEETAH__cheetahIncludes
        result = self.BuiltinTemplate.SNIPPET(self, file)

        # Now do our dirty work: locate the new include, and append its searchList to ours. We have to compute the full
        # path again? Eww.

        # This weird method is getting even weirder, the cheetah includes keys are no longer filenames but actual
        # contents of snippets. Regardless this seems to work and hopefully it will be ok.

        snippet_contents = self.read_snippet(file)
        if snippet_contents:
            # Only include what we don't already have. Because Cheetah passes our searchList into included templates,
            # the snippet's searchList will include this templates searchList. We need to avoid duplicating entries.
            childList = self._CHEETAH__cheetahIncludes[snippet_contents].searchList()
            myList = self.searchList()
            for childElem in childList:
                if childElem not in myList:
                    myList.append(childElem)

        return result

    # This function is used by several cheetah methods in cheetah_macros. It can be used by the end user as well.
    # Ex: Replace all instances of '/etc/banner' with a value stored in
    # $new_banner
    #
    # sed 's/$sedesc("/etc/banner")/$sedesc($new_banner)/'
    #
    def sedesc(self, value):
        """
        Escape a string for use in sed.

        :param value: The phrase to escape.
        :return: The escaped phrase.
        """

        def escchar(c):
            if c in '/^.[]$()|*+?{}\\':
                return '\\' + c
            else:
                return c
        return ''.join([escchar(c) for c in value])
