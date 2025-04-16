import json
from abc import ABC, abstractmethod
import os
import subprocess
import yaml
from dbt.cli.main import dbtRunner
from ..utils.github_utils import push_to_github,create_github_repository


class IBaseToolHandler(ABC):
    @abstractmethod
    def install_dependencies(self):
        pass

    @abstractmethod
    def initialize_project(self, project_name: str, project_dir: str, db_metadata: dict):
        pass


class DbtHandler(IBaseToolHandler):
    def __init__(self, database_type):
        self.database_type = database_type
        self.adapter_mapping = {
            'postgres': 'dbt-postgres',
            'snowflake': 'dbt-snowflake',
            'bigquery': 'dbt-bigquery',
            'redshift': 'dbt-redshift',
        }

    def install_dependencies(self):
        """Install dbt core and database-specific adapter package.

        Raises:
            ValueError: If unsupported database type is provided
            Exception: If package installation fails
        """

        try:
            subprocess.run(['pip', 'install', 'dbt-core'], check=True)

            adapter_package = self.adapter_mapping.get(self.database_type.lower())
            if adapter_package:
                subprocess.run(['pip', 'install', adapter_package], check=True)
            else:
                raise ValueError(f"Unsupported database type: {self.database_type}")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to install dbt dependencies: {str(e)}")

    def initialize_project(self, project_name: str, project_dir: str, db_metadata: dict):
        """Initialize a dbt project with proper configuration.

               Args:
                   project_name: Name of the dbt project
                   project_dir: Directory to initialize project in
                   db_metadata: Connection parameters

               Raises:
                   Exception: If project initialization fails
               """


        os.chdir(project_dir)

        dbt = dbtRunner()
        cli_args = ["init", project_name, "--skip-profile-setup"]
        result = dbt.invoke(cli_args)

        if not result.success:
            raise Exception(f"dbt init failed: {result.exception}")


        temp_project_path = os.path.join(project_dir, project_name)
        for item in os.listdir(temp_project_path):
            src = os.path.join(temp_project_path, item)
            dst = os.path.join(project_dir, item)
            os.rename(src, dst)

        os.rmdir(temp_project_path)


        dev_config = {
            "type": self.database_type,
        }
        dev_config.update(db_metadata)

        if self.database_type == "bigquery":
            dev_config.setdefault("method", "service-account")
            dev_config["keyfile"] = "./dbt_profiles/service_account.json"
        elif self.database_type == "snowflake":
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

        if self.database_type == "bigquery":
           keyfile_path = os.path.join(profiles_dir, "service_account.json")
           keyfile_dict = db_metadata['keyfile']
           with open(keyfile_path, 'w') as f:
            f.write(json.dumps(keyfile_dict))

        os.environ["DBT_PROFILES_DIR"] = profiles_dir

    def _generate_jenkinsfile(self) -> str:
            """Generate minimal Jenkinsfile that works with existing profiles.yml"""
            adapter_package = self.adapter_mapping.get(self.database_type.lower(), "")
            return f"""pipeline {{
                agent {{
                    docker {{
                        image 'mouadh07/dbt-custom:1.9'
                        args '-u root -v /var/run/docker.sock:/var/run/docker.sock --network postgres_jenkins'
                    }}
                }}

                environment {{
                    
                     PROJECT_ID = "${{params.PROJECT_ID}}"
                     MODEL_NAME = "${{params.MODEL_NAME}}"
                     RUN_ALL = "${{params.RUN_ALL}}".toBoolean()

                    
                    DBT_PROFILES_DIR = "${{WORKSPACE}}/dbt_profiles"
                }}

                stages {{
                    stage('Setup') {{
                        steps {{
                            checkout scm
                            
                        }}
                    }}

                    stage('Run dbt') {{
                        steps {{
                            script {{
                                if (env.RUN_ALL.toBoolean()) {{
                                    sh 'dbt run'
                                }} else {{
                                    sh "dbt run --select ${{env.MODEL_NAME}}"
                                }}
                            }}
                        }}
                    }}

                    
                }}

                
            }}"""
class SQLMeshHandler(IBaseToolHandler):
    def __init__(self, database_type):
        self.database_type = database_type

    def install_dependencies(self):
        """Install SQLMesh package and its dependencies."""
        try:
            subprocess.run(['pip', 'install', 'sqlmesh'], check=True)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to install SQLMesh: {str(e)}")

    def initialize_project(self, project_name: str, project_dir: str, db_metadata: dict):
        """Initialize a SQLMesh project with proper configuration."""

        try:
            os.chdir(project_dir)
            subprocess.run(['sqlmesh', 'init'], check=True)


            config_path = os.path.join(project_dir, 'config.yml')
            with open(config_path, 'w') as f:
                yaml.dump({
                    'default_connection': self.database_type,
                    'connections': {
                        self.database_type: db_metadata
                    }
                }, f)

            return "SQLMesh project initialized successfully"
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to initialize SQLMesh project: {str(e)}")


class ProjectService:
    def __init__(self, project_repository):
        self.project_repository = project_repository

    def _get_tool_handler(self, tool: str, database_type: str) -> IBaseToolHandler:
        """Retrieve the appropriate tool handler based on the tool name.

        Args:
            tool: Name of the tool ('dbt' or 'sqlmesh')
            database_type: Type of database being used

        Returns:
            Instance of the appropriate tool handler

        Raises:
            ValueError: If unsupported tool is provided
        """
        if tool == "dbt":
            return DbtHandler(database_type)
        elif tool == "sqlmesh":
            return SQLMeshHandler(database_type)
        else:
            raise ValueError(f"Unsupported tool: {tool}")

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
            project_dir = os.path.expanduser(f"~/generated_dbt_project/{project_name}")
            os.makedirs(project_dir, exist_ok=True)


            handler = self._get_tool_handler(tool, database_type)


            handler.install_dependencies()
            handler.initialize_project(project_name, project_dir, database_metadata)

            jenkinsfile_content = handler._generate_jenkinsfile()
            jenkinsfile_path = os.path.join(project_dir, "Jenkinsfile")
            with open(jenkinsfile_path, 'w') as f:
                f.write(jenkinsfile_content)


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

    def delete_project(self, project_id):
        self.project_repository.delete_project(project_id)