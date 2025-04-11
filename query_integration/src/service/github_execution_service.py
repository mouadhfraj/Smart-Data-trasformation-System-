import os
import requests
import json
import yaml
import base64
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from project_management.src.repo.models import ProjectMetadata
from ..repo.models import QueryIntegration
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class GitHubActionsExecutionService:
    """Service for executing dbt projects via GitHub Actions with complete request body handling"""

    GITHUB_API_BASE = "https://api.github.com"
    WORKFLOW_FILE = "dbt_workflow.yml"

    @staticmethod
    @csrf_exempt
    def execute_query(project_id, model_name=None, run_all=False):
        """
        Handle POST request to execute dbt via GitHub Actions

        Expected request body:
        {
            "project_id": "uuid",
            "model_name": "string" (optional),
            "run_all": boolean (optional)
        }
        """
        try:


            if not project_id:
                return JsonResponse({'error': 'project_id is required'}, status=400)

            if not run_all and not model_name:
                return JsonResponse({'error': 'Either model_name or run_all must be specified'}, status=400)

            project = ProjectMetadata.objects.get(pk=project_id)
            repo_path = urlparse(project.github_link).path.strip('/')

            # Mark queries as running
            if run_all:
                queries = QueryIntegration.objects.filter(project=project)
                if not queries.exists():
                    return JsonResponse({'error': f'No queries found for project {project.project_name}'}, status=400)
                queries.update(
                    execution_status=QueryIntegration.ExecutionStatus.RUNNING,
                    start_time=timezone.now()
                )
                query = queries.first()
            else:
                query = QueryIntegration.objects.filter(
                    project=project,
                    adapted_query__model_name=model_name
                ).first()
                if not query:
                    return JsonResponse({'error': f'No query found for model {model_name}'}, status=404)
                query.execution_status = QueryIntegration.ExecutionStatus.RUNNING
                query.start_time = timezone.now()
                query.save()

            # Generate workflow content
            workflow_content = GitHubActionsExecutionService._generate_workflow_yml(
                project, model_name, run_all
            )

            # Push workflow file to repository
            workflow_created = GitHubActionsExecutionService._manage_workflow_file(
                repo_path, project.github_token, workflow_content
            )

            # Trigger workflow run
            workflow_run = GitHubActionsExecutionService._trigger_workflow(
                repo_path, project.github_token, body
            )

            # Store workflow reference
            project.github_workflow_id = workflow_run.get('id')
            project.save()

            return JsonResponse({
                'status': 'triggered',
                'workflow_id': workflow_run.get('id'),
                'workflow_url': workflow_run.get('html_url'),
                'execution_id': str(query.query_id),
                'affected_queries': queries.count() if run_all else 1
            })

        except ObjectDoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)
        except Exception as e:
            logger.error(f"GitHub Actions execution failed: {str(e)}", exc_info=True)
            if 'query' in locals():
                query.execution_status = QueryIntegration.ExecutionStatus.FAILED
                query.end_time = timezone.now()
                query.save()
            return JsonResponse({'error': f"Execution failed: {str(e)}"}, status=500)

    @staticmethod
    def _generate_workflow_yml(project, model_name=None, run_all=False):
        """Generate GitHub Actions workflow YAML with dynamic inputs"""
        workflow = {
            'name': f"DBT Execution: {'all models' if run_all else model_name}",
            'on': {
                'workflow_dispatch': {
                    'inputs': {
                        'project_id': {
                            'description': 'Project ID from Django',
                            'required': True,
                            'default': str(project.id)
                        },
                        'model_name': {
                            'description': 'Specific model to run',
                            'required': not run_all,
                            'default': model_name if not run_all else ''
                        },
                        'run_all': {
                            'description': 'Run all models flag',
                            'type': 'boolean',
                            'required': False,
                            'default': str(run_all).lower()
                        }
                    }
                }
            },
            'env': {
                'DBT_PROFILES_DIR': './',
                'DBT_PROJECT_NAME': project.project_name,
                'DBT_TARGET': 'dev',
                'DJANGO_API_URL': os.getenv('DJANGO_API_URL', 'https://your-api.com'),
                'PROJECT_ID': str(project.id)
            },
            'jobs': {
                'run-dbt': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [
                        {
                            'name': 'Checkout repository',
                            'uses': 'actions/checkout@v3'
                        },
                        {
                            'name': 'Set up Python',
                            'uses': 'actions/setup-python@v4',
                            'with': {
                                'python-version': '3.10'
                            }
                        },
                        {
                            'name': 'Install dbt',
                            'run': f"pip install dbt-core dbt-{project.database_type}"
                        },
                        {
                            'name': 'Configure profiles',
                            'run': GitHubActionsExecutionService._generate_profiles_script(project)
                        },
                        {
                            'name': 'Run dbt',
                            'run': f"dbt {'run' if run_all else f'run --select {model_name}'}",
                            'env': {
                                'GITHUB_TOKEN': '${{ secrets.GITHUB_TOKEN }}'
                            }
                        },
                        {
                            'name': 'Notify completion',
                            'run': f"""
                            curl -X POST "$DJANGO_API_URL/api/workflow/callback" \\
                                -H "Authorization: Token ${{ secrets.DJANGO_API_TOKEN }}" \\
                                -H "Content-Type: application/json" \\
                                -d '{{"project_id": "$PROJECT_ID", "status": "${{ job.status }}", "conclusion": "${{ job.conclusion }}"}}'
                            """
                        }
                    ]
                }
            }
        }
        return yaml.dump(workflow, sort_keys=False)

    @staticmethod
    def _manage_workflow_file(repo_path, token, content):
        """Create or update workflow file in repository"""
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }

        url = f"{GitHubActionsExecutionService.GITHUB_API_BASE}/repos/{repo_path}/contents/.github/workflows/{GitHubActionsExecutionService.WORKFLOW_FILE}"

        # Check if file exists
        response = requests.get(url, headers=headers)

        data = {
            "message": "Configure dbt workflow",
            "content": base64.b64encode(content.encode()).decode(),
            "branch": "main"
        }

        if response.status_code == 200:
            data["sha"] = response.json()["sha"]
            method = "PUT"
        else:
            method = "PUT"

        response = requests.request(method, url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _trigger_workflow(repo_path, token, body):
        """Trigger workflow dispatch with input parameters"""
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }

        url = f"{GitHubActionsExecutionService.GITHUB_API_BASE}/repos/{repo_path}/actions/workflows/{GitHubActionsExecutionService.WORKFLOW_FILE}/dispatches"

        inputs = {
            "project_id": str(body['project_id']),
            "run_all": body.get('run_all', False)
        }
        if 'model_name' in body:
            inputs['model_name'] = body['model_name']

        data = {
            "ref": "main",
            "inputs": inputs
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()

        # Get the workflow run ID
        runs_url = f"{GitHubActionsExecutionService.GITHUB_API_BASE}/repos/{repo_path}/actions/runs?event=workflow_dispatch"
        response = requests.get(runs_url, headers=headers)
        response.raise_for_status()

        workflow_runs = response.json()['workflow_runs']
        if workflow_runs:
            return workflow_runs[0]
        return {}

    @staticmethod
    @csrf_exempt
    def workflow_callback(request):
        """Handle GitHub Actions webhook callback"""
        try:
            body = json.loads(request.body)
            project_id = body.get('project_id')
            status = body.get('status')
            conclusion = body.get('conclusion')

            if not all([project_id, status, conclusion]):
                return JsonResponse({'error': 'Missing required fields'}, status=400)

            project = ProjectMetadata.objects.get(pk=project_id)
            queries = QueryIntegration.objects.filter(project=project)

            if status == 'completed':
                execution_status = (
                    QueryIntegration.ExecutionStatus.COMPLETED
                    if conclusion == 'success'
                    else QueryIntegration.ExecutionStatus.FAILED
                )

                queries.update(
                    execution_status=execution_status,
                    end_time=timezone.now()
                )

                return JsonResponse({
                    'status': 'updated',
                    'project_id': project_id,
                    'workflow_status': conclusion
                })

            return JsonResponse({'status': 'pending'})

        except ObjectDoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Callback failed: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)