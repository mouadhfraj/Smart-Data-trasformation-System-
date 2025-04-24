from rest_framework import serializers


class GenerateQuerySerializer(serializers.Serializer):
    user_requirements = serializers.CharField()
    dataset_metadata = serializers.JSONField()
    llm_provider = serializers.CharField()
    project_id = serializers.IntegerField()

class GeneratedQueryResponseSerializer(serializers.Serializer):
    generated_query = serializers.CharField()
    is_valid = serializers.BooleanField()
    validation_errors = serializers.ListField(
        child=serializers.CharField(),
        default=[]
    )
    llm_provider = serializers.CharField()
    generation_time = serializers.CharField()
    status = serializers.CharField()
    query_id = serializers.IntegerField()