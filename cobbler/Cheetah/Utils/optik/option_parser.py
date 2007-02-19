"""optik.option_parser

Provides the OptionParser and Values classes.

Cheetah modifications:  added "Cheetah.Utils.optik." prefix to
  all intra-Optik imports.
"""

__revision__ = "$Id: option_parser.py,v 1.2 2002/09/12 06:56:51 hierro Exp $"

# Copyright (c) 2001 Gregory P. Ward.  All rights reserved.
# See the README.txt distributed with Optik for licensing terms.

# created 2001/10/17, GPW (from optik.py)

import sys, os
import types
from Cheetah.Utils.optik.option import Option, NO_DEFAULT
from Cheetah.Utils.optik.errors import OptionConflictError, OptionValueError, BadOptionError

def get_prog_name ():
    return os.path.basename(sys.argv[0])


SUPPRESS_HELP = "SUPPRESS"+"HELP"
SUPPRESS_USAGE = "SUPPRESS"+"USAGE"

STD_HELP_OPTION = Option("-h", "--help",
                         action="help",
                         help="show this help message and exit")
STD_VERSION_OPTION = Option("--version",
                            action="version",
                            help="show program's version number and exit")


class Values:

    def __init__ (self, defaults=None):
        if defaults:
            for (attr, val) in defaults.items():
                setattr(self, attr, val)


    def _update_careful (self, dict):
        """
        Update the option values from an arbitrary dictionary, but only
        use keys from dict that already have a corresponding attribute
        in self.  Any keys in dict without a corresponding attribute
        are silently ignored.
        """
        for attr in dir(self):
            if dict.has_key(attr):
                dval = dict[attr]
                if dval is not None:
                    setattr(self, attr, dval)

    def _update_loose (self, dict):
        """
        Update the option values from an arbitrary dictionary,
        using all keys from the dictionary regardless of whether
        they have a corresponding attribute in self or not.
        """
        self.__dict__.update(dict)

    def _update (self, dict, mode):
        if mode == "careful":
            self._update_careful(dict)
        elif mode == "loose":
            self._update_loose(dict)
        else:
            raise ValueError, "invalid update mode: %r" % mode

    def read_module (self, modname, mode="careful"):
        __import__(modname)
        mod = sys.modules[modname]
        self._update(vars(mod), mode)

    def read_file (self, filename, mode="careful"):
        vars = {}
        execfile(filename, vars)
        self._update(vars, mode)

    def ensure_value (self, attr, value):
        if not hasattr(self, attr) or getattr(self, attr) is None:
            setattr(self, attr, value)
        return getattr(self, attr)


class OptionParser:
    """
    Class attributes:
      standard_option_list : [Option]
        list of standard options that will be accepted by all instances
        of this parser class (intended to be overridden by subclasses).

    Instance attributes:
      usage : string
        a usage string for your program.  Before it is displayed
        to the user, "%prog" will be expanded to the name of
        your program (os.path.basename(sys.argv[0])).
      option_list : [Option]
        the list of all options accepted on the command-line of
        this program
      _short_opt : { string : Option }
        dictionary mapping short option strings, eg. "-f" or "-X",
        to the Option instances that implement them.  If an Option
        has multiple short option strings, it will appears in this
        dictionary multiple times.
      _long_opt : { string : Option }
        dictionary mapping long option strings, eg. "--file" or
        "--exclude", to the Option instances that implement them.
        Again, a given Option can occur multiple times in this
        dictionary.
      _long_opts : [string]
        list of long option strings recognized by this option
        parser.  Should be equal to _long_opt.values().
      defaults : { string : any }
        dictionary mapping option destination names to default
        values for each destination.

      allow_interspersed_args : boolean = true
        if true, positional arguments may be interspersed with options.
        Assuming -a and -b each take a single argument, the command-line
          -ablah foo bar -bboo baz
        will be interpreted the same as
          -ablah -bboo -- foo bar baz
        If this flag were false, that command line would be interpreted as
          -ablah -- foo bar -bboo baz
        -- ie. we stop processing options as soon as we see the first
        non-option argument.  (This is the tradition followed by
        Python's getopt module, Perl's Getopt::Std, and other argument-
        parsing libraries, but it is generally annoying to users.)

      rargs : [string]
        the argument list currently being parsed.  Only set when
        parse_args() is active, and continually trimmed down as
        we consume arguments.  Mainly there for the benefit of
        callback options.
      largs : [string]
        the list of leftover arguments that we have skipped while
        parsing options.  If allow_interspersed_args is false, this
        list is always empty.
      values : Values
        the set of option values currently being accumulated.  Only
        set when parse_args() is active.  Also mainly for callbacks.

    Because of the 'rargs', 'largs', and 'values' attributes,
    OptionParser is not thread-safe.  If, for some perverse reason, you
    need to parse command-line arguments simultaneously in different
    threads, use different OptionParser instances.
    
    """ 

    standard_option_list = [STD_HELP_OPTION]


    def __init__ (self,
                  usage=None,
                  option_list=None,
                  option_class=Option,
                  version=None,
                  conflict_handler="error"):
        self.set_usage(usage)
        self.option_class = option_class
        self.version = version
        self.set_conflict_handler(conflict_handler)
        self.allow_interspersed_args = 1

        # Create the various lists and dicts that constitute the
        # "option list".  See class docstring for details about
        # each attribute.
        self._create_option_list()

        # Populate the option list; initial sources are the
        # standard_option_list class attribute, the 'option_list'
        # argument, and the STD_VERSION_OPTION global (if 'version'
        # supplied).
        self._populate_option_list(option_list)

        self._init_parsing_state()

    # -- Private methods -----------------------------------------------
    # (used by the constructor)

    def _create_option_list (self):
        self.option_list = []
        self._short_opt = {}            # single letter -> Option instance
        self._long_opt = {}             # long option -> Option instance
        self._long_opts = []            # list of long options
        self.defaults = {}              # maps option dest -> default value

    def _populate_option_list (self, option_list):
        if self.standard_option_list:
            self.add_options(self.standard_option_list)
        if self.version:
            self.add_option(STD_VERSION_OPTION)
        if option_list:
            self.add_options(option_list)
        
    def _init_parsing_state (self):
        # These are set in parse_args() for the convenience of callbacks.
        self.rargs = None
        self.largs = None
        self.values = None


    # -- Simple modifier methods ---------------------------------------

    def set_usage (self, usage):
        if usage is None:
            self.usage = "usage: %prog [options]"
        elif usage is SUPPRESS_USAGE:
            self.usage = None
        else:
            self.usage = usage

    def enable_interspersed_args (self):
        self.allow_interspersed_args = 1

    def disable_interspersed_args (self):
        self.allow_interspersed_args = 0

    def set_conflict_handler (self, handler):
        if handler not in ("ignore", "error", "resolve"):
            raise ValueError, "invalid conflict_resolution value %r" % handler
        self.conflict_handler = handler

    def set_default (self, dest, value):
        self.defaults[dest] = value

    def set_defaults (self, **kwargs):
        self.defaults.update(kwargs)


    # -- Option-adding methods -----------------------------------------

    def _check_conflict (self, option):
        conflict_opts = []
        for opt in option._short_opts:
            if self._short_opt.has_key(opt):
                conflict_opts.append((opt, self._short_opt[opt]))
        for opt in option._long_opts:
            if self._long_opt.has_key(opt):
                conflict_opts.append((opt, self._long_opt[opt]))

        if conflict_opts:
            handler = self.conflict_handler
            if handler == "ignore":     # behaviour for Optik 1.0, 1.1
                pass
            elif handler == "error":    # new in 1.2
                raise OptionConflictError(
                    "conflicting option string(s): %s"
                    % ", ".join([co[0] for co in conflict_opts]),
                    option)
            elif handler == "resolve":  # new in 1.2
                for (opt, c_option) in conflict_opts:
                    if opt.startswith("--"):
                        c_option._long_opts.remove(opt)
                        del self._long_opt[opt]
                    else:
                        c_option._short_opts.remove(opt)
                        del self._short_opt[opt]
                    if not (c_option._short_opts or c_option._long_opts):
                        self.option_list.remove(c_option)


    def add_option (self, *args, **kwargs):
        """add_option(Option)
           add_option(opt_str, ..., kwarg=val, ...)
        """
        if type(args[0]) is types.StringType:
            option = self.option_class(*args, **kwargs)
        elif len(args) == 1 and not kwargs:
            option = args[0]
            if not isinstance(option, Option):
                raise TypeError, "not an Option instance: %r" % option
        else:
            raise TypeError, "invalid arguments"

        self._check_conflict(option)

        self.option_list.append(option)
        for opt in option._short_opts:
            self._short_opt[opt] = option
        for opt in option._long_opts:
            self._long_opt[opt] = option
            self._long_opts.append(opt)

        if option.dest is not None:     # option has a dest, we need a default
            if option.default is not NO_DEFAULT:
                self.defaults[option.dest] = option.default
            elif not self.defaults.has_key(option.dest):
                self.defaults[option.dest] = None

    def add_options (self, option_list):
        for option in option_list:
            self.add_option(option)


    # -- Option query/removal methods ----------------------------------

    def get_option (self, opt_str):
        return (self._short_opt.get(opt_str) or
                self._long_opt.get(opt_str))

    def has_option (self, opt_str):
        return (self._short_opt.has_key(opt_str) or
                self._long_opt.has_key(opt_str))


    def remove_option (self, opt_str):
        option = self._short_opt.get(opt_str)
        if option is None:
            option = self._long_opt.get(opt_str)
        if option is None:
            raise ValueError("no such option %r" % opt_str)

        for opt in option._short_opts:
            del self._short_opt[opt]
        for opt in option._long_opts:
            del self._long_opt[opt]
            self._long_opts.remove(opt)
        self.option_list.remove(option)


    # -- Option-parsing methods ----------------------------------------

    def _get_args (self, args):
        if args is None:
            return sys.argv[1:]
        else:
            return args[:]              # don't modify caller's list

    def parse_args (self, args=None, values=None):
        """
        parse_args(args : [string] = sys.argv[1:],
                   values : Values = None)
        -> (values : Values, args : [string])

        Parse the command-line options found in 'args' (default:
        sys.argv[1:]).  Any errors result in a call to 'error()', which
        by default prints the usage message to stderr and calls
        sys.exit() with an error message.  On success returns a pair
        (values, args) where 'values' is an Values instance (with all
        your option values) and 'args' is the list of arguments left
        over after parsing options.
        """
        rargs = self._get_args(args)
        if values is None:
            values = Values(self.defaults)

        # Store the halves of the argument list as attributes for the
        # convenience of callbacks:
        #   rargs
        #     the rest of the command-line (the "r" stands for
        #     "remaining" or "right-hand")
        #   largs
        #     the leftover arguments -- ie. what's left after removing
        #     options and their arguments (the "l" stands for "leftover"
        #     or "left-hand")

        # Say this is the original argument list:
        # [arg0, arg1, ..., arg(i-1), arg(i), arg(i+1), ..., arg(N-1)]
        #                            ^
        # (we are about to process arg(i)).
        #
        # Then rargs is [arg(i), ..., arg(N-1)]
        # and largs is a *subset* of [arg0, ..., arg(i-1)]
        # (any options and their arguments will have been removed
        # from largs).
        #
        # _process_arg() will always consume 1 or more arguments.
        # If it consumes 1 (eg. arg is an option that takes no arguments),
        # then after _process_arg() is done the situation is:
        #   largs = subset of [arg0, ..., arg(i)]
        #   rargs = [arg(i+1), ..., arg(N-1)]
        #
        # If allow_interspersed_args is false, largs will always be
        # *empty* -- still a subset of [arg0, ..., arg(i-1)], but
        # not a very interesting subset!

        self.rargs = rargs
        self.largs = largs = []
        self.values = values

        stop = 0
        while rargs and not stop:
            try:
                stop = self._process_arg(largs, rargs, values)
            except (BadOptionError, OptionValueError), err:
                self.error(err.msg)

        args = largs + rargs
        return self.check_values(values, args)

    def check_values (self, values, args):
        """
        check_values(values : Values, args : [string])
        -> (values : Values, args : [string])

        Check that the supplied option values and leftover arguments are
        valid.  Returns the option values and leftover arguments
        (possibly adjusted, possibly completely new -- whatever you
        like).  Default implementation just returns the passed-in
        values; subclasses may override as desired.
        """
        return (values, args)

    def _process_arg (self, largs, rargs, values):
        """_process_args(largs : [string],
                         rargs : [string],
                         values : Values)
           -> stop : boolean

        Process a single command-line argument, consuming zero or more
        arguments.  The next argument to process is rargs[0], which will
        almost certainly be consumed from rargs.  (It might wind up in
        largs, or it might affect a value in values, or -- if a callback
        is involved -- almost anything might happen.  It will not be
        consumed if it is a non-option argument and
        allow_interspersed_args is false.)  More arguments from rargs
        may also be consumed, depending on circumstances.

        Returns true if option processing should stop after this
        argument is processed.
        """

        # We handle bare "--" explicitly, and bare "-" is handled by the
        # standard arg handler since the short arg case ensures that the len
        # of the opt string is greater than 1.

        arg = rargs[0]
        if arg == "--":
            del rargs[0]
            return 1
        elif arg[0:2] == "--":
            # process a single long option (possibly with value(s))
            self._process_long_opt(rargs, values)
        elif arg[:1] == "-" and len(arg) > 1:
            # process a cluster of short options (possibly with
            # value(s) for the last one only)
            self._process_short_opts(rargs, values)
        else:
            if self.allow_interspersed_args:
                largs.append(arg)
                del rargs[0]
            else:
                return 1                # stop now, leave this arg in rargs

        return 0                        # keep processing args
        
    def _match_long_opt (self, opt):
        """_match_long_opt(opt : string) -> string

        Determine which long option string 'opt' matches, ie. which one
        it is an unambiguous abbrevation for.  Raises BadOptionError if
        'opt' doesn't unambiguously match any long option string.
        """
        return _match_abbrev(opt, self._long_opts)

    def _process_long_opt (self, rargs, values):
        arg = rargs.pop(0)

        # Value explicitly attached to arg?  Pretend it's the next
        # argument.
        if "=" in arg:
            (opt, next_arg) = arg.split("=", 1)
            rargs.insert(0, next_arg)
            had_explicit_value = 1
        else:
            opt = arg
            had_explicit_value = 0

        opt = self._match_long_opt(opt)
        option = self._long_opt[opt]
        if option.takes_value():
            nargs = option.nargs
            if len(rargs) < nargs:
                if nargs == 1:
                    self.error("%s option requires a value" % opt)
                else:
                    self.error("%s option requires %d values"
                               % (opt, nargs))
            elif nargs == 1:
                value = rargs.pop(0)
            else:
                value = tuple(rargs[0:nargs])
                del rargs[0:nargs]

        elif had_explicit_value:
            self.error("%s option does not take a value" % opt)

        else:
            value = None

        option.process(opt, value, values, self)

    def _process_short_opts (self, rargs, values):
        arg = rargs.pop(0)
        stop = 0
        i = 1
        for ch in arg[1:]:
            opt = "-" + ch
            option = self._short_opt.get(opt)
            i += 1                      # we have consumed a character

            if not option:
                self.error("no such option: %s" % opt)
            if option.takes_value():
                # Any characters left in arg?  Pretend they're the
                # next arg, and stop consuming characters of arg.
                if i < len(arg):
                    rargs.insert(0, arg[i:])
                    stop = 1

                nargs = option.nargs
                if len(rargs) < nargs:
                    if nargs == 1:
                        self.error("%s option requires a value" % opt)
                    else:
                        self.error("%s option requires %s values"
                                   % (opt, nargs))
                elif nargs == 1:
                    value = rargs.pop(0)
                else:
                    value = tuple(rargs[0:nargs])
                    del rargs[0:nargs]

            else:                       # option doesn't take a value
                value = None

            option.process(opt, value, values, self)

            if stop:
                break


    # -- Output/error methods ------------------------------------------

    def error (self, msg):
        self.print_usage(sys.stderr)
        sys.exit("%s: error: %s" % (get_prog_name(), msg))

    def print_usage (self, file=None):
        if self.usage:
            usage = self.usage.replace("%prog", get_prog_name())
            print >>file, usage
            print >>file

    def print_version (self, file=None):
        if self.version:
            version = self.version.replace("%prog", get_prog_name())
            print >>file, version

    def print_help (self, file=None):
        from distutils.fancy_getopt import wrap_text
        
        if file is None:
            file = sys.stdout

        self.print_usage(file)

        # The help for each option consists of two parts:
        #   * the opt strings and metavars
        #     eg. ("-x", or "-fFILENAME, --file=FILENAME")
        #   * the user-supplied help string
        #     eg. ("turn on expert mode", "read data from FILENAME")
        #
        # If possible, we write both of these on the same line:
        #   -x      turn on expert mode
        # 
        # But if the opt string list is too long, we put the help
        # string on a second line, indented to the same column it would
        # start in if it fit on the first line.
        #   -fFILENAME, --file=FILENAME
        #           read data from FILENAME

        print >>file, "options:"
        width = 78                      # assume 80 cols for now

        option_help = []                # list of (string, string) tuples
        lengths = []

        for option in self.option_list:
            takes_value = option.takes_value()
            if takes_value:
                metavar = option.metavar or option.dest.upper()

            opts = []               # list of "-a" or "--foo=FILE" strings
            if option.help is SUPPRESS_HELP:
                continue

            if takes_value:
                for sopt in option._short_opts:
                    opts.append(sopt + metavar)
                for lopt in option._long_opts:
                    opts.append(lopt + "=" + metavar)
            else:
                for opt in option._short_opts + option._long_opts:
                    opts.append(opt)

            opts = ", ".join(opts)
            option_help.append((opts, option.help))
            lengths.append(len(opts))

        max_opts = min(max(lengths), 20)

        for (opts, help) in option_help:
            # how much to indent lines 2 .. N of help text
            indent_rest = 2 + max_opts + 2 
            help_width = width - indent_rest

            if len(opts) > max_opts:
                opts = "  " + opts + "\n"
                indent_first = indent_rest

            else:                       # start help on same line as opts
                opts = "  %-*s  " % (max_opts, opts)
                indent_first = 0

            file.write(opts)

            if help:
                help_lines = wrap_text(help, help_width)
                print >>file, "%*s%s" % (indent_first, "", help_lines[0])
                for line in help_lines[1:]:
                    print >>file, "%*s%s" % (indent_rest, "", line)
            elif opts[-1] != "\n":
                file.write("\n")

# class OptionParser


def _match_abbrev (s, words):
    """_match_abbrev(s : string, words : [string]) -> string

    Returns the string in 'words' for which 's' is an unambiguous
    abbreviation.  If 's' is found to be ambiguous or doesn't match any
    of 'words', raises BadOptionError.
    """ 
    match = None
    for word in words:
        # If s isn't even a prefix for this word, don't waste any
        # more time on it: skip to the next word and try again.
        if not word.startswith(s):
            continue

        # Exact match?  Great, return now.
        if s == word:
            return word

        # Now comes the tricky business of disambiguation.  At this
        # point, we know s is a proper prefix of word, eg. s='--foo' and
        # word=='--foobar'.  If we have already seen another word where
        # this was the case, eg. '--foobaz', fail: s is ambiguous.
        # Otherwise record this match and keep looping; we will return
        # if we see an exact match, or when we fall out of the loop and
        # it turns out that the current word is the match.
        if match:
            raise BadOptionError("ambiguous option: %s (%s, %s, ...?)"
                                 % (s, match, word))
        match = word

    if match:
        return match
    else:
        raise BadOptionError("no such option: %s" % s)
