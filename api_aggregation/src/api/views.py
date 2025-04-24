from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


REQUEST_TIMEOUT = 30


def make_internal_request(method, path, data=None, headers=None):
    """Helper function to make internal API requests"""
    url = f"{settings.INTERNAL_API_BASE_URL}{path}"
    default_headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    if headers:
        default_headers.update(headers)

    try:
        response = requests.request(
            method,
            url,
            json=data,
            headers=default_headers,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed to {url}: {str(e)}")
        raise


@api_view(['POST'])
def query_auto_generate(request, project_id):
    """
    POST /api/v1/projects/<int:project_id>/queries/generate/
    Combines schema fetch and query generation
    """
    try:
        schema_path = f"/api/v1/project/{project_id}/database-schema/"
        schema_response = make_internal_request('GET', schema_path)

        if not request.data.get("user_requirements") or not request.data.get("llm_provider"):
            return Response(
                {"error": "Missing user_requirements or llm_provider"},
                status=status.HTTP_400_BAD_REQUEST
            )

        cleaned_response = dict(schema_response.json())


        cleaned_response.pop("project_id", None)
        cleaned_response.pop("status", None)

        generate_data = {
            'dataset_metadata': cleaned_response,
            'user_requirements': request.data.get('user_requirements'),
            'llm_provider': request.data.get('llm_provider'),
            'project_id': project_id
        }


        generate_path = "/api/v1/query/generate/"
        generate_response = make_internal_request('POST', generate_path, generate_data)

        return Response(generate_response.json(), status=generate_response.status_code)

    except Exception as e:
        logger.error(f"Query auto-generation failed: {str(e)}")
        return Response(
            {'error': 'Query generation failed', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(['POST'])
def query_integrate_execute(request, project_id):
    """
    POST /api/v1/projects/<int:project_id>/queries/integrate-execute/
    Combines metadata fetch, query integration, and conditional execution
    """
    try:

        metadata_path = f"/api/v1/projects/{project_id}/"
        metadata_response = make_internal_request('GET', metadata_path)


        integrate_path = "/api/v1/query/integrate/"
        integrate_data = {
            'validated_query': request.data.get('validated_query'),
            'project_metadata': metadata_response.json()
        }
        integrate_response = make_internal_request('POST', integrate_path, integrate_data)

        if not request.data.get('execution', False):
            return Response(integrate_response.json(), status=integrate_response.status_code)


        execute_path = "/api/v1/query/execute/"
        execute_data = {
            'model_name': request.data.get('validated_query').get('model_name'),
            'project_metadata': metadata_response.json()
        }
        execute_response = make_internal_request('POST', execute_path, execute_data)

        return Response(execute_response.json(), status=execute_response.status_code)

    except Exception as e:
        logger.error(f"Query integrate-execute failed: {str(e)}")
        return Response(
            {'error': 'Query integration/execution failed', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def query_auto_execute(request, project_id):
    """
    POST /api/v1/projects/<int:project_id>/queries/run
    Combines metadata retrieval and query execution
    """
    try:

        metadata_path = f"/api/v1/projects/{project_id}/"
        metadata_response = make_internal_request('GET', metadata_path)

        run_all = request.data.get('run_all', False)
        if run_all :
            execute_data = {
                'run_all': run_all,
                'project_metadata': metadata_response.json()
            }


        else :
            execute_data = {
                'model_name': request.data.get('model_name'),
                'project_metadata': metadata_response.json()
            }

        execute_path = "/api/v1/query/execute/"

        execute_response = make_internal_request('POST', execute_path, execute_data)

        return Response(execute_response.json(), status=execute_response.status_code)

    except Exception as e:
        logger.error(f"Query auto-execute failed: {str(e)}")
        return Response(
            {'error': 'Query execution failed', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )