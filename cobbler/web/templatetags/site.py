from builtins import object
from django import template
from collections import OrderedDict

register = template.Library()

# ==========================

# -*- coding: utf-8 -*-
'''
A smarter {% if %} tag for django templates.

While retaining current Django functionality, it also handles equality,
greater than and less than operators. Some common case examples::

    {% if articles|length >= 5 %}...{% endif %}
    {% if "ifnotequal tag" != "beautiful" %}...{% endif %}
'''
import unittest
from django import template


register = template.Library()


# ===============================================================================
# Calculation objects
# ===============================================================================

class BaseCalc(object):
    def __init__(self, var1, var2=None, negate=False):
        self.var1 = var1
        self.var2 = var2
        self.negate = negate

    def resolve(self, context):
        try:
            var1, var2 = self.resolve_vars(context)
            outcome = self.calculate(var1, var2)
        except:
            outcome = False
        if self.negate:
            return not outcome
        return outcome

    def resolve_vars(self, context):
        var2 = self.var2 and self.var2.resolve(context)
        return self.var1.resolve(context), var2

    def calculate(self, var1, var2):
        raise NotImplementedError()


class Or(BaseCalc):
    def calculate(self, var1, var2):
        return var1 or var2


class And(BaseCalc):
    def calculate(self, var1, var2):
        return var1 and var2


class Equals(BaseCalc):
    def calculate(self, var1, var2):
        return var1 == var2


class Greater(BaseCalc):
    def calculate(self, var1, var2):
        return var1 > var2


class GreaterOrEqual(BaseCalc):
    def calculate(self, var1, var2):
        return var1 >= var2


class In(BaseCalc):
    def calculate(self, var1, var2):
        return var1 in var2


# ===============================================================================
# Tests
# ===============================================================================

class TestVar(object):
    """
    A basic self-resolvable object similar to a Django template variable. Used
    to assist with tests.
    """
    def __init__(self, value):
        self.value = value

    def resolve(self, context):
        return self.value


class SmartIfTests(unittest.TestCase):
    def setUp(self):
        self.true = TestVar(True)
        self.false = TestVar(False)
        self.high = TestVar(9000)
        self.low = TestVar(1)

    def assertCalc(self, calc, context=None):
        """
        Test a calculation is True, also checking the inverse "negate" case.
        """
        context = context or {}
        self.assertTrue(calc.resolve(context))
        calc.negate = not calc.negate
        self.assertFalse(calc.resolve(context))

    def assertCalcFalse(self, calc, context=None):
        """
        Test a calculation is False, also checking the inverse "negate" case.
        """
        context = context or {}
        self.assertFalse(calc.resolve(context))
        calc.negate = not calc.negate
        self.assertTrue(calc.resolve(context))

    def test_or(self):
        self.assertCalc(Or(self.true))
        self.assertCalcFalse(Or(self.false))
        self.assertCalc(Or(self.true, self.true))
        self.assertCalc(Or(self.true, self.false))
        self.assertCalc(Or(self.false, self.true))
        self.assertCalcFalse(Or(self.false, self.false))

    def test_and(self):
        self.assertCalc(And(self.true, self.true))
        self.assertCalcFalse(And(self.true, self.false))
        self.assertCalcFalse(And(self.false, self.true))
        self.assertCalcFalse(And(self.false, self.false))

    def test_equals(self):
        self.assertCalc(Equals(self.low, self.low))
        self.assertCalcFalse(Equals(self.low, self.high))

    def test_greater(self):
        self.assertCalc(Greater(self.high, self.low))
        self.assertCalcFalse(Greater(self.low, self.low))
        self.assertCalcFalse(Greater(self.low, self.high))

    def test_greater_or_equal(self):
        self.assertCalc(GreaterOrEqual(self.high, self.low))
        self.assertCalc(GreaterOrEqual(self.low, self.low))
        self.assertCalcFalse(GreaterOrEqual(self.low, self.high))

    def test_in(self):
        list_ = TestVar([1, 2, 3])
        invalid_list = TestVar(None)
        self.assertCalc(In(self.low, list_))
        self.assertCalcFalse(In(self.low, invalid_list))

    def test_parse_bits(self):
        var = IfParser([True]).parse()
        self.assertTrue(var.resolve({}))
        var = IfParser([False]).parse()
        self.assertFalse(var.resolve({}))

        var = IfParser([False, 'or', True]).parse()
        self.assertTrue(var.resolve({}))

        var = IfParser([False, 'and', True]).parse()
        self.assertFalse(var.resolve({}))

        var = IfParser(['not', False, 'and', 'not', False]).parse()
        self.assertTrue(var.resolve({}))

        var = IfParser([1, '=', 1]).parse()
        self.assertTrue(var.resolve({}))

        var = IfParser([1, '!=', 1]).parse()
        self.assertFalse(var.resolve({}))

        var = IfParser([3, '>', 2]).parse()
        self.assertTrue(var.resolve({}))

        var = IfParser([1, '<', 2]).parse()
        self.assertTrue(var.resolve({}))

        var = IfParser([2, 'not', 'in', [2, 3]]).parse()
        self.assertFalse(var.resolve({}))

    def test_boolean(self):
        var = IfParser([True, 'and', True, 'and', True]).parse()
        self.assertTrue(var.resolve({}))
        var = IfParser([False, 'or', False, 'or', True]).parse()
        self.assertTrue(var.resolve({}))
        var = IfParser([True, 'and', False, 'or', True]).parse()
        self.assertTrue(var.resolve({}))
        var = IfParser([False, 'or', True, 'and', True]).parse()
        self.assertTrue(var.resolve({}))

        var = IfParser([True, 'and', True, 'and', False]).parse()
        self.assertFalse(var.resolve({}))
        var = IfParser([False, 'or', False, 'or', False]).parse()
        self.assertFalse(var.resolve({}))
        var = IfParser([False, 'or', True, 'and', False]).parse()
        self.assertFalse(var.resolve({}))
        var = IfParser([False, 'and', True, 'or', False]).parse()
        self.assertFalse(var.resolve({}))


OPERATORS = {
    '=': (Equals, True),
    '==': (Equals, True),
    '!=': (Equals, False),
    '>': (Greater, True),
    '>=': (GreaterOrEqual, True),
    '<=': (Greater, False),
    '<': (GreaterOrEqual, False),
    'or': (Or, True),
    'and': (And, True),
    'in': (In, True),
}


class IfParser(object):
    error_class = ValueError

    def __init__(self, tokens):
        self.tokens = tokens

    def _get_tokens(self):
        return self._tokens

    def _set_tokens(self, tokens):
        self._tokens = tokens
        self.len = len(tokens)
        self.pos = 0

    tokens = property(_get_tokens, _set_tokens)

    def parse(self):
        if self.at_end():
            raise self.error_class('No variables provided.')
        var1 = self.get_var()
        while not self.at_end():
            token = self.get_token()
            if token == 'not':
                if self.at_end():
                    raise self.error_class('No variable provided after "not".')
                token = self.get_token()
                negate = True
            else:
                negate = False
            if token not in OPERATORS:
                raise self.error_class('%s is not a valid operator.' % token)
            if self.at_end():
                raise self.error_class('No variable provided after "%s"' % token)
            op, true = OPERATORS[token]
            if not true:
                negate = not negate
            var2 = self.get_var()
            var1 = op(var1, var2, negate=negate)
        return var1

    def get_token(self):
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def at_end(self):
        return self.pos >= self.len

    def create_var(self, value):
        return TestVar(value)

    def get_var(self):
        token = self.get_token()
        if token == 'not':
            if self.at_end():
                raise self.error_class('No variable provided after "not".')
            token = self.get_token()
            return Or(self.create_var(token), negate=True)
        return self.create_var(token)


# ===============================================================================
# Actual templatetag code.
# ===============================================================================

class TemplateIfParser(IfParser):
    error_class = template.TemplateSyntaxError

    def __init__(self, parser, *args, **kwargs):
        self.template_parser = parser
        super(TemplateIfParser, self).__init__(*args, **kwargs)

    def create_var(self, value):
        return self.template_parser.compile_filter(value)


class SmartIfNode(template.Node):
    def __init__(self, var, nodelist_true, nodelist_false=None):
        self.nodelist_true, self.nodelist_false = nodelist_true, nodelist_false
        self.var = var

    def render(self, context):
        if self.var.resolve(context):
            return self.nodelist_true.render(context)
        if self.nodelist_false:
            return self.nodelist_false.render(context)
        return ''

    def __repr__(self):
        return "<Smart If node>"

    def __iter__(self):
        for node in self.nodelist_true:
            yield node
        if self.nodelist_false:
            for node in self.nodelist_false:
                yield node

    def get_nodes_by_type(self, nodetype):
        nodes = []
        if isinstance(self, nodetype):
            nodes.append(self)
        nodes.extend(self.nodelist_true.get_nodes_by_type(nodetype))
        if self.nodelist_false:
            nodes.extend(self.nodelist_false.get_nodes_by_type(nodetype))
        return nodes


# @register.tag('if')
def smart_if(parser, token):
    '''
    A smarter {% if %} tag for django templates.

    While retaining current Django functionality, it also handles equality,
    greater than and less than operators. Some common case examples::

        {% if articles|length >= 5 %}...{% endif %}
        {% if "ifnotequal tag" != "beautiful" %}...{% endif %}

    Arguments and operators _must_ have a space between them, so
    ``{% if 1>2 %}`` is not a valid smart if tag.

    All supported operators are: ``or``, ``and``, ``in``, ``=`` (or ``==``),
    ``!=``, ``>``, ``>=``, ``<`` and ``<=``.
    '''
    bits = token.split_contents()[1:]
    var = TemplateIfParser(parser, bits).parse()
    nodelist_true = parser.parse(('else', 'endsmart_if'))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse(('endsmart_if',))
        parser.delete_first_token()
    else:
        nodelist_false = None
    return SmartIfNode(var, nodelist_true, nodelist_false)


# ==========================

ifinlist = register.tag(smart_if)

# ==========================

# Based on code found here:
# http://stackoverflow.com/questions/2024660/django-sort-dict-in-template
#
# Required since dict.items|dictsort doesn't seem to work
# when iterating over the keys with a for loop


@register.filter(name='sort')
def listsort(value):
    if isinstance(value, dict):
        new_dict = OrderedDict()
        key_list = list(value.keys())
        key_list.sort()
        for key in key_list:
            new_dict[key] = value[key]
        return new_dict
    elif isinstance(value, list):
        new_list = list(value)
        new_list.sort()
        return new_list
    else:
        return value
    listsort.is_safe = True
