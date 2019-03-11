from rest_framework import serializers

from rest_framework_friendly_errors.mixins import FriendlyErrorMessagesMixin


class FEModelSerializer(FriendlyErrorMessagesMixin, serializers.ModelSerializer):
    pass


class FEListSerializer(FriendlyErrorMessagesMixin, serializers.ListSerializer):
    pass


class FESerializer(FriendlyErrorMessagesMixin, serializers.Serializer):
    pass
