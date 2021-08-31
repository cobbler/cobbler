"""
This module contains Python triggers for Cobbler.
With Cobbler one is able to add custom actions and commands after many events happening in Cobbler. The Python modules
presented here are an example of what can be done after certain events. Custom triggers may be added in any language as
long as Cobbler is allowed to execute them. If implemented in Python they need to follow the following specification:

- Expose a method called ``register()`` which returns a ``str`` and returns the path of the trigger in the filesystem.
- Expose a method called ``run(api, args)`` of type ``int``. The integer would represent the exit status of an e.g.
  shell script. Thus 0 means success and anything else a failure.
"""
