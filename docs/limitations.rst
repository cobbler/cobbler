*************************
Limitations and Surprises
*************************

Templating
==========

Before templates are passed to Jinja or Cheetah there is a pre-processing of templates happening. During pre-processing
Cobbler replaces variables like ``@@my_key@@`` in the template. Those keys are currently limited by the regex of ``\S``,
which translates to ``[^ \t\n\r\f\v]``.
