from __future__ import unicode_literals

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.fields import get_error_detail
from rest_framework.settings import api_settings


def update_field_settings(setting, user_setting):
    for field in user_setting:
        field_type = setting.get(field)
        if field_type is None:
            setting[field] = user_setting[field]
        else:
            for key in user_setting[field]:
                setting[field][key] = user_setting[field][key]
    return setting


def is_pretty(response):
    data = response.data
    return'message' in data and 'code' in data and isinstance(data, dict) and isinstance(data.get('errors'), list)


def get_int_value(value, default=None):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    else:
        return value


def as_serializer_error(exc):
    """
    Продублировал аналогичную функцию из DRF за исключением того,
    что не превращаю
    {
        "key": "value"
    }

    В
    {
        "key": ["value"]
    }
    """
    assert isinstance(exc, (ValidationError, DjangoValidationError))

    if isinstance(exc, DjangoValidationError):
        detail = get_error_detail(exc)
    else:
        detail = exc.detail

    if isinstance(detail, list):
        # Errors raised as a list are non-field errors.
        return {
            api_settings.NON_FIELD_ERRORS_KEY: detail
        }
    if isinstance(detail, str):
        # Errors raised as a string are non-field errors.
        return {
            api_settings.NON_FIELD_ERRORS_KEY: [detail]
        }
    return detail
