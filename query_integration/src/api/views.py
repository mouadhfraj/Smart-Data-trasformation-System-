from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import IntegrateQuerySerializer, ExecuteQuerySerializer
from ..service.integration_service import IntegrationService
from ..service.pipeline_execution_service import ExecutionService


@api_view(['POST'])
def integrate_query(request):
    serializer = IntegrateQuerySerializer(data=request.data)
    if not serializer.is_valid():
        print(f"Integrate query validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        validated_data = serializer.validated_data
        print(f"[IntegrateQuery] Validated data: {validated_data}")

        # Debug individual parts
        project_metadata = validated_data['project_metadata']
        validated_query = validated_data['validated_query']

        print(f"[IntegrateQuery] project_metadata keys: {list(project_metadata.keys())}")
        print(f"[IntegrateQuery] validated_query keys: {list(validated_query.keys())}")

        result = IntegrationService.integrate_query(
            serializer.validated_data['project_metadata'],
            serializer.validated_data['validated_query']
        )
        print(result)
        return Response(result, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def execute_query(request):
    serializer = ExecuteQuerySerializer(data=request.data)
    if not serializer.is_valid():

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:

        run_all = serializer.validated_data.get('run_all', False)
        model_name = None if run_all else serializer.validated_data['model_name']

        result = ExecutionService.execute_query(
            serializer.validated_data['project_metadata'],
            model_name,
            run_all=run_all
        )
        return Response(result)
    except ValueError as e:
        return Response({'detail': str(e)}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

