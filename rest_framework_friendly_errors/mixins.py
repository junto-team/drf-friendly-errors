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

    def find_key(self, field, error, field_name):
        if getattr(error, 'code', None):
            return error.code

        if getattr(field, 'child_relation', None):
            return self.find_key(field=field.child_relation, error=error, field_name=field_name)

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
        field_type_mro = [klass.__name__ for klass in type(field).__mro__]
        key = self.find_key(field, error, field.field_name)

        if key:
            # Возможно, мы обозначили в настройках ошибки для данного класса поля,
            # но для классов, наследующих это поле - нет
            # Поэтому здесь если не нашли ошибки для текущего класса, попробуем найти ошибки в классов-родителей
            for field_type in field_type_mro:
                error_codes = settings.FRIENDLY_FIELD_ERRORS.get(field_type)
                if error_codes:
                    return {
                        'code': error_codes.get(key),
                        'field': field.field_name,
                        'message': error,
                        'errors': [],
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
                'message': error,
                'errors': [],
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
                'message': error,
                'errors': [],
            }

    def get_field_error_entries(self, errors, field):
        return [self.get_field_error_entry(error, field) for error in errors]

    def get_non_field_error_entry(self, error):
        if settings.INVALID_DATA_MESSAGE.format(data_type=type(self.initial_data).__name__) == error:
            return {
                'code': settings.FRIENDLY_NON_FIELD_ERRORS.get('invalid'),
                'field': None,
                'message': error,
                'errors': [],
            }
        code = self.NON_FIELD_ERRORS.get(error.code) or settings.FRIENDLY_NON_FIELD_ERRORS.get(error.code)
        return {
            'code': code,
            'field': None,
            'message': error,
            'errors': [],
        }

    def get_non_field_error_entries(self, errors):
        return [self.get_non_field_error_entry(error) for error in errors]

    def build_pretty_errors(self, errors, fields=None):
        if not fields:
            fields = self.fields

        pretty = []
        for error_type in errors:
            if isinstance(errors[error_type], Mapping):
                if hasattr(self.fields[error_type], 'fields'):
                    fields = self.fields[error_type].fields
                # Случай вложенных ошибок. Рекурсивно получаем вложенные ошибки
                nested_errors = self.build_pretty_errors(errors[error_type], fields=fields)
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
                field = fields.get(error_type)
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
