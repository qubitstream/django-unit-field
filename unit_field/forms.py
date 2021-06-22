# -*- coding: utf-8 -*-
from django import forms

__all__ = ('UnitInputField',)


class UnitInputField(forms.FloatField):
    def __init__(self, *args, **kwargs):
        kwargs['localize'] = True
        super().__init__(*args, **kwargs)

    def widget_attrs(self, widget):
        attrs = super(UnitInputField, self).widget_attrs(widget)
        attrs.update({'class': 'unit-field-input'})
        return attrs
