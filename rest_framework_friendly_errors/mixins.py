from __future__ import unicode_literals
from __future__ import unicode_literals

from typing import Mapping

from rest_framework.exceptions import ValidationError as RestValidationError
from rest_framework.fields import *
from rest_framework.relations import *
from rest_framework.utils.serializer_helpers import ReturnDict

from rest_framework_friendly_errors import settings
from rest_framework_friendly_errors.field_map import FieldMap
from rest_framework_friendly_errors.utils import as_serializer_error


class FriendlyErrorMessagesMixin(FieldMap):
    FIELD_VALIDATION_ERRORS = {}
    NON_FIELD_ERRORS = {}

    def __init__(self, *args, **kwargs):
        self.registered_errors = {}
        super(FriendlyErrorMessagesMixin, self).__init__(*args, **kwargs)

    @property
    def errors(self):
        ugly_errors = super(FriendlyErrorMessagesMixin, self).errors
        pretty_errors = self.build_pretty_errors(ugly_errors)
        return ReturnDict(pretty_errors, serializer=self)

    def run_validation(self, data=empty):
        """
        Переопределил стандартный run_validation для того,
        чтобы вызвать нашу кастомную функцию as_serializer_error
        """
        (is_empty_value, data) = self.validate_empty_values(data)
        if is_empty_value:
            return data

        value = self.to_internal_value(data)
        try:
            self.run_validators(value)
            value = self.validate(value)
            assert value is not None, '.validate() should return the validated data'
        except (ValidationError, DjangoValidationError) as exc:
            raise ValidationError(detail=as_serializer_error(exc))
        return value

    def register_error(self, error_message, field_name=None, error_key=None, error_code=None):
        # ToDo: мб убрать вообще, лень этим пользоваться
        if field_name is None:
            if error_code is None:
                raise ValueError('For non field error you must provide an error code')
            error = {
                'code': error_code,
                'message': error_message,
                'field': None
            }
        else:
            field_instance = self.fields.get(field_name)
            if field_instance is None:
                raise ValueError('Incorrect field name')

            field_type = field_instance.__class__.__name__
            if error_key is None and error_code is None:
                raise ValueError('You have to provide either error key or error code')

            if error_code is not None:
                error_code = error_code
            else:
                try:
                    error_code = settings.FRIENDLY_FIELD_ERRORS[field_type].get(error_key)
                except KeyError:
                    raise ValueError(f'Unknown field type: "{field_type}"')

                if error_code is None:
                    raise ValueError(f'Unknown error key: "{error_key}" for field type: "{field_type}"')

            error = {
                'code': error_code,
                'field': field_name,
                'message': error_message
            }
        key = f'{error_message}_{error_code}_{field_name}'
        self.registered_errors[key] = error
        raise RestValidationError(key)

    def get_field_kwargs(self, field, field_data):
        kwargs = {
            'data_type': type(field_data).__name__
        }

        if isinstance(field, self.field_map['boolean']):
            kwargs.update({'input': field_data})
        elif isinstance(field, self.field_map['string']):
            kwargs.update({
                'max_length': getattr(field, 'max_length', None),
                'min_length': getattr(field, 'min_length', None),
                'value': field_data
            })
        elif isinstance(field, self.field_map['numeric']):
            kwargs.update({
                'min_value': field.min_value,
                'max_value': field.max_value,
                'decimal_places': getattr(field, 'decimal_places', None),
                'max_decimal_places': getattr(field, 'decimal_places', None),
                'max_digits': getattr(field, 'max_digits', None)
            })

            max_digits = kwargs['max_digits']
            decimal_places = kwargs['decimal_places']
            if max_digits is not None and decimal_places is not None:
                whole_digits = max_digits - decimal_places
                kwargs.update({'max_whole_digits': whole_digits})
        elif isinstance(field, tuple(self.field_map['date'].keys())):
            kwargs.update({
                'format': self.field_map['date'][field]
            })
        elif isinstance(field, self.field_map['choice']):
            kwargs.update({
                'input': field_data,
                'input_type': type(field_data).__name__
            })
        elif isinstance(field, self.field_map['file']):
            kwargs.update({
                'max_length': field.max_length,
                'length': len(field.parent.data.get(field.source, ''))
            })
        elif isinstance(field, self.field_map['composite']):
            kwargs.update({
                'input_type': type(field_data).__name__,
                'max_length': getattr(field, 'max_length', None),
                'min_length': getattr(field, 'min_length', None)
            })
        elif isinstance(field, self.field_map['relation']):
            kwargs.update({
                'pk_value': field_data,
                'data_type': type(field_data).__name__,
                'input_type': type(field_data).__name__,
                'slug_name': getattr(field, 'slug_field', None),
                'value': field_data
            })
        else:
            kwargs.update({'max_length': getattr(field, 'max_length', None)})
        return kwargs

    def does_not_exist_many_to_many_handler(self, field, message, kwargs):
        unformatted = field.error_messages['does_not_exist']
        new_kwargs = kwargs
        for value in kwargs['value']:
            new_kwargs['value'] = value
            if unformatted.format(**new_kwargs) == message:
                return True
        return False

    def find_key(self, field, message, field_name):
        kwargs = self.get_field_kwargs(
            field,
            self.initial_data.get(field_name)
        )
        for key in field.error_messages:
            if key == 'does_not_exist' and isinstance(kwargs.get('value'), list) \
                    and self.does_not_exist_many_to_many_handler(
                        field,
                        message,
                        kwargs
                    ):
                return key
            unformatted = field.error_messages[key]
            if unformatted.format(**kwargs) == message:
                return key
        if getattr(field, 'child_relation', None):
            return self.find_key(field=field.child_relation, message=message, field_name=field_name)

    def _run_validator(self, validator, field, message):
        try:
            validator(self.initial_data[field.field_name])
        except (DjangoValidationError, RestValidationError) as err:
            err_message = err.detail[0] if hasattr(err, 'detail') else err.message
            return err_message == message

    def find_validator(self, field, message):
        for validator in field.validators:
            if self._run_validator(validator, field, message):
                return validator

    def get_field_error_entry(self, error, field):
        if error in self.registered_errors:
            return self.registered_errors[error]

        field_type_mro = [klass.__name__ for klass in type(field).__mro__]
        key = self.find_key(field, error, field.field_name)

        if key:
            # Возможно, мы обозначили в настройках ошибки для данного класса поля,
            # но для классов, наследующих это поле - нет
            # Поэтому здесь если не нашли ошибки для текущего класса, попробуем найти ошибки в классов-родителей
            for field_type in field_type_mro:
                error_codes = settings.FRIENDLY_FIELD_ERRORS.get(field_type, {})
                if error_codes:
                    return {
                        'code': error_codes.get(key),
                        'field': field.field_name,
                        'message': error
                    }

        # Here we know that error was raised by a custom field validator
        validator = self.find_validator(field, error)
        if validator:
            try:
                name = validator.__name__
            except AttributeError:
                name = validator.__class__.__name__
            code = self.FIELD_VALIDATION_ERRORS.get(name) or settings.FRIENDLY_VALIDATOR_ERRORS.get(name)
            return {
                'code': code,
                'field': field.field_name,
                'message': error
            }
        # Here we know that error was raised by custom validate method
        # in serializer
        validator = getattr(self, f'validate_{field.field_name}')
        if self._run_validator(validator, field, error):
            name = validator.__name__
            code = self.FIELD_VALIDATION_ERRORS.get(name) or settings.FRIENDLY_VALIDATOR_ERRORS.get(name)
            return {
                'code': code,
                'field': field.field_name,
                'message': error
            }

    def get_field_error_entries(self, errors, field):
        return [self.get_field_error_entry(error, field) for error in errors]

    def get_non_field_error_entry(self, error):
        if error in self.registered_errors:
            return self.registered_errors[error]

        if settings.INVALID_DATA_MESSAGE.format(data_type=type(self.initial_data).__name__) == error:
            return {
                'code': settings.FRIENDLY_NON_FIELD_ERRORS.get('invalid'),
                'field': None,
                'message': error
            }
        code = self.NON_FIELD_ERRORS.get(error.code) or settings.FRIENDLY_NON_FIELD_ERRORS.get(error.code)
        return {
            'code': code,
            'field': None,
            'message': error
        }

    def get_non_field_error_entries(self, errors):
        return [self.get_non_field_error_entry(error) for error in errors]

    def build_pretty_errors(self, errors):
        pretty = []
        for error_type in errors:
            if isinstance(errors[error_type], Mapping):
                nested_errors = self.build_pretty_errors(errors[error_type])
                pretty.append({
                    'field': error_type,
                    'code': nested_errors['code'],
                    'message': nested_errors['message'],
                    'errors': nested_errors.get('errors', [])
                })
            elif error_type == 'non_field_errors':
                # Решил отдавать ток 1 non field еррор, причем в формате 'code', 'message'
                # Т.к. все равно никогда не бывает 2ух non_field_errors, да и вообще они - редкий кейс
                error_data = self.get_non_field_error_entries(errors[error_type])[0]
                return {
                    'code': error_data.get('code', settings.VALIDATION_FAILED_CODE),
                    'message': error_data.get('message', settings.VALIDATION_FAILED_MESSAGE),
                    'errors': []
                }
            else:
                field = self.fields.get(error_type)
                # Прокидываем ошибку напрямую в случае кастомной ошибки, вызванной разработчиком напрямую, н-р,
                # raise ValidationError({'code': 228, 'message': 'kek'})
                if not field:
                    break

                pretty.extend(self.get_field_error_entries(errors[error_type], field))
        if pretty:
            return {
                'code': settings.VALIDATION_FAILED_CODE,
                'message': settings.VALIDATION_FAILED_MESSAGE,
                'errors': pretty
            }
        # Возвращаем на клиент необработанные ошибки
        return errors
