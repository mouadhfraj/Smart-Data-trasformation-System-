import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import IntegrateQuerySerializer, ExecuteQuerySerializer
from ..service.integration_service import IntegrationService
from ..service.execution_service import ExecutionService
from ..service.github_execution_service import GitHubActionsExecutionService

@api_view(['POST'])
def integrate_query(request):
    serializer = IntegrateQuerySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = IntegrationService.integrate_query(
            serializer.validated_data['project_id'],
            serializer.validated_data['validated_query']
        )
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
            serializer.validated_data['project_id'],
            model_name,
            run_all=run_all
        )
        return Response(result)
    except ValueError as e:
        return Response({'detail': str(e)}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
def workflow_callback(request):
    try:
        payload = json.loads(request.body)
        return JsonResponse(
            GitHubActionsExecutionService.handle_webhook(payload)
        )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)