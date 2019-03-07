from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException

from rest_framework_friendly_errors import settings
from rest_framework_friendly_errors.utils import is_pretty, get_int_value


def get_transformed_value(value):
    if isinstance(value, list):
        # Чтобы убрать собирание ошибок в список там, где не надо
        if len(value) == 1:
            return get_transformed_value(value[0])
        return [get_transformed_value(_value) for _value in value]

    if isinstance(value, dict):
        return {
            key: get_transformed_value(value)
            for key, value in value.items()
        }

    if value == 'None':
        return None

    if isinstance(value, str) and value.isdigit():
        return get_int_value(value, value)
    return value


def transform_response_data_values(response):
    """
    Костыль, чтобы компенсировать конвертацию в str всех значений дикта ошибок

    (см. ValidationError.__init__ (158 строчка))

    Без данного преобразования невозможно передать на клиент в ошибке int или None,
    вместо этого будет str(int) и "none"

    Например:
    {
      "code": "2",
      "message": "None"
    }
    :param response:
    :return:
    """
    if not isinstance(response.data, dict):
        response.data = {
            'detail': response.data
        }

    data = {}
    for key, value in response.data.items():
        data[key] = get_transformed_value(value)
    response.data = data


def friendly_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if not response and settings.CATCH_ALL_EXCEPTIONS:
        exc = APIException(exc)
        response = exception_handler(exc, context)

    if response is not None:
        transform_response_data_values(response)

        # Стандартные ошибки из сериалайзера. Уже обработаны на уровне сериалайзера
        if is_pretty(response):
            return response

        code = settings.FRIENDLY_EXCEPTION_DICT.get(
            exc.__class__.__name__,
            settings.FRIENDLY_EXCEPTION_DICT['APIException']
        )
        # Стандартные ошибки по типу Not Authenticated, PermissionDenied и т.д.
        # Или случай, когда была передана просто строка
        detail = response.data.pop('detail', None)
        if detail:
            response.data['code'] = code
            response.data['message'] = detail
            response.data['errors'] = []
        # Случай кастомных ошибок (разработичик сам сделал raise ValidationError).
        # В этом случае ниче не преобразуем, только на всякий случай дефолтные значения поставим
        # ToDo: нужно ли это?
        response.data.setdefault('errors', [])
        response.data.setdefault('code', code)
        response.data.setdefault('message', 'Error')
    return response
