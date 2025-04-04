from rest_framework import serializers
from ..repo.models import QueryIntegration

class QueryIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueryIntegration
        fields = '__all__'
        read_only_fields = ('query_id', 'created_at', 'execution_status',
                          'start_time', 'end_time')

class IntegrateQuerySerializer(serializers.Serializer):
    validated_query = serializers.JSONField()
    project_id = serializers.IntegerField()

class ExecuteQuerySerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    model_name = serializers.CharField(max_length=100)