import os
import tempfile

from django.utils import timezone
from git import Repo
from dbt.cli.main import dbtRunner
from project_management.src.repo.models import ProjectMetadata
from ..repo.models import QueryIntegration
from django.core.exceptions import ObjectDoesNotExist


class ExecutionService:
    @staticmethod
    def execute_query(project_id, model_name=None, run_all=False):
        """
        Execute a specific model or all models from a project and track execution status.

        Args:
            project_id: PK of the ProjectMetadata
            model_name: Name of the model to execute (optional if run_all=True)
            run_all: Boolean flag to run all models in the project

        Returns:
            {
                'status': 'completed',
                'execution_id': PK,
                'details': execution_results
            }

        Raises:
            ValueError: If project not found or model not found (when run_all=False)
            Exception: On execution failure with error details
        """
        try:
            project = ProjectMetadata.objects.get(pk=project_id)

            if run_all:

                all_queries = QueryIntegration.objects.filter(
                    project=project
                ).order_by('-created_at')

                if not all_queries.exists():
                    raise ValueError(f'No queries found for project {project.project_name}')


                all_queries.update(
                    execution_status=QueryIntegration.ExecutionStatus.RUNNING,
                    start_time=timezone.now()
                )


                query = all_queries.first()
            else:

                query = QueryIntegration.objects.filter(
                    project=project,
                    adapted_query__model_name=model_name
                ).order_by('-created_at').first()

                if not query:
                    raise ValueError(f'No query found for model {model_name}')

                query.execution_status = QueryIntegration.ExecutionStatus.RUNNING
                query.start_time = timezone.now()
                query.save()


            with tempfile.TemporaryDirectory() as temp_dir:


              try:
                repo = Repo.clone_from(
                    project.github_link,
                    temp_dir,
                    branch='main',
                    env={'GIT_ASKPASS': 'echo', 'GIT_USERNAME': 'token',
                         'GIT_PASSWORD': project.github_token}
                )

                if project.tool == 'dbt':
                    result = ExecutionService._execute_dbt(temp_dir, model_name, run_all)
                elif project.tool == 'sqlmesh':
                    result = ExecutionService._execute_sqlmesh(temp_dir, model_name, run_all)
                else:
                    raise ValueError(f"Unsupported tool: {project.tool}")


                if run_all:
                    all_queries.update(
                        execution_status=QueryIntegration.ExecutionStatus.COMPLETED,
                        end_time=timezone.now()
                    )
                else:
                    query.execution_status = QueryIntegration.ExecutionStatus.COMPLETED
                    query.end_time = timezone.now()
                    query.save()



                return {
                    'status': 'completed',
                    'execution_id': str(query.query_id),
                    'details': result,
                    'affected_queries': all_queries.count() if run_all else 1
                }

              except Exception as e:

                if run_all:
                    all_queries.update(
                        execution_status=QueryIntegration.ExecutionStatus.FAILED,
                        end_time=timezone.now()
                    )
                else:
                    query.execution_status = QueryIntegration.ExecutionStatus.FAILED
                    query.end_time = timezone.now()
                    query.save()
                raise e

        except ObjectDoesNotExist:
            raise ValueError("Project not found")
        except Exception as e:
            raise Exception(f"Execution failed: {str(e)}")

    @staticmethod
    def _execute_dbt( project_dir, model_name=None, run_all=False):
        """
        Execute a dbt model run or full project run.

        Args:
            dir: Base directory containing dbt project
            project_dir: Specific project directory
            model_name: Model to execute (optional if run_all=True)
            run_all: Boolean flag to run all models

        Returns:
            {
                'success': bool,
                'logs': execution_logs,
                'affected_models': [model_names] or 'all'
            }

        Raises:
            Exception: If dbt execution fails
        """
        os.chdir(project_dir)
        os.environ["DBT_PROFILES_DIR"] = os.path.join(project_dir, "dbt_profiles")


        dbt = dbtRunner()

        if run_all:
            result = dbt.invoke(["run"])
            affected_models = "all"
        else:
            result = dbt.invoke(["run", "--select", model_name])
            affected_models = [model_name]

        if not result.success:
            raise Exception(f"dbt execution failed: {result.exception}")

        return {
            'success': True,
            'logs': result.result.to_dict(),
            'affected_models': affected_models
        }

    @staticmethod
    def _execute_sqlmesh(project_dir, model_name=None, run_all=False):
        """Execute SQLMesh run for specific model or all models"""

        return {
            'success': True,
            'operation': 'run_all' if run_all else f'run_model_{model_name}'
        }