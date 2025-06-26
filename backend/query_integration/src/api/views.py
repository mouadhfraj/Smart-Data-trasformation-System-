from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import IntegrateQuerySerializer, ExecuteQuerySerializer, QueryResponseSerializer
from ..service.integration_service import IntegrationService
from ..service.pipeline_execution_service import ExecutionService
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ObjectDoesNotExist
from ..repo.models import Execution , QueryIntegration


@api_view(['POST'])
def integrate_query(request):
    serializer = IntegrateQuerySerializer(data=request.data)
    if not serializer.is_valid():
        print(f"Integrate query validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        validated_data = serializer.validated_data
        print(f"[IntegrateQuery] Validated data: {validated_data}")


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



@api_view(['GET'])
def executions_details(request, user_id):
    try:
        executions = Execution.objects.filter(user_id=user_id)
        if not executions.exists():
            return Response({'detail': 'No executions found for this user.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = QueryResponseSerializer(executions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@require_http_methods(["GET"])
def get_execution(request, execution_id):
    """Get execution details by ID"""
    try:

        execution = Execution.objects.get(execution_id=execution_id)





        status_map = {
            Execution.ExecutionStatus.RUNNING: 'RUNNING',
            Execution.ExecutionStatus.COMPLETED: 'COMPLETED',
            Execution.ExecutionStatus.FAILED: 'FAILED',

        }

        status = status_map.get(execution.execution_status, 'UNKNOWN')


        response_data = {
            'id': str(execution.execution_id),
            'model_name': execution.model_name ,
            'start_time': execution.start_time.isoformat() if execution.start_time else None,
            'end_time': execution.end_time.isoformat() if execution.end_time else None,
            'status': status,
            'execution_status': status,
            'logs': execution.logs,
            'project_id': str(execution.project_id),

        }

        return JsonResponse(response_data)

    except ObjectDoesNotExist:
        return JsonResponse({'error': 'Execution not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_project_models(request, project_id):
    """Get all model names for a specific project"""
    try:

        model_names = QueryIntegration.objects.filter(
            project_id=project_id
        ).values_list(
            'adapted_query__model_name',
            flat=True
        ).distinct()


        model_names = [name for name in model_names if name is not None]

        return JsonResponse({
            'project_id': project_id,
            'model_names': list(model_names),
            'count': len(model_names)
        })

    except Exception as e:
        return JsonResponse(
            {'error': str(e)},
            status=500
        )