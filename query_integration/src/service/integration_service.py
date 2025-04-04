import os
import tempfile
from .adaptation_service import QueryAdapter
from git import Repo
from project_management.src.repo.models import ProjectMetadata
from ..repo.models import QueryIntegration
from django.core.exceptions import ObjectDoesNotExist


class IntegrationService:
    @staticmethod
    def integrate_query(project_id, validated_query):
        """
        Integrate a SQL query into project repository and create a QueryIntegration record.

        Args:
            project_id: PK of the ProjectMetadata
            validated_query: {
                'query': SQL string,
                'model_name': model filename,
                'materialization': type (for dbt)
            }

        Returns:
            {'status': 'success', 'query_id'} on success

        Raises:
            ValueError: If project not found
            Exception: On integration failure (with error details)
        """
        try:
            project = ProjectMetadata.objects.get(pk=project_id)
            project_name = project.project_name

            with tempfile.TemporaryDirectory() as temp_dir:

                repo = Repo.clone_from(
                    project.github_link,
                    temp_dir,
                    branch='main',
                    env={'GIT_ASKPASS': 'echo', 'GIT_USERNAME': 'token',
                         'GIT_PASSWORD': project.github_token}
                )

                project_path = os.path.join(temp_dir, project_name)


                query_with_refs = QueryAdapter.adapt_references(
                    query=validated_query['query'],
                    project_dir=project_path
                )


                full_content = ""
                if project.tool == 'dbt':
                    full_content = (
                        f"{{{{ config(\n"
                        f"    materialized='{validated_query.get('materialization', 'view')}',\n"
                        f"    schema='{validated_query.get('schema', 'public')}'\n"
                        f") }}}}\n"
                        f"{query_with_refs}"
                    )
                else:
                    full_content = query_with_refs


                query = QueryIntegration.objects.create(
                    original_query=validated_query['query'],
                    adapted_query={
                        **validated_query,
                        'final_query': full_content
                    },
                    target_tool=project.tool,
                    project=project
                )


                model_path = os.path.join(
                    project_path,
                    'models',
                    f"{validated_query['model_name']}.sql"
                )
                os.makedirs(os.path.dirname(model_path), exist_ok=True)

                with open(model_path, 'w') as f:
                    f.write(full_content)


                repo.git.add(A=True)
                repo.git.commit(m=f"Add model {validated_query['model_name']}")
                repo.git.push('origin', 'main')

            return {
                'status': 'success',
                'query_id': str(query.query_id),
                'model_content': full_content
            }

        except ObjectDoesNotExist:
            raise ValueError("Project not found")
        except Exception as e:
            if 'query' in locals():
                query.delete()
            raise Exception(f"Integration failed: {str(e)}")