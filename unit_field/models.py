# -*- coding: utf-8 -*-
import warnings


class UnitModelMixin(object):
    def __init__(self, *args, **kwargs):
        warnings.warn(u'The UnitModelMixin overriding __getattr__ is deprecated, instead for a field "foo", the '
                      'properties "foo_html", "foo_label_key" and "foo_label_value" are available automatically. '
                      'This mixin can be removed from classes using it.',
                      DeprecationWarning, stacklevel=2)
        super(UnitModelMixin, self).__init__(*args, **kwargs)
