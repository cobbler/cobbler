#!/usr/bin/env python
# $Id: VerifyType.py,v 1.4 2005/11/02 22:26:08 tavis_rudd Exp $
"""Functions to verify an argument's type

Meta-Data
================================================================================
Author: Mike Orr <iron@mso.oz.net>
License: This software is released for unlimited distribution under the
         terms of the MIT license.  See the LICENSE file.
Version: $Revision: 1.4 $
Start Date: 2001/11/07
Last Revision Date: $Date: 2005/11/02 22:26:08 $
""" 
__author__ = "Mike Orr <iron@mso.oz.net>"
__revision__ = "$Revision: 1.4 $"[11:-2]

##################################################
## DEPENDENCIES

import types       # Used in VerifyTypeClass.

##################################################
## PRIVATE FUNCTIONS

def _errmsg(argname, ltd, errmsgExtra=''):
    """Construct an error message.

    argname, string, the argument name.
    ltd, string, description of the legal types.
    errmsgExtra, string, text to append to error mssage.
    Returns: string, the error message.
    """
    if errmsgExtra:
        errmsgExtra = '\n' + errmsgExtra
    return "arg '%s' must be %s%s" % (argname, ltd, errmsgExtra)


##################################################
## TYPE VERIFICATION FUNCTIONS

def VerifyType(arg, argname, legalTypes, ltd, errmsgExtra=''):
    """Verify the type of an argument.
    
    arg, any, the argument.
    argname, string, name of the argument.
    legalTypes, list of type objects, the allowed types.
    ltd, string, description of legal types (for error message).
    errmsgExtra, string, text to append to error message.
    Returns: None.
    Exceptions: TypeError if 'arg' is the wrong type.
    """
    if type(arg) not in legalTypes:
        m = _errmsg(argname, ltd, errmsgExtra)
        raise TypeError(m)


def VerifyTypeClass(arg, argname, legalTypes, ltd, klass, errmsgExtra=''):
    """Same, but if it's a class, verify it's a subclass of the right class.

    arg, any, the argument.
    argname, string, name of the argument.
    legalTypes, list of type objects, the allowed types.
    ltd, string, description of legal types (for error message).
    klass, class, the parent class.
    errmsgExtra, string, text to append to the error message.
    Returns: None.
    Exceptions: TypeError if 'arg' is the wrong type.
    """
    VerifyType(arg, argname, legalTypes, ltd, errmsgExtra)
    # If no exception, the arg is a legal type.
    if type(arg) == types.ClassType and not issubclass(arg, klass):
        # Must test for "is class type" to avoid TypeError from issubclass().
        m = _errmsg(argname, ltd, errmsgExtra)
        raise TypeError(m)

# @@MO: Commented until we determine whether it's useful.
#def VerifyClass(arg, argname, klass, ltd):
#    """Same, but allow *only* a subclass of the right class.
#    """
#    VerifyTypeClass(arg, argname, [types.ClassType], ltd, klass)

# vim: shiftwidth=4 tabstop=4 expandtab
