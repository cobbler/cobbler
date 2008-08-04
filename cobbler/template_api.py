"""
Cobbler provides builtin methods for use in Cheetah templates. $SNIPPET is one
such function and is now used to implement Cobbler's SNIPPET:: syntax.

Copyright 2008, The Defense Information Systems Agency
Daniel Guernsey <danpg102@gmail.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import Cheetah.Template
import os.path

# This class is defined using the Cheetah language. Using the 'compile' function
# we can compile the source directly into a python class. This class will allow
# us to define the cheetah builtins.

BuiltinTemplate = Cheetah.Template.Template.compile(source="\n".join([

    # This part (see 'Template' below
    # for the other part) handles the actual inclusion of the file contents. We
    # still need to make the snippet's namespace (searchList) available to the
    # template calling SNIPPET (done in the other part).
    
    # TODO: Should this be in its own file? If so, should it go into
    # /var/lib/cobbler or should it go with cobbler's site-package?
    # how about /etc/cobbler/cheetah.conf ? -- mpd

    "#def SNIPPET($file)",
        "#set $fullpath = $find_snippet($file)",
        "#if $fullpath",
            "#include $fullpath",
        "#else",
            "# Error: no snippet data",
        "#end if",
    "#end def",
    
    # Comment every line containing the $pattern given
    "#def comment_lines($filename, $pattern, $commentchar='#')",
        "perl -npe 's/^(.*${pattern}.*)$/${commentchar}\\${1}/' -i '$filename'",
    "#end def",
    
    # Comments every line which contains only the exact pattern.
    "#def comment_lines_exact($filename, $pattern, $commentchar='#')",
        "perl -npe 's/^(${pattern})$/${commentchar}\\${1}/' -f '$filename'",
    "#end def",
    
    # Uncomments every (commented) line containing the pattern
    # Patterns should not contain the #
    "#def uncomment_lines($filename, $pattern, $commentchar='#')",
        "perl -npe 's/^[ \\t]*${commentchar}(.*${pattern}.*)$/\\${1}/' -i '$filename'",
    "#end def",
    
    # Nullify (by changing to 'true') all instances of a given sh command. This
    # does understand lines with multiple commands (separated by ';') and also
    # knows to ignore comments. Consider other options before using this
    # method.
    "#def delete_command($filename, $pattern)",
        "sed -nr '",
        "    h",
        "    s/^([^#]*)(#?.*)$/\\1/",
        "    s/((^|;)[ \\t]*)${pattern}([ \\t]*($|;))/\\1true\\3/g",
        "    s/((^|;)[ \\t]*)${pattern}([ \\t]*($|;))/\\1true\\3/g",
        "    x",
        "    s/^([^#]*)(#?.*)$/\\2/",
        "    H",
        "    x",
        "    s/\\n//",
        "    p",
        "' -i '$filename'",
    "#end def",
    
    # Replace a configuration parameter value, or add it if it doesn't exist.
    # Assumes format is [param_name] [value]
    "#def set_config_value($filename, $param_name, $value)",
        "if [ -n \"\\$(grep -Ee '^[ \\t]*${param_name}[ \\t]+' '$filename')\" ]",
        "then",
        "    perl -npe 's/^([ \\t]*${param_name}[ \\t]+)[\\x21-\\x7E]*([ \\t]*(#.*)?)$/\\${1}${sedesc($value)}\\${2}/' -i '$filename'",
        "else",
        "    echo '$param_name $value' >> '$filename'",
        "fi",
    "#end def",
    
    # Replace a configuration parameter value, or add it if it doesn't exist.
    # Assues format is [param_name] [delimiter] [value], where [delimiter] is
    # usually '='.
    "#def set_config_value_delim($filename, $param_name, $delim, $value)",
        "if [ -n \"\\$(grep -Ee '^[ \\t]*${param_name}[ \\t]*${delim}[ \\t]*' '$filename')\" ]",
        "then",
        "    perl -npe 's/^([ \\t]*${param_name}[ \\t]*${delim}[ \\t]*)[\\x21-\\x7E]*([ \\t]*(#.*)?)$/${1}${sedesc($value)}${2}/' -i '$filename'",
        "else",
        "    echo '$param_name$delim$value' >> '$filename'",
        "fi",
    "#end def",
    
    # Copy a file from the server to the client.
    "#def copy_over_file($serverfile, $clientfile)",
        "cat << 'EOF' > '$clientfile'",
        "#include $files + $serverfile",
        "EOF",
    "#end def",
    
    # Copy a file from the server and append the contents to a file on the
    # client.
    "#def copy_over_file($serverfile, $clientfile)",
        "cat << 'EOF' >> '$clientfile'",
        "#include $files + $serverfile",
        "EOF",
    "#end def",
    
    # Convenience function: Copy/append several files at once. This accepts a
    # list of tuples. The first element indicates whether to overwrite ('w') or
    # append ('a'). The second element is the file name on both the server and
    # the client (a '/' is prepended on the client side).
    "#def copy_files($filelist)",
        "#for $thisfile in $filelist",
            "#if $thisfile[0] == 'a'",
                "$copy_append_file($thisfile[1], '/' + $thisfile[1])",
            "#else",
                "$copy_over_file($thisfile[1], '/' + $thisfile[1])",
            "#end if",
        "#end for",
    "#end def",
    
    # Append some content to the todo file. NOTE: $todofile must be defined
    # before using this (unless you want unexpected results). Be sure to end
    # the content with 'EOF'
    "#def TODO()",
        "cat << 'EOF' >> '$todofile'",
    "#end def",
    
    # Set the owner, group, and permissions for several files. Assignment can
    # be plain ('p') or recursive. If recursive you can assign everything ('r')
    # or just files ('f'). This method takes a list of tuples. The first element
    # of each indicates which style. The remaining elements are owner, group,
    # and mode respectively. If 'f' is used, an additional element is a find
    # pattern that can further restrict assignments (use '*' if no additional
    # restrict is desired).
    "#def set_permissions($filelist)",
        "#for $file in $filelist",
            "#if $file[0] == 'p'",
                "#if $file[1] != '' and $file[2] != ''",
                    "chown '$file[1]:$file[2]' '$file[4]'",
                "#else",
                    "#if $file[1] != ''",
                        "chown '$file[1]' '$file[4]'",
                    "#end if",
                    "#if $file[2] != ''",
                        "chgrp '$file[2]' '$file[4]'",
                    "#end if",
                "#end if",
                "#if $file[3] != ''",
                    "chmod '$file[3]' '$file[4]'",
                "#end if",
            "#elif $file[0] == 'r'",
                "#if $file[1] != '' and $file[2] != ''",
                    "chown -R '$file[1]:$file[2]' '$file[4]'",
                "#else",
                    "#if $file[1] != ''",
                        "chown -R '$file[1]' '$file[4]'",
                    "#end if",
                    "#if $file[2] != ''",
                        "chgrp -R '$file[2]' '$file[4]'",
                    "#end if",
                "#end if",
                "#if $file[3] != ''",
                    "chmod -R '$file[3]' '$file[4]'",
                "#end if",
            "#elif $file[0] == 'f'",
                "#if $file[1] != '' and $file[2] != ''",
                    "find $file[4] -name '$file[5]' -type f -exec chown -R '$file[1]:$file[2]' {} \\;",
                "#else",
                    "#if $file[1] != ''",
                        "find $file[4] -name '$file[5]' -type f -exec chown -R '$file[1]' {} \\;",
                    "#end if",
                    "#if $file[2] != ''",
                        "find $file[4] -name '$file[5]' -type f -exec chgrp -R '$file[2]' {} \\;",
                    "#end if",
                "#end if",
                "#if $file[3] != ''",
                    "find $file[4] -name '$file[5]' -type f -exec chmod -R '$file[3]' {} \\;",
                "#end if",
            "#end if",
        "#end for",
    "#end def",
    
    # Cheeseball an entire directory.
    "#def includeall($dir)",
        "#import os",
        "#for $file in $os.listdir($snippetsdir + '/' + $dir)",
            "#include $snippetsdir + '/' + $dir + '/' + $file",
        "#end for",
    "#end def",

]) + "\n")


class Template(BuiltinTemplate):

    """
    This class will allow us to include any pure python builtin functions.
    It derives from the cheetah-compiled class above. This way, we can include
    both types (cheetah and pure python) of builtins in the same base template.
    We don't need to override __init__
    """
 
    # OK, so this function gets called by Cheetah.Template.Template.__init__ to
    # compile the template into a class. This is probably a kludge, but it
    # add a baseclass argument to the standard compile (see Cheetah's compile
    # docstring) and returns the resulting class. This argument, of course,
    # points to this class. Now any methods entered here (or in the base class
    # above) will be accessible to all cheetah templates compiled by cobbler.

    def compile(klass, *args, **kwargs):
        """
        Compile a cheetah template with cobbler modifications. Modifications
        include SNIPPET:: syntax replacement and inclusion of cobbler builtin
        methods.
        """

        # We can do the SNIPPET:: syntax replacements here, effectively making
        # it recursive. Any cheetah template compiled by cobbler will have this
        # replacement

        def replace_token(token):
            if token.startswith('SNIPPET::'):
                snippet_name = token.replace('SNIPPET::', '')
                return "$SNIPPET('%s')" % snippet_name
            else:
                return token

        def replace_line(line):
            return ' '.join([replace_token(token) for token in line.split(' ')])

        def preprocess(source, file):
            # Normally, the cheetah compiler worries about this, but we need to
            # preprocess the actual source
            if source is None:
                if isinstance(file, (str, unicode)):
                    f = open(file)
                    source = f.read()
                    f.close()
                elif hasattr(file, 'read'):
                    source = file.read()
                file = None # Stop Cheetah from throwing a fit.
            return ('\n'.join([replace_line(line) for line in source.split('\n')]), file)
        preprocessors = [preprocess]
        if kwargs.has_key('preprocessors'):
            preprocessors.extend(kwargs['preprocessors'])
        kwargs['preprocessors'] = preprocessors
        
        # Instruct Cheetah to use this class as the base for all cheetah templates
        if not kwargs.has_key('baseclass'):
            kwargs['baseclass'] = Template
        
        # Now let Cheetah do the actual compilation
        return Cheetah.Template.Template.compile(*args, **kwargs)
    compile = classmethod(compile)
    
    def find_snippet(self, file):
        """
        Locate the appropriate snippet for the current system and profile.
        This will first check for a per_system snippet, a per_profile snippet,
        and a general snippet. If no snippet is located, it returns None.
        """
        if self.varExists('system_name'):
            fullpath = '%s/per_system/%s/%s' % (self.getVar('snippetsdir'), file, self.getVar('system_name'))
            if os.path.exists(fullpath):
                return fullpath
        if self.varExists('profile_name'):
            fullpath = '%s/per_profile/%s/%s' % (self.getVar('snippetsdir'), file, self.getVar('profile_name'))
            if os.path.exists(fullpath):
                return fullpath
        fullpath = '%s/%s' % (self.getVar('snippetsdir'), file)
        if os.path.exists(fullpath):
            return fullpath
        return None
    
    # This may be a little frobby, but it's really cool. This is a pure python
    # portion of SNIPPET that appends the snippet's searchList to the caller's
    # searchList. This makes any #defs within a given snippet available to the
    # template that included the snippet.

    def SNIPPET(self, file):
        """
        Include the contents of the named snippet here. This is equivalent to
        the #include directive in Cheetah, except that it searches for system
        and profile specific snippets, and it includes the snippet's namespace.
        """
        # First, do the actual inclusion. Cheetah (when processing #include)
        # will track the inclusion in self._CHEETAH__cheetahIncludes
        result = BuiltinTemplate.SNIPPET(self, file)
        
        # Now do our dirty work: locate the new include, and append its
        # searchList to ours.
        # We have to compute the full path again? Eww.
        fullpath = self.find_snippet(file);
        if fullpath:
            # Only include what we don't already have. Because Cheetah
            # passes our searchList into included templates, the snippet's
            # searchList will include this templates searchList. We need to
            # avoid duplicating entries.
            childList = self._CHEETAH__cheetahIncludes[fullpath].searchList()
            myList = self.searchList()
            for childElem in childList:
                if not childElem in myList:
                    myList.append(childElem)
        
        return result
    
    def sedesc(self, value):
        """
	Escape a string for use in sed.
	"""
        def escchar(c):
            if c in '/^.[]$()|*+?{}\\':
                return '\\' + c
            else:
                return c
        return ''.join([escchar(c) for c in value])


