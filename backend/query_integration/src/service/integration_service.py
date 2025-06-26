
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any
from git import Repo, GitCommandError
from django.core.exceptions import ObjectDoesNotExist
from .adaptation_service import QueryAdapter
from ..repo.models import QueryIntegration

logger = logging.getLogger(__name__)


class IntegrationService:
    @staticmethod
    def generate_model_content(tool: str,schema:str, query: str,model_name: str, materialization: str = 'view') -> str:
        """
        Generate complete model content based on target tool.

        Args:
            tool: Target tool ('dbt' or 'sqlmesh')
            query: Adapted SQL query
            materialization: Model materialization type

        Returns:
            Complete model content as string
        """
        if tool == 'dbt':
            return (
                "{{\n"
                f"  config(\n"
                f"    materialized='{materialization}'\n"
                "  )\n"
                "}}\n"
                f"{query}"
            )
        elif tool == 'sqlmesh':
            if schema=='':
                full_name=model_name
            else:
                full_name = f"{schema}.{model_name}"
            return (
                "MODEL (\n"
                f"  name {full_name},\n"
                f"  kind {materialization.upper()},\n"
                ");\n\n"
                f"{query}"
            )
        return query

    @staticmethod
    def integrate_query(project_metadata: Dict[str, Any], validated_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Integrate a SQL query into project repository and create a QueryIntegration record.

        Args:
            project_metadata: {
                'project_name': str,
                'github_link': str,
                'github_token': str,
                'tool': str ('dbt' or 'sqlmesh'),
                'project_id': str,
                'user_id': str
            }
            validated_query: {
                'query': str (SQL string),
                'model_name': str,
                'materialization': str (optional)
            }

        Returns:
            {
                'status': 'success',
                'query_id': str,
                'model_content': str,
                'model_path': str
            }

        Raises:
            ValueError: For invalid inputs or project not found
            Exception: For integration failures with detailed error
        """
        try:

            if not all(k in project_metadata for k in ['github_link', 'tool', 'project_id']):
                raise ValueError("Missing required project metadata")

            if not all(k in validated_query for k in ['query', 'model_name']):
                raise ValueError("Missing required query data")

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                try:
                    # Clone repository
                    repo = Repo.clone_from(
                        url=project_metadata['github_link'],
                        to_path=temp_path,
                        branch='main',
                        env={
                            'GIT_ASKPASS': 'echo',
                            'GIT_USERNAME': 'token',
                            'GIT_PASSWORD': project_metadata.get('github_token', '')
                        }
                    )
                except GitCommandError as e:
                    raise Exception(f"Failed to clone repository: {str(e)}")

                if project_metadata['tool'] == 'dbt':
                    query_with_refs = QueryAdapter.adapt_references(
                      query=validated_query['query'],
                      project_dir=temp_path
                   )
                else:
                    query_with_refs=QueryAdapter.adapt_sqlmesh_references(
                    query=validated_query['query'],
                    schema=project_metadata['database_metadata'].get('schema', ''))


                full_content = IntegrationService.generate_model_content(
                    tool=project_metadata['tool'],
                    schema= project_metadata['database_metadata'].get('schema', ''),
                    model_name=validated_query['model_name'],
                    query=query_with_refs,
                    materialization=validated_query.get('materialization', 'view')
                )


                query = QueryIntegration.objects.create(
                    original_query=validated_query['query'],
                    adapted_query={
                        'final_query': full_content,
                        **validated_query
                    },
                    target_tool=project_metadata['tool'],
                    project_id=project_metadata['project_id'],
                    user_id=project_metadata.get('user_id')
                )

                # Write model file
                model_path = temp_path / 'models' / f"{validated_query['model_name']}.sql"
                model_path.parent.mkdir(parents=True, exist_ok=True)

                with open(model_path, 'w') as f:
                    f.write(full_content)


                try:
                    repo.git.add(A=True)
                    repo.git.commit(m=f"Add model {validated_query['model_name']}")
                    repo.git.push('origin', 'main')
                except GitCommandError as e:
                    logger.error(f"Git operation failed: {str(e)}")
                    raise Exception(f"Failed to commit changes: {str(e)}")

                return {
                    'status': 'success',
                    'query_id': str(query.query_id),
                    'model_content': full_content,
                    'model_path': str(model_path.relative_to(temp_path))
                }

        except ObjectDoesNotExist:
            raise ValueError("Project not found in database")
        except Exception as e:
            logger.exception("Integration failed")
            if 'query' in locals():
                query.delete()
            raise Exception(f"Integration failed: {str(e)}")