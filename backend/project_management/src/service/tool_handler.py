from abc import ABC, abstractmethod
import os
import subprocess
import yaml
from dbt.cli.main import dbtRunner


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
            'mysql': 'dbt-mysql',
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


        if self.database_type in ("postgres", "mysql"):
            db_metadata['port'] = int(db_metadata['port'])

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



            with open(keyfile_path, 'w') as f:
                f.write(db_metadata['keyfile'])

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
        self.database_type = database_type.lower()

        self.adapter_mapping = {
            'postgres': 'psycopg2-binary',
            'snowflake': 'snowflake-sqlalchemy',
            'bigquery': 'google-cloud-bigquery',
            'mysql': 'pymysql',
        }

        self.connection_type_mapping = {
            'postgres': 'postgresql',
            'mysql': 'mysql',
            'snowflake': 'snowflake',
            'bigquery': 'bigquery',
        }

    def install_dependencies(self):
        """Install SQLMesh and database-specific adapter package.

        Raises:
            ValueError: If unsupported database type is provided
            Exception: If package installation fails
        """
        try:
            # Install SQLMesh core
            subprocess.run(['pip', 'install', 'sqlmesh'], check=True)

            # Install database-specific adapter
            adapter_package = self.adapter_mapping.get(self.database_type)
            if adapter_package:
                subprocess.run(['pip', 'install', adapter_package], check=True)
            else:
                raise ValueError(f"Unsupported database type: {self.database_type}")

            # Additional common packages that might be needed
            subprocess.run(['pip', 'install', 'sqlalchemy'], check=True)

        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to install SQLMesh dependencies: {str(e)}")

    def initialize_project(self, project_name: str, project_dir: str, db_metadata: dict):
        """Initialize a SQLMesh project with proper configuration.

        Args:
            project_name: Name of the SQLMesh project
            project_dir: Directory to initialize project in
            db_metadata: Connection parameters

        Raises:
            Exception: If project initialization fails
        """
        try:

            os.chdir(project_dir)

            subprocess.run(
                ["sqlmesh", "init", "--template", "empty", self.database_type],
                check=True,
                capture_output=True,
                text=True
            )



            config = {
                'gateways': {
                    'default': {
                        'connection': self._prepare_connection_config(db_metadata),
                        'state_schema': f"{project_name}_state",
                    }
                },
                'model_defaults': {
                    'dialect': self.database_type,

                }
            }

            # Write config to sqlmesh.yaml
            config_path = os.path.join(project_dir, 'config.yaml')
            with open(config_path, 'w') as f:
                yaml.dump(config, f, sort_keys=False)

            # Create credentials file if needed
            self._handle_credentials(project_dir, db_metadata)



            return {
                "status": "success",
                "message": "SQLMesh project initialized successfully",
                "config_path": config_path
            }

        except subprocess.CalledProcessError as e:
            raise Exception(f"SQLMesh init failed: {e.stderr}")
        except Exception as e:
            raise Exception(f"Failed to initialize SQLMesh project: {str(e)}")

    def _prepare_connection_config(self, db_metadata):
        """Prepare connection configuration based on database type."""
        config = {'type': self.database_type}

        if self.database_type == "postgres":
            config.update({
                'host': db_metadata.get('host'),
                'port': int(db_metadata.get('port', 5432)),
                'user': db_metadata.get('user'),
                'password': db_metadata.get('password'),
                'database': db_metadata.get('dbname')

            })

        elif self.database_type == "snowflake":
            config.update({
                'account': db_metadata.get('account'),
                'user': db_metadata.get('user'),
                'password': db_metadata.get('password'),
                'database': db_metadata.get('database'),
                'warehouse': db_metadata.get('warehouse', 'compute_wh')


            })

        elif self.database_type == "bigquery":
            config.update({
                'project': db_metadata.get('project'),
                'keyfile': db_metadata.get('credentials', './credentials/service_account.json')
            })

        elif self.database_type == "mysql":
            config.update({
                'host': db_metadata.get('host'),
                'port': int(db_metadata.get('port', 3306)),
                'user': db_metadata.get('user'),
                'password': db_metadata.get('password'),
                'database': db_metadata.get('database')
            })

        return config

    def _handle_credentials(self, project_dir, db_metadata):
        """Handle credentials for databases that require external files."""
        if self.database_type == "bigquery":
            credentials_dir = os.path.join(project_dir, 'credentials')
            os.makedirs(credentials_dir, exist_ok=True)

            keyfile_path = os.path.join(credentials_dir, 'service_account.json')
            with open(keyfile_path, 'w') as f:

                    f.write(db_metadata['keyfile'])



    def _generate_jenkinsfile(self) -> str:
        """Generate minimal Jenkinsfile for SQLMesh CI/CD pipeline."""
        adapter_package = self.adapter_mapping.get(self.database_type, "")

        return f"""pipeline {{
    agent {{
        docker {{
                        image 'mouadh07/custom-sqlmesh:1.9'
                        args '-u root -v /var/run/docker.sock:/var/run/docker.sock --network postgres_jenkins'
                    }}
    }}

    environment {{
        PROJECT_NAME = "${{params.PROJECT_NAME}}"
        MODEL_NAME = "${{params.MODEL_NAME}}"
        RUN_ALL = "${{params.RUN_ALL}}".toBoolean()
    }}

    stages {{
       
        stage('Plan Changes') {{
            steps {{
                sh 'sqlmesh plan --auto-apply'
            }}
        }}

        stage('Apply Changes') {{
            steps {{
                script {{
                    if (env.RUN_ALL.toBoolean()) {{
                        sh 'sqlmesh run'
                    }} else {{
                        sh "sqlmesh run --select-model ${{env.MODEL_NAME}} "
                    }}
                }}
            }}
        }}

        
    }}
}}"""