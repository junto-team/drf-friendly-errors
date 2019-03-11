DRF Friendly Errors (fork)
===================

**Extension for Django REST framework error display**

## Overview

This package extends default error JSON body providing configurable error codes
and more consumable response structure.

It turns default JSON body of HTTP 400 response, which look like this


    {
        "name": ["This field is required."],
        "password": ["This field may not be blank."]
        "age": ["This field may not be null."]
        "description": ["Ensure this field has no more than 100 characters."]
    }

into

    {
        "code" : 1000,
        "message" : "Validation Failed",
        "errors" : [
            {
                "code" : 2002,
                "field" : "name",
                "message" : "This field is required.",
                "errors": []
            },
            {
                "code" : 2031,
                "field" : "password",
                "message" : "This field may not be blank.",
                "errors": []
            },
            {
                "code" : 2023,
                "field" : "age",
                "message" : "This field may not be null.",
                "errors": []
            },
            {
                "code" : 2041,
                "field" : "description",
                "message" : "Ensure this field has no more than 100 characters.",
                "errors": []
            },
        ]
    }

Library handles all `Django REST framework` built-in serializer validation

This package is fork of [drf-friend-errors library](https://github.com/FutureMind/drf-friendly-errors)

## Main fork differences:

**- DRF 3.9+ compatibility**

**- Changed/added some code errors**

**- Support for custom field errors**

Now if you have custom field, say:

```python
class PrimaryKeyRelatedNestedField(serializers.PrimaryKeyRelatedField):
    def __init__(self, serializer_class=None, **kwargs):
        assert serializer_class, 'you should pass serializer class'
        self.serializer_class = serializer_class
        super().__init__(**kwargs)

    def to_representation(self, value):
        return self.serializer_class(value, context=self.context).data
```

You don't have to specify custom errors for this field in settings,
because, now friendly-errors would use error code of PrimaryKeyRelatedField (parent class)
as default. 

If no parent class errors found, friendly-errors would try to find error codes for parent class of parent class. 

For example:

 
 ```python
class SoCustomField(PrimaryKeyRelatedNestedField):
    pass
```

For class *SoCustomField* it would try to find error codes for PrimaryKeyRelatedNestedField, PrimaryKeyRelatedField

However, you always can specify your custom field error codes this way:

```
FRIENDLY_ERRORS = {
    FIELD_ERRORS = {
        'MyCustomFieldName': {'required': 10, 'null':11, 'blank': 12, 'max_length': 13, 'min_length': 14}
    }
}
```
  

**- Changed custom validation errors throwing flow**

(look below)

**- Added support for nested serializer and nested errors**

**- Got rid of `nested_errors: []`**

It was:
```
{
    "code" : <int>,
    "message" :  <str>,
    "errors" : [
        {
            "code" : <int>,
            "field" : null,
            "message" : <str>
        },
        ...
    ]
}
```

Has become to:
```
{
    "code" : <int>,
    "message" :  <str>,
    "errors" : []
}
```

Because it's almost impossible to have several non-field-errors at once, 
i decided to show only the one of them and to change format
to more appropriate form

**- Changed common error format (for nested field errors support)**

It was:
```
{
    "code" : <int>,
    "message" :  <str>,
    "errors" : [
        {
            "code" : <int>,
            "field" : <str>,
            "message" : <str>
        },
    ]
}
```

Has become to:
```
{
        "code" : <int>,
        "message" :  <str>,
        "errors" : [
            {
                "code" : <int>,
                "field" : <str>,
                "message" : <str>,
                "errors": [
                    {
                        "code": <int>,
                        "field": <str>,
                        "message": <str>,
                        "errors": []
                    },
                ]
            },
        ]
    }
```

Requirements
------------
-  Python (3.4+)
-  Django (1.8+)
-  Django REST framework (3.9+)

Installation
------------

By running installation script


    $ python setup.py install

Or using pip


    $ pip install git+https://github.com/junto-team/drf-friendly-errors.git
    
   (пока не успел добавить в pip)

Usage
-----

Simply add special firendly error classes:

```python
from rest_framework_friendly_errors.serializers import ModelSerializer, ListSerializer, Serializer

class MyModelSerializer(ModelSerializer):
    pass

class MySerializer(Serializer):
    pass
    
class MyListSerializer(ListSerializer):
    pass    
```

If you want to change default library settings and provide your own set of error codes just add following in your
settings.py

```python
FRIENDLY_ERRORS = {
    FIELD_ERRORS = {
        'CharField': {'required': 10, 'null':11, 'blank': 12, 'max_length': 13, 'min_length': 14}
    }
    VALIDATOR_ERRORS = {
        'UniqueValidator': 50
    },
    EXCEPTION_DICT = {
        'PermissionDenied': 100
    }
}
```

Custom serializer validation
----------------------------

If you need custom field validation or validation for whole serializer you can do it this way:

```python
class PostSerializer(ModelSerializer):
    class Meta:
        model = Post

    def validate_title(self, value):
        if value[0] != value[0].upper():
            raise ValidationError({
                "code": 228,
                "message": "First letter must be an uppercase"
            })
        """
        Result response will be:
        {
            "code": 1000,
            "message": "Validation Failed",
            "errors": [ 
                {
                    "field": "title",
                    "code": 228,
                    "message": "First letter must be an uppercase",
                    "errors": []
                }
            ]
        }
        """
        return value

    def validate(self, attrs):
        category = attrs.get('category)
        title = attrs.get('title')
        if category and category not in title:
            raise ValidationError({
                "code": 1489,
                "message": "Title has to include category"
            })
        """
        Result response will be:
        {
            "code": 1489,
            "message": "Title has to include category Failed",
            "errors": []
        }
        """
        return attrs
```
If you want to raise field error in validate method:

````python
class PostSerializer(ModelSerializer):
        class Meta:
            model = Post

        def validate(self, attrs):
            category = attrs.get('category')
            title = attrs.get('title')
            if category and category not in title:
                raise ValidationError({
                    {
                        'title': {
                            'message': 'Title has to include category',
                            'code': 8000
                        }
                    }
                })
                """
                Result response will be:
                {
                    "code": 1000,
                    "message": "Validation Failed",
                    "errors": [
                        {
                            "field": "title",
                            "code": 8000,
                            "message": "Title has to include category",
                            "errors": []
                        }
                    ]
                }
                """
            return attrs
````

Error codes not related to serializer validation
------------------------------------------------

To turn other type of errors responses (401, 403, view-level errors, etc) into friendly errors responses with error codes
add this exception handler to your REST_FRAMEWORK settings

```python
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER':  'rest_framework_friendly_errors.handlers.friendly_exception_handler'
}
```

Default error codes
-------------------

Following conventions were used:

1xxx - Are reserved for non field errors

2xxx - Are reserved for field errors

3xxx - Are reserved for validator errors

4xxx - Are reserved for other errors not related to serializer validation

Default field error codes
-------------------------

Field is required

- 2001: BooleanField, NullBooleanField
- 2002: CharField, EmailField, RegexField, SlugField, URLField, UUIDField, FilePathField, IPAddressField
- 2003: IntegerField, FloatField, DecimalField
- 2004: ChoiceField, MultipleChoiceField
- 2005: FileField, ImageField
- 2006: ListField, DictField, JSONField
- 2007: StringRequiredField, PrimaryKeyRelatedField, HyperlinkedRelatedField, SlugRelatedField, HyperlinkedIdentityField, ManyRelatedField
- 2008: ReadOnlyField, HiddenField, ModelField, SerializerMethodField
- 2009: DateTimeField, DateField, TimeField, DurationField
- 2010: Serializer

Field data is invalid (invalid regex, string instead of number, date, etc.)

- 2011: BooleanField, NullBooleanField
- 2012: EmailField, RegexField, SlugField, URLField, UUIDField, IPAddressField
- 2013: IntegerField, FloatField, DecimalField
- 2014: FileField, ImageField
- 2015: DateTimeField, DateField, TimeField, DurationField

Field data cannot be null

- 2021: BooleanField, NullBooleanField
- 2022: CharField, EmailField, RegexField, SlugField, URLField, UUIDField, FilePathField, IPAddressField
- 2023: IntegerField, FloatField, DecimalField
- 2024: ChoiceField, MultipleChoiceField
- 2025: FileField, ImageField
- 2026: ListField, DictField, JSONField
- 2027: StringRequiredField, PrimaryKeyRelatedField, HyperlinkedRelatedField, SlugRelatedField, HyperlinkedIdentityField, ManyRelatedField
- 2028: ReadOnlyField, HiddenField, ModelField, SerializerMethodField

Field data cannot be blank

- 2031: CharField, EmailField, RegexField, SlugField, URLField, UUIDField, IPAddressField

Field data is too long string

- 2041: CharField, EmailField, RegexField, SlugField, URLField, UUIDField, IPAddressField
- 2042: IntegerField, FloatField, DecimalField
- 2043: FileField, ImageField

Field data is too short string

- 2051: CharField, EmailField, RegexField, SlugField, URLField, UUIDField, IPAddressField

Field data is too big number

- 2061: IntegerField, FloatField, DecimalField

Field data is too small number

- 2071: IntegerField, FloatField, DecimalField

Field data do not match any value from available choices

- 2081: ChoiceField, MultipleChoiceField
- 2082: FilePathField
- 2083: ManyRelatedField

Field is empty

- 2091: FileField, ImageField
- 2092: MultipleChoiceField
- 2093: ManyRelatedField

File has no name

- 2101: FileField, ImageField

File is an invalid image

- 2111: ImageField

Field is not a list

- 2121: MultipleChoiceField
- 2122: ListField
- 2123: ManyRelatedField

Field is not a dict

- 2131: DictField

Field is not a json

- 2141: JSONField

Field does not exist (invalid hyperlink, primary key, etc.)

- 2151: PrimaryKeyRelatedField, HyperlinkedRelatedField, SlugRelatedField, HyperlinkedIdentityField

Incorrect type for relation key

- 2161: PrimaryKeyRelatedField, HyperlinkedRelatedField, SlugRelatedField, HyperlinkedIdentityField, ManyRelatedField

Couldn't match url or name to a view

- 2171: HyperlinkedRelatedField, HyperlinkedIdentityField

Expected a DateTime, got Date

- 2181: DateTimeField

Excpected a Date, got DateTime

- 2191: DateField

Too many digits for defined Decimal

- 2201: DecimalField

Too many whole digits for defined Decimal

- 2211: DecimalField

Too many decimal digits for defined Decimal

- 2221: DecimalField

Default built-in validators error codes
---------------------------------------

- UniqueValidator: 3001
- UniqueTogetherValidator: 3003
- UniqueForDateValidator: 3004
- UniqueForMonthValidator: 3004
- UniqueForYearValidator: 3005
- RegexValidator: 3006
- EmailValidator: 3007
- URLValidator: 3008
- MaxValueValidator: 3009
- MinValueValidator: 3010
- MaxLengthValidator: 3011
- MinLengthValidator: 3012
- DecimalValidator: 3013
- validate_email: 3014
- validate_slug: 3015
- validate_unicode_slug: 3016
- validate_ipv4_address: 3017
- validate_ipv46_address: 3018
- validate_comma_separated_integer_list: 3019
- int_list_validator: 3020

Other error codes not related to serializer validation
------------------------------------------------------
- Server Error: 4000
- Parser Error (exception was raised by Parser class): 4001,
- Authentication Failed (invalid credentials were provided): 4002,
- Not Authenticated (no credentials were provided): 4003,
- Not Found: 4004,
- Permission Denied: 4005,
- Method Not Allowed (invalid HTTP method): 4006,
- Not Acceptable (Could not satisfy the request Accept header): 4007,
- Unsupported Media-Type: 4008,
- Throttled (Too many requests): 4009


Contributors
------------
- Geoffrey Lehée <socketubs> (original library creator)
- [Alexandr Kochetov](https://github.com/alexshurik)