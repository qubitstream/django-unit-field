# -*- coding: utf-8 -*-
import unicodedata

import six
from django import VERSION as DJANGO_VERSION
from django.conf import settings
from django.utils.formats import get_format

"""
Use Django's django.utils.formats.sanitize_formats of Version 1.8
to guarantee the same behaviour in older Django versions (<= 1.7)
"""


def sanitize_separators(value, force_custom_func=False):
    """
    Sanitizes a value according to the current decimal and
    thousand separator setting. Used with form field input.

    force_custom_func: do not use Django's native sanitize_separators, even if it is available in a
        proper version
    """

    if settings.USE_L10N and isinstance(value, six.string_types):
        if (DJANGO_VERSION[0] > 1 or (DJANGO_VERSION[0] == 1 and DJANGO_VERSION[1] >= 8)) and not force_custom_func:
            # Better to use the current native version if possible...
            from django.utils.formats import sanitize_separators as django_sanitize_separators
            return django_sanitize_separators(value)

        parts = []
        decimal_separator = get_format('DECIMAL_SEPARATOR')
        if decimal_separator in value:
            value, decimals = value.split(decimal_separator, 1)
            parts.append(decimals)
        if settings.USE_THOUSAND_SEPARATOR:
            thousand_sep = get_format('THOUSAND_SEPARATOR')
            if thousand_sep == '.' and value.count('.') == 1 and \
                    len(value.split('.')[-1]) != 3:
                # Special case where we suspect a dot meant decimal separator
                # (see #22171)
                pass
            else:
                for replacement in set([
                        thousand_sep, unicodedata.normalize('NFKD', thousand_sep)]):
                    value = value.replace(replacement, '')
        parts.append(value)
        value = '.'.join(reversed(parts))
    return value
