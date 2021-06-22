# -*- coding: utf-8 -*-
import logging

from django.db.models import FloatField, CharField as ModelCharField
from django.forms import CharField
from django.template.defaultfilters import floatformat
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from unit_field import forms
from unit_field.utils import sanitize_separators

try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5
from unit_field.units import (UnitValueCreator,
                              UNITS_PERCENTAGE,
                              UNITS_LENGTH,
                              UNITS_SQUARE_MEASURE,
                              UNITS_SOLID_MEASURE,
                              UNITS_MASS,
                              UNITS_TIME,
                              UNITS_TIME2,
                              UNITS_TEMPERATURE,
                              UNITS_AMOUNT_OF_SUBSTANCE,
                              UNITS_LUMINOUS_INTENSITY,

                              UNITS_ACCELERATION,
                              UNITS_ANGLE,
                              UNITS_CRACKLE,
                              UNITS_CURRENT,
                              UNITS_DENSITY,
                              UNITS_FORCE,
                              UNITS_INERTIA_TORQUE,
                              UNITS_JERK,
                              UNITS_POTENTIAL,
                              UNITS_SNAP,
                              UNITS_SPEED,
                              UNITS_TORSION,
                              UNITS_TORQUE,
                              UNITS_VELOCITY,

                              UNITS_POWER,
                              UNITS_THERMAL_RESISTANCE,
                              UNITS_HEAT_TRANSFER_RESISTANCE,
                              UNITS_HEAT_CONDUCTANCE,
                              UNITS_HEAT_CAPACITY,
                              UNITS_SPECIFIC_HEAT_CAPACITY,
                              UNITS_MOTOR_CONSTANT,
                              UNITS_FORCE_CONSTANT,
                              UNITS_ELECTRICAL_TIME_CONSTANT,
                              UNITS_POTENTIAL_CONSTANT,
                              UNITS_ELECTRICAL_RESISTANCE,
                              UNITS_INDUCTANCE,

                              UNITS_ANGLE_VELOCITY,
                              UNITS_ANGLE_ACCELERATION,
                              UNITS_ANGLE_JERK,
                              UNITS_ANGLE_SNAP,
                              UNITS_ANGLE_CRACKLE,

                              UNITS_VISCOSITY,
                              UNITS_FLOW_RATE,
                              )

logger = logging.getLogger(__name__)


def md5_hexdigest(value):
    try:
        return md5(value).hexdigest()
    except TypeError:
        return md5(value.encode('utf8')).hexdigest()


def get_factor(units, unit_id):
    """
    Returns the factor of a Unit-Config
    """
    if not units:
        return None

    for unit in units:
        if unit.id == unit_id:
            if unit.to_base_function:
                return unit.to_base_function
            return unit.factor


class UnitInputField(FloatField):

    auto_convert = True

    def __init__(self, *args, **kwargs):
        auto_convert = kwargs.pop('auto_convert', None)
        if auto_convert is not None:
            self.auto_convert = auto_convert
        super(UnitInputField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        """
        Validates that float() can be called on the input. Returns the result
        of float(). Returns None for empty values.
        """
        value = super(FloatField, self).to_python(value)
        value = sanitize_separators(value)
        return value

    def get_prep_value(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def formfield(self, **kwargs):
        if self.auto_convert:
            defaults = {'form_class': forms.UnitInputField}
        else:
            defaults = {'form_class': CharField}
        defaults.update(kwargs)
        return super(UnitInputField, self).formfield(**defaults)


class CalculatedFloatField(FloatField):
    """
    This field is required to define the special behaviour of the
    pre-calculated field, used in UnitField
    """
    units = None

    def get_unit_by_id(self, unit_id):
        """
        returns the unit factor of the desired unit, e.g.:
        get_unit_by_id(u'dm²') ---> 0.01
        """
        return get_factor(self.units, unit_id)

    def __init__(self, *args, **kwargs):
        kwargs['editable'] = False
        self.units = kwargs.pop('units', None)
        super(CalculatedFloatField, self).__init__(*args, **kwargs)
        self.default = 0.0

    def pre_save(self, model_instance, add):
        input_field_name = self.attname.replace('_value', '_input')
        unit_field_name = self.attname.replace('_value', '_unit')

        a = getattr(model_instance, input_field_name)
        # IMPORTANT!!! NEVER USER sanitize_separators here!!!
        # b = sanitize_separators(a)
        b = a
        try:
            input_value = float(b)
        except ValueError:
            input_value = None
        unit_id = getattr(model_instance, unit_field_name)

        unit_value = self.get_unit_by_id(unit_id)

        if (not input_value is None) and (not unit_value is None):
            if hasattr(unit_value, '__call__'):
                # conversion by function
                setattr(model_instance, self.attname, unit_value(input_value))
            else:
                # conversion by factor
                setattr(model_instance, self.attname, input_value * unit_value)
        else:
            setattr(model_instance, self.attname, 0.0)
        return getattr(model_instance, self.attname)


class UnitField(FloatField):
    """
    a compound field contributes three columns to the model instead of the
    standard single column
    """
    choices = None

    units = []

    auto_convert = True

    verbose_name = u'(UnitField)'

    blank = False

    db_index = False

    null = False

    default_unit = None

    validators = []

    help_text = None

    def update_choices(self):
        """
        generates choices list, if not set
        """
        if self.choices is None:
            self.choices = []
            for unit in self.units:
                self.choices.append((unit.id, unit.abbrev, ))

    def get_base_unit(self):
        """
        returns the unit with factor == 1.0
        """
        if self.units:
            for unit in self.units:
                if unit.factor == 1.0:
                    return unit
        return None

    def get_base_unit_id(self):
        """
        returns the identifier of the base unit (e.g. "m²")
        """
        base_unit = self.get_base_unit()
        if base_unit is None:
            return None

        return base_unit.id

    @staticmethod
    def _html(instance, name):
        _field = name
        _label = _(instance._meta.get_field(_field).verbose_name)

        _unit_field = u'{}_unit'.format(name)
        _val = floatformat(getattr(instance, _field), 2)
        _method_name = u'get_%s_display' % _unit_field
        _unit_method = getattr(instance, _method_name)
        try:
            _unit_method = getattr(instance, _method_name)
            _unit_method_val = _unit_method()
        except Exception as excp:
            logger.debug(
                '{0!r}: Using unit value directly for "{1}" because of error: {2}'.format(instance, name, excp))
            _unit_method_val = getattr(instance, _unit_field)
        return mark_safe(u'<div class="row-fluid">'
                         '<div class="span6"><span class="readonly-label">%s:</span></div>'
                         '<div class="span6"><strong class="readonly-value">%s %s</strong></div>'
                         '</div>' % (_label, _val, _unit_method_val,))

    @staticmethod
    def _label_key(instance, name):
        _field = u'{}_input'.format(name)
        return instance._meta.get_field(_field).verbose_name

    @staticmethod
    def _label_value(instance, name):
        _field = u'{}_input'.format(name)
        _unit_field = u'{}_unit'.format(name)
        _val = getattr(instance, _field)
        _method_name = u'get_%s_display' % _unit_field
        try:
            _unit_method = getattr(instance, _method_name)
            _label_value = u'%s %s' % (_val, _unit_method(),)
        except Exception as excp:
            logger.debug(
                '{0!r}: Using unit value directly for "{1}" because of error: {2}'.format(instance, name, excp))
            _label_value = _val
        return _label_value

    def __init__(self, *args, **kwargs):
        if 'choices' in kwargs:
            raise TypeError("%s invalid attribute 'choices'" % (
                self.__class__.__name__, ))
        _units = kwargs.pop('units', None)
        if _units:
            self.units = _units

        self.auto_convert = kwargs.pop('auto_convert', True)
        self.verbose_name = kwargs.get('verbose_name')
        self.blank = kwargs.get('blank')
        self.null = kwargs.get('null')
        self.db_index = kwargs.get('db_index', False)
        self.validators = kwargs.get('validators', [])
        self.default = kwargs.get('default', 0.0)
        self.help_text = kwargs.get('help_text', None)
        kwargs['editable'] = False
        kwargs['default'] = self.default

        self.default_unit = kwargs.pop('default_unit',
                                       self.get_base_unit_id())
        self.update_choices()
        super(UnitField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        self.name = name

        self.input_field = UnitInputField(
            default=self.default,
            blank=self.blank,
            null=self.null,
            auto_convert=self.auto_convert,
            validators=self.validators,
            help_text=self.help_text,
            verbose_name=self.verbose_name)
        cls.add_to_class("%s_input" % (self.name,), self.input_field)

        # self.unit_field = CharField(default=self.default_unit, choices=self.choices)
        self.update_choices()
        self.unit_field = ModelCharField(max_length=10,
                                         default=self.default_unit,
                                         choices=self.choices)
        cls.add_to_class("%s_unit" % (self.name,), self.unit_field)

        self.value_field = CalculatedFloatField(default=0.0,
                                                db_index=self.db_index,
                                                units=self.units,
                                                blank=self.blank,
                                                null=self.null)
        cls.add_to_class("%s_value" % (self.name,), self.value_field)

        self.key = md5_hexdigest(self.name)

        field = UnitValueCreator(self)

        # add the properties ending with '..._html', '..._label_key', '..._label_value'
        cls.add_to_class(
            '{0.name}_html'.format(self), property(lambda instance: UnitField._html(instance, self.name)))
        cls.add_to_class(
            '{0.name}_label_key'.format(self), property(lambda instance: UnitField._label_key(instance, self.name)))
        cls.add_to_class(
            '{0.name}_label_value'.format(self), property(lambda instance: UnitField._label_value(instance, self.name)))

        setattr(cls, name, field)

    def get_db_prep_save(self, value):
        pass

    def get_db_prep_lookup(self, lookup_type, value):
        raise NotImplementedError(self.get_db_prep_lookup)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.UnitField}
        defaults.update(kwargs)
        return super(UnitField, self).formfield(**defaults)

# Fields for Base Units


class LengthField(UnitField):
    units = UNITS_LENGTH


class SquareMeasureField(UnitField):
    units = UNITS_SQUARE_MEASURE


class SolidMeasureField(UnitField):
    units = UNITS_SOLID_MEASURE


class MassField(UnitField):
    units = UNITS_MASS


class TimeField(UnitField):
    units = UNITS_TIME


class Time2Field(UnitField):
    units = UNITS_TIME2


class TemperatureField(UnitField):
    units = UNITS_TEMPERATURE


class AmountOfSubstanceField(UnitField):
    units = UNITS_AMOUNT_OF_SUBSTANCE


class LuminousIntensityField(UnitField):
    units = UNITS_LUMINOUS_INTENSITY

# Fields for Derived Units


class AccelerationField(UnitField):
    units = UNITS_ACCELERATION


class AngleField(UnitField):
    units = UNITS_ANGLE


class CrackleField(UnitField):
    units = UNITS_CRACKLE


class CurrentField(UnitField):
    units = UNITS_CURRENT


class DensityField(UnitField):
    units = UNITS_DENSITY


class ForceField(UnitField):
    units = UNITS_FORCE


class InertiaTorqueField(UnitField):
    units = UNITS_INERTIA_TORQUE


class JerkField(UnitField):
    units = UNITS_JERK


class PotentialField(UnitField):
    units = UNITS_POTENTIAL


class SnapField(UnitField):
    units = UNITS_SNAP


class SpeedField(UnitField):
    units = UNITS_SPEED


class TorqueField(UnitField):
    units = UNITS_TORQUE


class VelocityField(UnitField):
    units = UNITS_VELOCITY


class TorsionField(UnitField):
    units = UNITS_TORSION


class PowerField(UnitField):
    units = UNITS_POWER


class ThermalResistanceField(UnitField):
    units = UNITS_THERMAL_RESISTANCE


class ElectricalTimeConstantField(UnitField):
    units = UNITS_ELECTRICAL_TIME_CONSTANT


class MotorConstantField(UnitField):
    units = UNITS_MOTOR_CONSTANT


class ForceConstantField(UnitField):
    units = UNITS_FORCE_CONSTANT


class PotentialConstantField(UnitField):
    units = UNITS_POTENTIAL_CONSTANT


class ResistanceField(UnitField):
    units = UNITS_ELECTRICAL_RESISTANCE


class InductanceField(UnitField):
    units = UNITS_INDUCTANCE


class AngleVelocityField(UnitField):
    units = UNITS_ANGLE_VELOCITY


class AngleAccelerationField(UnitField):
    units = UNITS_ANGLE_ACCELERATION


class AngleJerkField(UnitField):
    units = UNITS_ANGLE_JERK


class AngleSnapField(UnitField):
    units = UNITS_ANGLE_SNAP


class AngleCrackleField(UnitField):
    units = UNITS_ANGLE_CRACKLE


class HeatTransferResistanceField(UnitField):
    units = UNITS_HEAT_TRANSFER_RESISTANCE


class HeatConductanceField(UnitField):
    units = UNITS_HEAT_CONDUCTANCE


class HeatCapacityField(UnitField):
    units = UNITS_HEAT_CAPACITY


class SpecificHeatCapacityField(UnitField):
    units = UNITS_SPECIFIC_HEAT_CAPACITY


class ViscosityField(UnitField):
    units = UNITS_VISCOSITY


class FlowRateField(UnitField):
    units = UNITS_FLOW_RATE


class PercentageField(UnitField):
    units = UNITS_PERCENTAGE


try:
    from south.modelsinspector import add_introspection_rules
    rules = [((CalculatedFloatField, ), [], {}), ]
    add_introspection_rules(rules, [
        "^unit_field\.fields"])
except ImportError:
    pass
