# -*- Mode: Python; test-case-name: test_command -*-
# vi:si:et:sw=4:sts=4:ts=4

# This file is released under the standard PSF license.
#
#  from MOAP - https://thomas.apestaart.org/moap/trac
#    written by Thomas Vander Stichele (thomas at apestaart dot org)
#

# Modified from usage in func
# https://hosted.fedoraproject.org/projects/func/

"""
Command class.
"""

import optparse
import sys

# from func.config import read_config, CONFIG_FILE
# from func.commonconfig import CMConfig

class CommandHelpFormatter(optparse.IndentedHelpFormatter):
    """
    I format the description as usual, but add an overview of commands
    after it if there are any, formatted like the options.
    """
    _commands = None

    def addCommand(self, name, description):
        if self._commands is None:
            self._commands = {}
        self._commands[name] = description

    ### override parent method
    def format_description(self, description):
        # textwrap doesn't allow for a way to preserve double newlines
        # to separate paragraphs, so we do it here.
        blocks = description.split('\n\n')
        rets = []

        for block in blocks:
            rets.append(optparse.IndentedHelpFormatter.format_description(self,
                block))
        ret = "\n".join(rets)
        if self._commands:
            commandDesc = []
            commandDesc.append("commands:")
            keys = self._commands.keys()
            keys.sort()
            length = 0
            for key in keys:
                if len(key) > length:
                    length = len(key)
            for name in keys:
                format = "  %-" + "%d" % length + "s  %s"
                commandDesc.append(format % (name, self._commands[name]))
            ret += "\n" + "\n".join(commandDesc) + "\n"
        return ret

class CommandOptionParser(optparse.OptionParser):
    """
    I parse options as usual, but I explicitly allow setting stdout
    so that our print_help() method (invoked by default with -h/--help)
    defaults to writing there.
    """
    _stdout = sys.stdout

    def set_stdout(self, stdout):
        self._stdout = stdout

    # we're overriding the built-in file, but we need to since this is
    # the signature from the base class
    __pychecker__ = 'no-shadowbuiltin'
    def print_help(self, file=None):
        # we are overriding a parent method so we can't do anything about file
        __pychecker__ = 'no-shadowbuiltin'
        if file is None:
            file = self._stdout
        file.write(self.format_help())

class Command:
    """
    I am a class that handles a command for a program.
    Commands can be nested underneath a command for further processing.

    @cvar name:        name of the command, lowercase
    @cvar aliases:     list of alternative lowercase names recognized
    @type aliases:     list of str
    @cvar usage:       short one-line usage string;
                       %command gets expanded to a sub-command or [commands]
                       as appropriate
    @cvar summary:     short one-line summary of the command
    @cvar description: longer paragraph explaining the command
    @cvar subCommands: dict of name -> commands below this command
    @type subCommands: dict of str  -> L{Command}
    """
    name = None
    aliases = None
    usage = None
    summary = None
    description = None
    parentCommand = None
    subCommands = None
    subCommandClasses = None
    aliasedSubCommands = None

    def __init__(self, parentCommand=None, stdout=sys.stdout,
        stderr=sys.stderr):
        """
        Create a new command instance, with the given parent.
        Allows for redirecting stdout and stderr if needed.
        This redirection will be passed on to child commands.
        """
        if not self.name:
            self.name = str(self.__class__).split('.')[-1].lower()
        self.stdout = stdout
        self.stderr = stderr
        self.parentCommand = parentCommand

        # from Func, now removed:
        # self.config = read_config(CONFIG_FILE, CMConfig)

        # create subcommands if we have them
        self.subCommands = {}
        self.aliasedSubCommands = {}
        if self.subCommandClasses:
            for C in self.subCommandClasses:
                c = C(self, stdout=stdout, stderr=stderr)
                self.subCommands[c.name] = c
                if c.aliases:
                    for alias in c.aliases:
                        self.aliasedSubCommands[alias] = c

        # create our formatter and add subcommands if we have them
        formatter = CommandHelpFormatter()
        if self.subCommands:
            for name, command in self.subCommands.items():
                formatter.addCommand(name, command.summary or
                    command.description)

        # expand %command for the bottom usage
        usage = self.usage or self.name
        if usage.find("%command") > -1:
            usage = usage.split("%command")[0] + '[command]'
        usages = [usage, ]

        # FIXME: abstract this into getUsage that takes an optional
        # parentCommand on where to stop recursing up
        # useful for implementing subshells

        # walk the tree up for our usage
        c = self.parentCommand
        while c:
            usage = c.usage or c.name
            if usage.find(" %command") > -1:
                usage = usage.split(" %command")[0]
            usages.append(usage)
            c = c.parentCommand
        usages.reverse()
        usage = " ".join(usages)

        # create our parser
        description = self.description or self.summary
        self.parser = CommandOptionParser(
            usage=usage, description=description,
            formatter=formatter)
        self.parser.set_stdout(self.stdout)
        self.parser.disable_interspersed_args()

        # allow subclasses to add options
        self.addOptions()

    def addOptions(self):
        """
        Override me to add options to the parser.
        """
        pass

    def do(self, args):
        """
        Override me to implement the functionality of the command.
        """
        pass

    def parse(self, argv):
        """
        Parse the given arguments and act on them.

        @rtype:   int
        @returns: an exit code
        """
        self.options, args = self.parser.parse_args(argv)

        # FIXME: make handleOptions not take options, since we store it
        # in self.options now
        ret = self.handleOptions(self.options)
        if ret:
            return ret

        # handle pleas for help
        if args and args[0] == 'help':
            self.debug('Asked for help, args %r' % args)

            # give help on current command if only 'help' is passed
            if len(args) == 1:
                self.outputHelp()
                return 0

            # complain if we were asked for help on a subcommand, but we don't
            # have any
            if not self.subCommands:
                self.stderr.write('No subcommands defined.')
                self.parser.print_usage(file=self.stderr)
                self.stderr.write(
                    "Use --help to get more information about this command.\n")
                return 1

            # rewrite the args the other way around;
            # help doap becomes doap help so it gets deferred to the doap
            # command
            args = [args[1], args[0]]


        # if we have args that we need to deal with, do it now
        # before we start looking for subcommands
        self.handleArguments(args)

        # if we don't have subcommands, defer to our do() method
        if not self.subCommands:
            ret = self.do(args)

            # if everything's fine, we return 0
            if not ret:
                ret = 0

            return ret


        # if we do have subcommands, defer to them
        try:
            command = args[0]
        except IndexError:
            self.parser.print_usage(file=self.stderr)
            self.stderr.write(
                "Use --help to get a list of commands.\n")
            return 1

        if command in self.subCommands.keys():
            return self.subCommands[command].parse(args[1:])

        if self.aliasedSubCommands:
            if command in self.aliasedSubCommands.keys():
                return self.aliasedSubCommands[command].parse(args[1:])

        self.stderr.write("Unknown command '%s'.\n" % command)
        return 1

    def outputHelp(self):
        """
        Output help information.
        """
        self.parser.print_help(file=self.stderr)

    def outputUsage(self):
        """
        Output usage information.
        Used when the options or arguments were missing or wrong.
        """
        self.parser.print_usage(file=self.stderr)

    def handleOptions(self, options):
        """
        Handle the parsed options.
        """
        pass

    def handleArguments(self, arguments):
        """
        Handle the parsed arguments.
        """
        pass

    def getRootCommand(self):
        """
        Return the top-level command, which is typically the program.
        """
        c = self
        while c.parentCommand:
            c = c.parentCommand
        return c
