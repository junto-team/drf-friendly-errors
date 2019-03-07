from __future__ import unicode_literals

from rest_framework import serializers


class FieldMap:
    TIME_FORMAT = 'hh:mm[:ss[.uuuuuu]]'
    DATE_FORMAT = 'YYYY[-MM[-DD]]'
    DATETIME_FORMAT = 'YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z]'
    DURATION_FORMAT = '[DD] [HH:[MM:]]ss[.uuuuuu]'

    @property
    def field_map(self):
        return {
            'boolean': (
                serializers.BooleanField,
                serializers.NullBooleanField)
            ,
            'string': (
                serializers.CharField,
                serializers.EmailField,
                serializers.RegexField,
                serializers.SlugField,
                serializers.URLField,
                serializers.UUIDField,
                serializers.FilePathField,
                serializers.IPAddressField
            ),
            'numeric': (
                serializers.IntegerField,
                serializers.FloatField,
                serializers.DecimalField
            ),
            'date': {
                serializers.DateField: self.DATE_FORMAT,
                serializers.TimeField: self.TIME_FORMAT,
                serializers.DurationField: self.DURATION_FORMAT
            },
            'choice': (
                serializers.ChoiceField,
                serializers.MultipleChoiceField
            ),
            'file': (
                serializers.FileField,
                serializers.ImageField
            ),
            'composite': (
                serializers.ListField,
                serializers.DictField,
                serializers.JSONField
            ),
            'relation': (
                serializers.StringRelatedField,
                serializers.PrimaryKeyRelatedField,
                serializers.HyperlinkedRelatedField,
                serializers.SlugRelatedField,
                serializers.HyperlinkedIdentityField,
                serializers.ManyRelatedField
            ),
            'miscellaneous': (
                serializers.ReadOnlyField,
                serializers.HiddenField,
                serializers.ModelField,
                serializers.SerializerMethodField
            ),
        }
