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


    def update_project_metadata(self, project_metadata_data,project_id):
        try:
            project_metadata = ProjectMetadata.objects.get(pk=project_id)


            if 'database_type' in project_metadata_data:

                db_config = DatabaseConfiguration.objects.get(
                    database_type=project_metadata_data['database_type']
                )
                project_metadata.database_type = db_config
                del project_metadata_data['database_type']


            for field, value in project_metadata_data.items():
                if hasattr(project_metadata, field):
                    setattr(project_metadata, field, value)
                else:
                    raise ValueError(f"Invalid field '{field}' for ProjectMetadata")

            project_metadata.save()
            return project_metadata.project_id

        except ProjectMetadata.DoesNotExist:
            raise ValueError(f"Project with ID {project_id} does not exist")
        except DatabaseConfiguration.DoesNotExist:
            raise ValueError(f"Database configuration '{project_metadata_data.get('database_type')}' not found")
        except (TypeError, AttributeError) as e:
            raise ValueError(f"Invalid data provided: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to update project metadata: {str(e)}")


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


    def restore_project(self, project_id):
        try:
            project = ProjectMetadata.objects.get(pk=project_id)
            project.is_active = True
            project.updated_at = datetime.utcnow()
            project.save()
        except ProjectMetadata.DoesNotExist:
            pass
