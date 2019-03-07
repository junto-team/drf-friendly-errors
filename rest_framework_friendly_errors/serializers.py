from rest_framework import serializers

from rest_framework_friendly_errors.mixins import FriendlyErrorMessagesMixin


class ModelSerializer(FriendlyErrorMessagesMixin, serializers.ModelSerializer):
    pass


class ListSerializer(FriendlyErrorMessagesMixin, serializers.ListSerializer):
    pass


class Serializer(FriendlyErrorMessagesMixin, serializers.Serializer):
    pass
