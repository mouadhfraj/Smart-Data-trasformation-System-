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