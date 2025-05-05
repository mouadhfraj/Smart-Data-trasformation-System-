from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from ..repo.models import ProjectMetadata, DatabaseConfiguration
from ..repo.repository import ProjectRepository
from ..service.project_service import ProjectService
from .serializers import (
    ProjectSetupRequestSerializer,
    ProjectSetupResponseSerializer,
    ProjectResponseSerializer,
    DeleteProjectResponseSerializer,
    DatabaseConfigResponseSerializer
)

project_repository = ProjectRepository()
project_service = ProjectService(project_repository)


@api_view(['GET'])
def root_view(request):
    return Response({
        "message": "Welcome to the Smart Data Transformation System",
        "endpoints": {
            "admin": "/admin/",
            "api_v1": "/api/v1/",
            "list-projects": "/api/v1/<int:user_id>/projects/",
            "setup-project": "/api/v1/projects/initialize/",
            "project-detail": "/api/v1/projects/<int:project_id>/",
            "get-database-config": "/api/v1/database-configurations/<str:database_type>/",
            "get-database-schema": "/api/v1/projects/<int:project_id>/database-schema/",
            "integrate-execute-query": "/api/v1/projects/<int:project_id>/query/integrate-execute/",
            "execute-query": "/api/v1/projects/<int:project_id>/query/run/",
            "generate-query": "/api/v1/projects/<int:project_id>/query/generate/",


        }
    })


@api_view(['GET'])
def list_projects(request, user_id):
    try:
        projects = ProjectMetadata.objects.filter(user_id=user_id)
        if not projects.exists():
            return Response({'detail': 'No projects found for this user.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProjectResponseSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def setup_project(request):
    serializer = ProjectSetupRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = project_service.setup_project(
            project_name=serializer.validated_data['project_name'],
            description=serializer.validated_data['description'],
            database_type=serializer.validated_data['database_type'],
            database_metadata=serializer.validated_data['database_metadata'],
            github_token=serializer.validated_data['github_token'],
            tool=serializer.validated_data['tool'],
            user_id=serializer.validated_data['user_id']
        )


        response_serializer = ProjectSetupResponseSerializer(data={
            'status': 'success',
            'project_id': result['project_id'],
            'message': result['message'],
            'github_link': result['github_link']
        })
        response_serializer.is_valid(raise_exception=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'DELETE', 'PATCH'])
def project_detail(request, project_id):
    project = get_object_or_404(ProjectMetadata, pk=project_id)

    if request.method == 'GET':
        serializer = ProjectResponseSerializer(project)
        return Response(serializer.data)

    elif request.method == 'PATCH':


        project_repository.update_project_metadata(request.data,project_id)
        return Response({
            'status': 'success',
            'message': 'Project updated successfully'
        })


    elif request.method == 'DELETE':
        project_service.delete_project(project_id)
        serializer = DeleteProjectResponseSerializer(data={
            'status': 'success',
            'message': 'Project deleted successfully'
        })
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
def get_database_config(request, database_type):
    try:
        config = project_repository.get_database_configuration(database_type)
        serializer = DatabaseConfigResponseSerializer(config)
        return Response({
            'database_type': database_type,
            'config_parameters': serializer.data['config_parameters'],
            'status': 'success'
        })
    except DatabaseConfiguration.DoesNotExist:
        return Response(
            {'detail': f"Configuration for database type '{database_type}' not found."},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def retrieve_database_schema(request, project_id):
    """
    Retrieve database schema details for a specific project.
    """
    try:

        details = project_service.get_schema_details(project_id)

        return Response({
            'project_id': project_id,
            'database_type': details['database_type'],
            'schema': details['schema'],
            'status': 'success'
        })

    except ValueError as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {'detail': f"Database error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def restore_project(request, project_id):
        try:

            project_repository.restore_project(project_id)


            response_data = {
                'status': 'success',
                'message': 'Project restored successfully'
            }


            return Response(response_data, status=status.HTTP_200_OK)

        except ProjectMetadata.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Project not found or cannot be restored'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)