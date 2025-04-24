from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import GenerateQuerySerializer, GeneratedQueryResponseSerializer
from ..service.generation_service import QueryGenerationService
from ..service.validation_service import QueryValidationService
from ..repo.repository import GenerationRepository
import time
from datetime import datetime


@api_view(['POST'])
def generate_query(request):
    """
    API endpoint for generating SQL queries from natural language prompts.

    Args:
        request (HttpRequest): Contains:
            - user_requirements (str): Natural language prompt
            - dataset_metadata (dict): Schema/metadata about the dataset
            - llm_provider (str): Which LLM provider to use
            - project_id (int): Associated project ID

    Returns:
        Response: Contains generated query and metadata or error
    """
    serializer = GenerateQuerySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        start_time = time.time()
        data = serializer.validated_data
        repo = GenerationRepository()


        result = QueryGenerationService.generate_query(
            data['user_requirements'],
            data['dataset_metadata'],
            data['llm_provider']
        )


        generation_time_ms = int((time.time() - start_time) * 1000)


        query = repo.save_query_metadata({
            'raw_query': result['generated_query'],
            'prepared_prompt': str(result['prepared_prompt']),
            'llm_provider': data['llm_provider'],
            'generation_time_ms': generation_time_ms,
            'project_id': data['project_id']
        }, request=request)


        validation_result = QueryValidationService.validate_query(result['generated_query'])

        updated_query = repo.update_validation_status(
            query_id=query.query_id,
            is_valid=validation_result['is_valid']
        )


        result = {
            'generated_query': result['generated_query'],
            'is_valid': validation_result['is_valid'],
            'validation_errors': validation_result.get('errors', []),
            'llm_provider': data['llm_provider'],
            'generation_time': datetime.now().isoformat(),
            'status': 'success',
            'query_id': query.query_id
        }

        response_serializer = GeneratedQueryResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    except ValueError as e:
        return Response(
            {'detail': f"Database error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {'detail': f"Generation failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


