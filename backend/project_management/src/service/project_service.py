import os
from ..utils.github_utils import push_to_github,create_github_repository
from ..repo.models import ProjectMetadata
from .tool_handler import IBaseToolHandler, DbtHandler, SQLMeshHandler
from google.cloud import bigquery
from google.oauth2 import service_account
import json
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import snowflake.connector
import mysql.connector
from mysql.connector import Error as MySQLError


class ProjectService:
    def __init__(self, project_repository):
        self.project_repository = project_repository
        self.schema_retrievers = {
            'postgres': self._get_postgres_schema,
            'bigquery': self._get_bigquery_schema,
            'snowflake': self._get_snowflake_schema,
            'mysql': self._get_mysql_schema

        }

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


            #handler.install_dependencies()

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

    def get_schema_details(self, project_id):
        """
        Unified method to get schema details for any supported database type
        Args:
            project_id: ID of the project to get schema for

        Returns:
            Dictionary containing schema information
        """
        try:
            project = ProjectMetadata.objects.get(pk=project_id)
            db_type = project.database_type.database_type.lower()

            if db_type not in self.schema_retrievers:
                raise ValueError(f"Unsupported database type: {db_type}")


            schema_func = self.schema_retrievers[db_type]



            return {
            'database_type': db_type,
            'schema': schema_func(project.database_metadata),

        }

        except ProjectMetadata.DoesNotExist:
            raise ValueError(f"Project with ID {project_id} not found")
        except Exception as e:
            raise Exception(f"Schema retrieval failed: {str(e)}")

    def _get_postgres_schema(self, db_metadata):
        """Retrieve PostgreSQL schema details with enhanced error handling

        Args:
            db_metadata: Dictionary containing:
                - host: Database host
                - port: Database port
                - user: Username
                - password: Password
                - dbname: Database name
                - schema: Schema name (default: 'public')
                - max_sample_rows: Maximum sample rows (default: 3)

        Returns:
            Dictionary with schema information including tables, columns, and sample data
        """


        conn = None
        try:
            conn = psycopg2.connect(
                host='localhost',
                port=db_metadata.get('port', 5432),
                user=db_metadata['user'],
                password=db_metadata['password'],
                dbname=db_metadata['dbname']
            )

            schema_name = db_metadata.get('schema', 'public')
            max_sample_rows = db_metadata.get('max_sample_rows', 3)

            schema_info = {
                'database': db_metadata['dbname'],
                'schema': schema_name,
                'tables': {}
            }

            with conn.cursor() as cursor:

                cursor.execute(sql.SQL("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = %s
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """), [schema_name])

                tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                try:
                    with conn.cursor() as cursor:

                        cursor.execute(sql.SQL("""
                            SELECT 
                                column_name, 
                                data_type,
                                is_nullable,
                                column_default,
                                character_maximum_length,
                                numeric_precision,
                                numeric_scale
                            FROM information_schema.columns
                            WHERE table_schema = %s
                            AND table_name = %s
                            ORDER BY ordinal_position
                        """), [schema_name, table])

                        columns = []
                        for row in cursor.fetchall():
                            try:
                                columns.append({
                                    'name': row[0],
                                    'type': row[1],
                                    'nullable': row[2] == 'YES',
                                    'default': row[3],
                                    'max_length': row[4],
                                    'precision': row[5],
                                    'scale': row[6]
                                })
                            except IndexError as e:

                                continue


                    sample_rows = []
                    try:
                        with conn.cursor(cursor_factory=RealDictCursor) as dict_cursor:
                            dict_cursor.execute(
                                sql.SQL("SELECT * FROM {}.{} LIMIT {}")
                                .format(
                                    sql.Identifier(schema_name),
                                    sql.Identifier(table),
                                    sql.Literal(max_sample_rows)
                                )
                            )
                            sample_rows = dict_cursor.fetchall()


                            for row in sample_rows:
                                for key, value in row.items():
                                    if hasattr(value, 'isoformat'):
                                        row[key] = value.isoformat()
                                    elif isinstance(value, (bytes, memoryview)):
                                        row[key] = str(value)
                    except Exception as e:
                        sample_rows = f"Failed to retrieve sample data: {str(e)}"

                    schema_info['tables'][table] = {
                        'columns': columns,
                        'sample_rows': sample_rows
                    }

                except Exception as e:

                    schema_info['tables'][table] = {
                        'error': f"Failed to process table: {str(e)}"
                    }
                    continue

            return schema_info

        except Exception as e:
            raise Exception(f"PostgreSQL schema retrieval failed: {str(e)}")
        finally:
            if conn is not None:
                conn.close()
    def _get_bigquery_schema(self, db_metadata):
        """
        Retrieve schema details from BigQuery
        Args:
            db_metadata: Dictionary containing:
                - project (str): GCP project ID
                - dataset (str): BigQuery dataset ID
                - keyfile (str/dict): Service account JSON or path to JSON file

        Returns:
            Dictionary with schema information
        """
        try:





            credentials = None
            if 'keyfile' in db_metadata:
                keyfile = db_metadata['keyfile']
                if isinstance(keyfile, str):
                    try:
                        keyfile = json.loads(keyfile)
                    except json.JSONDecodeError:

                        credentials = service_account.Credentials.from_service_account_file(keyfile)
                    else:
                        credentials = service_account.Credentials.from_service_account_info(keyfile)


            client = bigquery.Client(
                credentials=credentials,
                project=db_metadata.get('project')
            )


            dataset = client.get_dataset(db_metadata['dataset'])
            schema_info = {
                'project': client.project,
                'dataset': dataset.dataset_id,
                'location': dataset.location,
                'tables': {}
            }


            tables = client.list_tables(dataset)
            for table in tables:
                table_ref = client.get_table(table.reference)
                columns= [
                    {
                        'name': field.name,
                        'type': field.field_type,
                        'mode': field.mode,
                        'description': field.description or ''
                    }
                    for field in table_ref.schema
                ]

                sample_rows = []
                try:
                    query_job = client.query(
                        f"SELECT * FROM `{dataset.project}.{dataset.dataset_id}.{table.table_id}` LIMIT 3"
                    )
                    results = query_job.result()

                    for row in results:
                        row_dict = {}
                        for field in table_ref.schema:
                            row_dict[field.name] = row.get(field.name)
                        sample_rows.append(row_dict)
                except Exception as e:
                    sample_rows = f"Failed to retrieve sample data: {str(e)}"

                schema_info['tables'][table.table_id] = {
                    'columns': columns,
                    'sample_rows': sample_rows,
                    'num_rows': table_ref.num_rows,
                    'created': table_ref.created.isoformat(),
                    'modified': table_ref.modified.isoformat()
                }

            return schema_info

            r

        except ImportError:
            raise Exception("Google Cloud BigQuery client not installed. Run: pip install google-cloud-bigquery")
        except Exception as e:
            raise Exception(f"BigQuery schema retrieval failed: {str(e)}")

    def _get_snowflake_schema(self, db_metadata):
        """
        Retrieve schema details from Snowflake
        Args:
            db_metadata: Dictionary containing:
                - account: Snowflake account identifier
                - user: Username
                - password: Password
                - warehouse: Warehouse name
                - database: Database name
                - schema: Schema name (defaults to 'PUBLIC')
                - role: Optional role name
        Returns:
            Dictionary with schema information
        """


        try:

            conn = snowflake.connector.connect(
                user=db_metadata['user'],
                password=db_metadata['password'],
                account=db_metadata['account'],
                warehouse=db_metadata.get('warehouse'),
                database=db_metadata['database'],
                schema=db_metadata.get('schema', 'PUBLIC')
            )

            schema_info = {
                'database': db_metadata['database'],
                'schema': db_metadata.get('schema', 'PUBLIC'),
                'tables': {}
            }


            with conn.cursor() as cur:

                cur.execute(f"""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = '{db_metadata.get('schema', 'PUBLIC')}'
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)

                tables = [row[0] for row in cur.fetchall()]


                for table in tables:
                    cur.execute(f"""
                        SELECT 
                            column_name,
                            data_type,
                            is_nullable,
                            comment
                        FROM information_schema.columns
                        WHERE table_schema = '{db_metadata.get('schema', 'PUBLIC')}'
                        AND table_name = '{table}'
                        ORDER BY ordinal_position
                    """)

                    columns = [
                        {
                            'name': row[0],
                            'type': row[1],
                            'nullable': row[2] == 'YES',
                            'description': row[3] or ''
                        }
                        for row in cur.fetchall()
                    ]

                    sample_rows = []
                    try:
                        cur.execute(f"SELECT * FROM {table} LIMIT 3")
                        column_names = [col[0] for col in cur.description]
                        rows = cur.fetchall()

                        for row in rows:
                            sample_rows.append(dict(zip(column_names, row)))
                    except Exception as e:
                        sample_rows = f"Failed to retrieve sample data: {str(e)}"

                    schema_info['tables'][table] = {
                        'columns': columns ,
                        'sample_rows': sample_rows
                    }

            return schema_info

        except Exception as e:
            raise Exception(f"Snowflake operation failed: {str(e)}")

        finally:
            if 'conn' in locals():
                conn.close()

    def _get_mysql_schema(self, db_metadata):
        import mysql.connector
        from mysql.connector import Error as MySQLError

        conn = None
        try:
            conn = mysql.connector.connect(
                host='localhost',
                port=db_metadata.get('port', 3306),
                user=db_metadata['user'],
                password=db_metadata['password'],
                database=db_metadata['database']
            )

            schema_info = {
                'database': db_metadata['database'],
                'tables': {}
            }

            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = %s
                    ORDER BY table_name
                """, [db_metadata['database']])
                tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            column_name,
                            data_type,
                            is_nullable,
                            column_comment
                        FROM information_schema.columns
                        WHERE table_schema = %s
                        AND table_name = %s
                        ORDER BY ordinal_position
                    """, [db_metadata['database'], table])

                    columns = []
                    for row in cursor.fetchall():
                        column_name, data_type, is_nullable, column_comment = row
                        columns.append({
                            'name': column_name,
                            'type': data_type,
                            'nullable': is_nullable == 'YES',
                            'description': column_comment or ''
                        })

                    sample_rows = []

                    cursor.execute(f"SELECT * FROM `{table}` LIMIT 3")
                    sample_rows = cursor.fetchall()




                    schema_info['tables'][table] = {
                        'columns': columns,
                        'sample_rows': sample_rows
                    }

            return schema_info

        except MySQLError as e:
            raise Exception(f"MySQL operation failed (code {e.errno}): {e.msg}")
        except Exception as e:
            raise Exception(f"Schema retrieval failed: Unexpected error: {str(e)}")
        finally:
            if conn and conn.is_connected():
                conn.close()
