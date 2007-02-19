#!/usr/bin/env python
# $Id: DummyTransaction.py,v 1.13 2005/11/13 01:12:13 tavis_rudd Exp $

"""Provides dummy Transaction and Response classes is used by Cheetah in place
of real Webware transactions when the Template obj is not used directly as a
Webware servlet.

Meta-Data
==========
Author: Tavis Rudd <tavis@damnsimple.com>
Version: $Revision: 1.13 $
Start Date: 2001/08/30
Last Revision Date: $Date: 2005/11/13 01:12:13 $
"""
__author__ = "Tavis Rudd <tavis@damnsimple.com>"
__revision__ = "$Revision: 1.13 $"[11:-2]

def flush():
    pass

class DummyResponse:
    
    """A dummy Response class is used by Cheetah in place of real Webware
    Response objects when the Template obj is not used directly as a Webware
    servlet.  """

    
    def __init__(self):
        self._outputChunks = outputChunks = []
        self.write = write = outputChunks.append
        def getvalue(outputChunks=outputChunks):
            return ''.join(outputChunks)
        self.getvalue = getvalue
            
        def writeln(txt):
            write(txt)
            write('\n')
        self.writeln = writeln        
        self.flush = flush

    def writelines(self, *lines):
        ## not used
        [self.writeln(ln) for ln in lines]
        
class DummyTransaction:

    """A dummy Transaction class is used by Cheetah in place of real Webware
    transactions when the Template obj is not used directly as a Webware
    servlet.

    It only provides a response object and method.  All other methods and
    attributes make no sense in this context.
    """
    
    def __init__(self, DummyResponse=DummyResponse):       
        def response(resp=DummyResponse()):
            return resp
        self.response = response
