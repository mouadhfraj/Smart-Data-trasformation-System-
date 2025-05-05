from rest_framework import serializers
from ..repo.models import QueryIntegration , Execution

class QueryIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueryIntegration
        fields = '__all__'
        read_only_fields = ('query_id', 'created_at', 'execution_status',
                          'start_time', 'end_time')

class IntegrateQuerySerializer(serializers.Serializer):
    validated_query = serializers.JSONField()
    project_metadata = serializers.JSONField()


class ExecuteQuerySerializer(serializers.Serializer):
    project_metadata = serializers.JSONField()

    model_name = serializers.CharField(max_length=100, required=False, allow_null=True)
    run_all = serializers.BooleanField(default=False, required=False)

    def validate(self, data):
        """
        Validate that either model_name is provided or run_all is True,
        but not both at the same time.
        """
        model_name = data.get('model_name')
        run_all = data.get('run_all', False)

        if not run_all and not model_name:
            raise serializers.ValidationError(
            )

        if run_all and model_name:
            raise serializers.ValidationError(
            )

        return data


class QueryResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Execution
        fields = '__all__'