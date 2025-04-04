import os
from django.utils import timezone
from git import Repo
from dbt.cli.main import dbtRunner
from project_management.src.repo.models import ProjectMetadata
from ..repo.models import QueryIntegration
from django.core.exceptions import ObjectDoesNotExist

class ExecutionService:
    @staticmethod
    def execute_query(project_id, model_name):
        """
                Execute a specific model from a project and track execution status.

                Args:
                    project_id: PK of the ProjectMetadata
                    model_name: Name of the model to execute

                Returns:
                    {
                        'status': 'completed',
                        'execution_id': PK,
                        'details': execution_results
                    }

                Raises:
                    ValueError: If project or model not found
                    Exception: On execution failure with error details
                """
        try:
            project = ProjectMetadata.objects.get(pk=project_id)
            query = QueryIntegration.objects.filter(
                project=project,
                adapted_query__model_name=model_name
            ).order_by('-created_at').first()

            if not query:
                raise ValueError(f'No query found for model {model_name}')

            query.execution_status = QueryIntegration.ExecutionStatus.RUNNING
            query.start_time = timezone.now()
            query.save()

            dir = os.path.expanduser(f"C:/Users/elyadata/Documents/executed_dbt_project/{project.project_name}")
            os.makedirs(dir, exist_ok=True)
            temp_dir = os.path.join(dir, f"{project.project_name}")

            try:
                repo = Repo.clone_from(
                    project.github_link,
                    dir,
                    branch='main',
                    env={'GIT_ASKPASS': 'echo', 'GIT_USERNAME': 'token',
                         'GIT_PASSWORD': project.github_token}
                )

                if project.tool == 'dbt':
                    result = ExecutionService._execute_dbt(dir, temp_dir, model_name)
                elif project.tool == 'sqlmesh':
                    result = ExecutionService._execute_sqlmesh(temp_dir, model_name)
                else:
                    raise ValueError(f"Unsupported tool: {project.tool}")

                query.execution_status = QueryIntegration.ExecutionStatus.COMPLETED
                query.end_time = timezone.now()
                query.save()

                return {
                    'status': 'completed',
                    'execution_id': str(query.query_id),
                    'details': result
                }

            except Exception as e:
                query.execution_status = QueryIntegration.ExecutionStatus.FAILED
                query.end_time = timezone.now()
                query.save()
                raise e

        except ObjectDoesNotExist:
            raise ValueError("Project not found")
        except Exception as e:
            raise Exception(f"Execution failed: {str(e)}")

    @staticmethod
    def _execute_dbt(dir, project_dir, model_name):
        """
        Execute a dbt model run.

        Args:
            dir: Base directory containing dbt project
            project_dir: Specific project directory
            model_name: Model to execute

        Returns:
            {
                'success': bool,
                'logs': execution_logs,
                'affected_models': [model_names]
            }

        Raises:
            Exception: If dbt execution fails
        """
        os.chdir(dir)
        os.environ["DBT_PROFILES_DIR"] = os.path.join(dir, "dbt_profiles")

        os.chdir(project_dir)
        dbt = dbtRunner()
        result = dbt.invoke(["run", "--select", model_name])

        if not result.success:
            raise Exception(f"dbt execution failed: {result.exception}")

        return {
            'success': True,
            'logs': result.result.to_dict(),
            'affected_models': [model_name]
        }

    @staticmethod
    def _execute_sqlmesh(project_dir, model_name):
        """Execute SQLMesh run for specific model"""
        return "sqlmesh"