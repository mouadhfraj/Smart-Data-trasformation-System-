from rest_framework import serializers
from ..repo.models import ProjectMetadata, DatabaseConfiguration

class ProjectSetupRequestSerializer(serializers.Serializer):
    project_name = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True)
    database_type = serializers.CharField()
    database_metadata = serializers.DictField()
    github_token = serializers.CharField(required=False, allow_null=True)
    tool = serializers.ChoiceField(choices=['dbt', 'sqlmesh'])
    user_id = serializers.IntegerField()

class ProjectSetupResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    project_id = serializers.IntegerField()
    message = serializers.CharField()
    github_link = serializers.URLField(required=False, allow_null=True)

class ProjectResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectMetadata
        fields = '__all__'

class DeleteProjectResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()

class DatabaseConfigResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatabaseConfiguration
        fields = ['database_type', 'config_parameters']


class DatabaseSchemaSerializer(serializers.Serializer):
    """Serializer for database schema details response"""
    project_id = serializers.IntegerField()
    database_type = serializers.CharField()
    schema = serializers.DictField(
        child=serializers.DictField(
            child=serializers.ListField(
                child=serializers.DictField(
                    child=serializers.CharField()
                )
            )
        )
    )
    status = serializers.CharField()

class ColumnDetailSerializer(serializers.Serializer):
    """Serializer for individual column details"""
    column_name = serializers.CharField()
    data_type = serializers.CharField()

class TableSchemaSerializer(serializers.Serializer):
    """Serializer for table schema details"""
    columns = serializers.ListField(child=ColumnDetailSerializer())

class DatabaseSchemaDetailSerializer(serializers.Serializer):
    """Detailed schema serializer with nested structure"""
    schemas = serializers.DictField(
        child=serializers.DictField(
            child=TableSchemaSerializer()
        )
    )