import os
import yaml
import subprocess
from dbt.cli.main import dbtRunner
from ..utils.github_utils import create_github_repository, push_to_github


class ProjectService:
    def __init__(self, project_repository):
        """Initialize ProjectService with required dependencies.

               Args:
                   project_repository: Repository instance for project persistence operations
               """
        self.project_repository = project_repository
        self.adapter_mapping = {
            'postgres': 'dbt-postgres',
            'snowflake': 'dbt-snowflake',
            'bigquery': 'dbt-bigquery',
            'redshift': 'dbt-redshift',

        }

    def setup_project(self, project_name, description, database_type, database_metadata,
                      github_token, tool, user_id):
        """Set up a complete analytics project with all required components.

                Args:
                    project_name: Name for the new project
                    description: Project description
                    database_type: Type of database (postgres, snowflake, etc.)
                    database_metadata: Connection details for the database
                    github_token: GitHub access token for repository operations
                    tool: Analytics tool to use (dbt or sqlmesh)
                    user_id: ID of the user creating the project

                Returns:
                    dict: {
                        "project_id": str,
                        "message": str,
                        "github_link": str,
                        "dependencies_installed": bool
                    }

                Raises:
                    ValueError: If unsupported tool or database type is provided
                    Exception: For any setup failures with detailed error message
                """
        try:
            project_dir = os.path.expanduser(f"C:/Users/elyadata/Documents/generated_dbt_project/{project_name}")
            os.makedirs(project_dir, exist_ok=True)

            if tool == "dbt":
                self._install_dbt_dependencies(database_type)
                self._initialize_dbt_project(project_name, project_dir, database_type, database_metadata)
            elif tool == "sqlmesh":
                self._install_sqlmesh_dependencies()
                self._initialize_sqlmesh_project(project_dir, database_metadata)
            else:
                raise ValueError(f"Unsupported tool: {tool}")

            repo = create_github_repository(
                repo_name=project_name,
                description=f"{tool} project for {project_name}",
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
                "github_link": github_link,
                "dependencies_installed": True
            }
        except Exception as e:
            raise e

    def _install_dbt_dependencies(self, database_type):
        """Install dbt core and database-specific adapter package.

        Args:
            database_type: Type of database to install adapter for

        Raises:
            ValueError: If unsupported database type is provided
            Exception: If package installation fails
        """
        try:

            subprocess.run(['pip', 'install', 'dbt-core'], check=True)


            adapter_package = self.adapter_mapping.get(database_type.lower())
            if adapter_package:
                subprocess.run(['pip', 'install', adapter_package], check=True)
            else:
                raise ValueError(f"Unsupported database type: {database_type}")

        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to install dbt dependencies: {str(e)}")

    def _install_sqlmesh_dependencies(self):
        """Install SQLMesh package and its dependencies.

        Raises:
            Exception: If installation fails
        """
        try:
            subprocess.run(['pip', 'install', 'sqlmesh'], check=True)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to install SQLMesh: {str(e)}")

    def _initialize_dbt_project(self, project_name, project_dir, database_type, database_metadata):
        """Initialize a dbt project with proper configuration.

               Args:
                   project_name: Name of the dbt project
                   project_dir: Directory to initialize project in
                   database_type: Type of database connection
                   database_metadata: Connection parameters

               Raises:
                   Exception: If project initialization fails
               """
        dev_config = {
            "type": database_type,
        }
        dev_config.update(database_metadata)

        if database_type == "bigquery":
            dev_config.setdefault("method", "service-account")
        elif database_type == "snowflake":
            dev_config.setdefault("warehouse", "compute_wh")

        profiles_config = {
            project_name: {
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
        result = dbt.invoke(cli_args)

        if not result.success:
            raise Exception(f"dbt init failed: {result.exception}")

    def delete_project(self, project_id):
        self.project_repository.delete_project(project_id)

    def _initialize_sqlmesh_project(self, project_dir, database_metadata):
        """Initialize a SQLMesh project"""
        return "sqlmesh project initialized"
