import os
import yaml
from dbt.cli.main import dbtRunner
from ..utils.github_utils import create_github_repository, push_to_github


class ProjectService:
    def __init__(self, project_repository):
        self.project_repository = project_repository

    def setup_project(self, project_name, description, database_type, database_metadata,
                      github_token, tool, user_id):
        try:
            project_dir = os.path.expanduser(f"C:/Users/elyadata/Documents/generated_dbt_project/{project_name}")
            os.makedirs(project_dir, exist_ok=True)

            if tool == "dbt":
                self._initialize_dbt_project(project_name, project_dir, database_type, database_metadata)
            elif tool == "sqlmesh":
                self._initialize_sqlmesh_project(project_dir, database_metadata)
            else:
                raise ValueError(f"Unsupported tool: {tool}")

            repo = create_github_repository(
                repo_name=project_name,
                description=f"dbt project for {project_name}",
                private=True,
                github_token=github_token
            )

            push_to_github(project_dir, repo.clone_url, github_token=github_token)
            github_link = repo.html_url




            project_metadata_data = {
                'project_name': project_name,
                'description': description,
                'database_type_id': database_type,
                'database_metadata': database_metadata,
                'github_link': github_link,
                'github_token': github_token,
                'tool': tool,
                'user_id': user_id,
                'is_active': True
            }

            project_id = self.project_repository.save_project_metadata(project_metadata_data)

            return {
                "project_id": project_id,
                "message": f"Project '{project_name}' setup completed for {tool}.",
                "github_link": github_link
            }
        except Exception as e:
            raise e

    def _initialize_dbt_project(self, project_name, project_dir, database_type, database_metadata):
        dev_config = {
            "type": database_type,
            "schema": database_metadata.pop("schema", "public")
        }
        dev_config.update(database_metadata)

        if database_type == "bigquery":
            dev_config.setdefault("method", "service-account")
        elif database_type == "snowflake":
            dev_config.setdefault("warehouse", "compute_wh")

        profiles_config = {
            "default": {
                "outputs": {
                    "dev": dev_config
                },
                "target": "dev"
            }
        }

        profiles_dir = os.path.join(project_dir, "dbt_profiles")
        os.makedirs(profiles_dir, exist_ok=True)
        profiles_path = os.path.join(profiles_dir, "profiles.yml")

        with open(profiles_path, "w") as f:
            yaml.dump(profiles_config, f)

        os.environ["DBT_PROFILES_DIR"] = profiles_dir
        os.chdir(project_dir)

        dbt = dbtRunner()
        cli_args = ["init", project_name, "--skip-profile-setup"]
        dbt.invoke(cli_args)

    def delete_project(self, project_id):
        self.project_repository.delete_project(project_id)

    def _initialize_sqlmesh_project(self, project_dir, database_metadata):
        return "sqlmesh"