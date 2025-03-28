from django.core.exceptions import ObjectDoesNotExist
from .models import ProjectMetadata, DatabaseConfiguration
from datetime import datetime

class ProjectRepository:
    def save_project_metadata(self, project_metadata_data):
        try:
            project_metadata = ProjectMetadata.objects.create(**project_metadata_data)
            return project_metadata.project_id
        except Exception as e:
            raise e

    def get_project_by_id(self, project_id):
        try:
            return ProjectMetadata.objects.get(pk=project_id)
        except ProjectMetadata.DoesNotExist:
            return None

    def delete_project(self, project_id):
        try:
            project = ProjectMetadata.objects.get(pk=project_id)
            project.is_active = False
            project.updated_at = datetime.utcnow()
            project.save()
        except ProjectMetadata.DoesNotExist:
            pass

    def get_database_configuration(self, database_type):
        try:
            return DatabaseConfiguration.objects.get(database_type=database_type)
        except DatabaseConfiguration.DoesNotExist:
            raise ObjectDoesNotExist(f"Configuration for database type '{database_type}' not found.")