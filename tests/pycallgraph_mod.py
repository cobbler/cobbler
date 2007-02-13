#!/usr/bin/env python
"""
pycallgraph
http://pycallgraph.slowchop.com/
Copyright Gerald Kaszuba 2007

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
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

# slight modifications for Cobbler testing
# Michael DeHaan <mdehaan@redhat.com>, 2007
"""

import inspect
import sys
import os
import tempfile

# statistical data
def reset_trace():
    global call_dict
    call_dict = {}
    global call_stack
    call_stack = ['__main__']
    global func_count
    func_count = {}
    global func_count_max
    func_count_max = 0

reset_trace()

# graphviz settings
graph_attributes = {
    'graph': {
    },
    'node': {
        'color': '.5 0 .9',
        'style': 'filled',
        'shape': 'rect',
        'fontname': 'Helvetica',
        'fontsize': 10,
    },
}

# settings for building dot files
settings = {
   'node_attributes': {
       'label': r'%(func)s\ncalls: %(hits)i',
       'color': '%(col)s',
    },
    'node_color': lambda calls, : '%f %f %f' % (calls / 2 + .5, calls, 0.9),
    'edge_color': lambda calls, : '%f %f %f' % (calls / 2 + .5, calls, 0.7),
    'exclude_module': [ 
        'yaml', 'yaml.load', 'yaml.stream', 'sre', 'unittest',
        'sys', 'os', 'subprocess', 'string', 'time', 'test', 'posixpath', 'random',
        'shutil', 'pycallgraph', 'stat', 'tempfile', 'socket', 'glob', 'sub_process', 
        'errno', 'weakref', 'traceback' 
    ],
    'exclude_class': [],
    'exclude_func': [],
    'exclude_specific': ['stop_trace', 'make_graph'],
    'include_module': [],
    'include_class': [],
    'include_func': [],
    'include_specific': [],
    'dont_exclude_anything': False,
}

class PyCallGraphException(Exception):
    pass

def start_trace(reset=True):
    if reset:
        reset_trace()
    sys.settrace(tracer)

def stop_trace():
    sys.settrace(None)

def tracer(frame, event, arg):
    global func_count_max

    if event == 'call':
        dont_keep = False
        code = frame.f_code
   
        # work out the module
        module = inspect.getmodule(code)
        if module:
            module_name = module.__name__ 
            if module_name == '__main__':
                module_name = ''
            else:
                if settings['include_module']:
                    if module_name not in settings['include_module']:
                        dont_keep = True
                else:
                    # if module_name in settings['exclude_module']:
                    #    dont_keep = True
                    for x in settings['exclude_module']:
                        if module_name.startswith(x):
                            dont_keep = True
                module_name += '.'
        else:
            module_name = 'unknown.'
            dont_keep = True

        # work out the instance, if we're in a class
        try:
            class_name = frame.f_locals['self'].__class__.__name__
            if settings['include_class']:
                if class_name not in settings['include_class']:
                    dont_keep = True
            else:
                if class_name in settings['exclude_class']:
                    dont_keep = True
            class_name += '.'
        except (KeyError, AttributeError):
            class_name = ''

        # work out the current function or method
        func_name = code.co_name
        if func_name == '?':
            func_name = '__main__'
        else:
            if settings['include_func']:
                if func_name not in settings['include_func']:
                    dont_keep = True
            else:
                if func_name in settings['exclude_func']:
                    dont_keep = True

        # join em together in a readable form
        full_name = '%s%s%s' % (module_name, class_name, func_name)

        if full_name in settings['exclude_specific']:
            dont_keep = True

        # throw it all in dictonaires
        fr = call_stack[-1]
        if not dont_keep or settings['dont_exclude_anything']:
            if fr not in call_dict:
                call_dict[fr] = {}
            if full_name not in call_dict[fr]:
                call_dict[fr][full_name] = 0
            call_dict[fr][full_name] += 1
            if full_name not in func_count:
                func_count[full_name] = 0
            func_count[full_name] += 1
            if func_count[full_name] > func_count_max:
                func_count_max = func_count[full_name]
            call_stack.append(full_name)
        else:
            call_stack.append('')
    if event == 'return':
        if call_stack:
            call_stack.pop(-1)

def get_dot(stop=True):
    if stop:
        stop_trace()
    ret = ['digraph G {',]
    for comp, comp_attr in graph_attributes.items():
        ret.append('%s [' % comp)
        for attr, val in comp_attr.items():
            ret.append('%(attr)s = "%(val)s",' % locals())
        ret.append('];')
    for func, hits in func_count.items():
        frac = float(hits) / func_count_max 
        col = settings['node_color'](frac)
        attribs = ['%s="%s"' % a for a in settings['node_attributes'].items()]
        node_str = '"%s" [%s];' % (func, ','.join(attribs))
        ret.append(node_str % locals())
    for fr_key, fr_val in call_dict.items():
        if fr_key == '':
            continue
        for to_key, to_val in fr_val.items():
            frac = float(to_val) / func_count_max
            col = settings['edge_color'](frac)
            edge = '[ color = "%s" ]' % col
            ret.append('"%s"->"%s" %s' % (fr_key, to_key, edge))
    ret.append('}')
    return '\n'.join(ret)

def save_dot(filename):
    open(filename, 'w').write(get_dot())

def make_graph(filename, format='png', tool='dot', stop=True):
    if stop:
        stop_trace()
    fd, tempname = tempfile.mkstemp()
    f = os.fdopen(fd, 'w')
    f.write(get_dot())
    f.close()
    cmd = '%(tool)s -T%(format)s -o%(filename)s %(tempname)s' % locals()
    ret = os.system(cmd)
    os.unlink(tempname)
    if ret:
        raise PyCallGraphException('The command "%(cmd)s" failed with error' \
            'code %(ret)i.' % locals())

if __name__ == '__main__':

    f = 'test.png'
    print 'Starting trace'
    start_trace()
    import re
    re.compile('h(e)l[A-Z]lo.*th[^e]*e(r)e')
    print 'Generating graph'
    stop_trace()
    make_graph(f)
    print '%s should be in this directiory. Hit enter to quit.' % f
    raw_input()

__version__ = "$Revision: $"
# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

