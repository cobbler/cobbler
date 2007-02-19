#!/usr/bin/env python
"""Nothing, but in a friendly way.  Good for filling in for objects you want to
hide.  If $form.f1 is a RecursiveNull object, then
$form.f1.anything["you"].might("use") will resolve to the empty string.

This module was contributed by Ian Bicking.
"""

class RecursiveNull:
      __doc__ = __doc__ # Use the module's docstring for the class's docstring.
      def __getattr__(self, attr):
              return self
      def __getitem__(self, item):
              return self
      def __call__(self, *vars, **kw):
              return self
      def __str__(self):
              return ''
      def __repr__(self):
              return ''
      def __nonzero__(self):
              return 0

