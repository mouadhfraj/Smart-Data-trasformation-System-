# api/v1/auth/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    isAdmin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'isAdmin']
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': False, 'allow_blank': True}
        }

    def get_isAdmin(self, obj):
        return obj.is_staff or obj.is_superuser


