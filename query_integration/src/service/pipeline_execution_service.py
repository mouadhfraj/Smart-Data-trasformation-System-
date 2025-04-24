import time
import requests
import logging
from threading import Thread
from django.core.mail import send_mail
from requests.auth import HTTPBasicAuth
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from ..repo.models import JenkinsConfig, QueryIntegration

logger = logging.getLogger(__name__)


class JenkinsService:
    """Encapsulates all Jenkins operations with proper error handling"""

    @staticmethod
    def _make_jenkins_request(url, method='get', auth=None, data=None, params=None, headers=None, timeout=60):
        """Generic Jenkins API request handler"""
        try:
            response = requests.request(
                method,
                url,
                auth=auth,
                data=data,
                params=params,
                headers=headers or {'Content-Type': 'application/xml'},
                timeout=timeout
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Jenkins API request failed to {url}: {str(e)}")
            raise Exception(f"Jenkins operation failed: {str(e)}")

    @staticmethod
    def create_jenkins_credentials(jenkins_url, jenkins_user, jenkins_token, project):
        """
        Creates a secret text credential in Jenkins for GitHub token without using a username.

        Args:
            jenkins_url (str): Base Jenkins URL (e.g., http://localhost:8080)
            jenkins_user (str): Jenkins username
            jenkins_token (str): Jenkins API token or password
            credential_id (str): Unique ID for the credential in Jenkins
            github_token (str): The GitHub personal access token (PAT)
            description (str): Optional description
        """
        credentials_url = f"{jenkins_url}/credentials/store/system/domain/_/createCredentials"
        headers = {"Content-Type": "application/xml"}


        github_token = project['github_token']
        github_username = project['github_link'].split("github.com/")[1].split("/")[0]


        credentials_xml = f"""
        <com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl>
          <scope>GLOBAL</scope>
          <id>{project['project_name']}</id>
          <description>GitHub token for {project['project_name']}</description>
          <username>{github_username}</username>
          <password>{github_token}</password>
        </com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl>
        """

        response = requests.post(
            credentials_url,
            headers=headers,
            data=credentials_xml,
            auth=(jenkins_user, jenkins_token)
        )

        if response.status_code != 200:
            raise Exception(f"Failed to create credentials. Status: {response.status_code}")


    @classmethod
    def create_job(cls, jenkins_url, project, username, api_token, model_name=None, run_all=False):
        """Create a new Jenkins job from repository Jenkinsfile"""
        try:
            JenkinsService.create_jenkins_credentials(jenkins_url,username,api_token,project)


            config_xml = f"""<?xml version='1.1' encoding='UTF-8'?>
            <flow-definition plugin="workflow-job@1251.vd262f96922b_4">
              <actions/>
              <description>{project['project_name']} pipeline using Git SCM</description>
              <keepDependencies>false</keepDependencies>
              <properties>
                <org.jenkinsci.plugins.workflow.job.properties.BuildDiscarderProperty>
                  <strategy class="hudson.tasks.LogRotator">
                    <daysToKeep>30</daysToKeep>
                    <numToKeep>10</numToKeep>
                    <artifactDaysToKeep>-1</artifactDaysToKeep>
                    <artifactNumToKeep>-1</artifactNumToKeep>
                  </strategy>
                </org.jenkinsci.plugins.workflow.job.properties.BuildDiscarderProperty>

                <!-- Parameters block -->
                <hudson.model.ParametersDefinitionProperty>
                  <parameterDefinitions>
                    <hudson.model.StringParameterDefinition>
                      <name>PROJECT_ID</name>
                      <description>Project ID for the dbt run</description>
                      <defaultValue>{project['project_id']}</defaultValue>
                    </hudson.model.StringParameterDefinition>
                    <hudson.model.StringParameterDefinition>
                      <name>MODEL_NAME</name>
                      <description>Name of the dbt model to run</description>
                      <defaultValue>{model_name}</defaultValue>
                    </hudson.model.StringParameterDefinition>
                    <hudson.model.BooleanParameterDefinition>
                      <name>RUN_ALL</name>
                      <description>Run all dbt models</description>
                      <defaultValue>{run_all}</defaultValue>
                    </hudson.model.BooleanParameterDefinition>
                  </parameterDefinitions>
                </hudson.model.ParametersDefinitionProperty>

              </properties>
              <definition class="org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition" plugin="workflow-cps@3650.vf6b_23a_f86b_29">
                <scm class="hudson.plugins.git.GitSCM" plugin="git@5.2.1">
                  <configVersion>2</configVersion>
                  <userRemoteConfigs>
                    <hudson.plugins.git.UserRemoteConfig>
                      <url>{project['github_link']}</url>
                      <credentialsId>{project['project_name']}</credentialsId>
                    </hudson.plugins.git.UserRemoteConfig>
                  </userRemoteConfigs>
                  <branches>
                    <hudson.plugins.git.BranchSpec>
                      <name>*/main</name>
                    </hudson.plugins.git.BranchSpec>
                  </branches>
                  <doGenerateSubmoduleConfigurations>false</doGenerateSubmoduleConfigurations>
                  <submoduleCfg class="empty-list"/>
                  <extensions/>
                </scm>
                <scriptPath>Jenkinsfile</scriptPath>
                <lightweight>true</lightweight>
              </definition>
              <triggers/>
              <disabled>false</disabled>
            </flow-definition>"""

            response = cls._make_jenkins_request(
                f"{jenkins_url}/createItem?name={project['project_name']}",
                method='post',
                auth=HTTPBasicAuth(username, api_token),
                data=config_xml
            )

            logger.info(f"Created Jenkins job: {project['project_name']}")
            return True

        except Exception as e:
            logger.error(f"Failed to create Jenkins job: {str(e)}")
            raise

    @classmethod
    def job_exists(cls, jenkins_url, job_name, username, api_token):
        """Check if Jenkins job exists"""
        try:
            response = cls._make_jenkins_request(
                f"{jenkins_url}/job/{job_name}/api/json",
                auth=HTTPBasicAuth(username, api_token)
            )
            return True
        except Exception:
            return False

    @classmethod
    def trigger_build(cls, jenkins_url, job_name, username, api_token, params=None):
        """Trigger a parameterized Jenkins build"""
        try:
            response = cls._make_jenkins_request(
                f"{jenkins_url}/job/{job_name}/buildWithParameters",
                method='post',
                auth=HTTPBasicAuth(username, api_token),
                params=params or {}
            )


            queue_url = response.headers.get('Location')
            if not queue_url:
                raise Exception("No queue location in response")

            for _ in range(5):
                queue_response = cls._make_jenkins_request(
                    f"{queue_url}api/json",
                    auth=HTTPBasicAuth(username, api_token),
                    timeout=60
                )
                queue_data = queue_response.json()
                if queue_data.get('executable'):
                    break
                time.sleep(5)
            else:
                raise Exception("Build not started within timeout period after multiple attempts")
            queue_data = queue_response.json()
            if not queue_data.get('executable'):
                raise Exception("Build not started within timeout period")

            return {
                'number': queue_data['executable']['number'],
                'url': queue_data['executable']['url']
            }
        except Exception as e:
            logger.error(f"Failed to trigger Jenkins build: {str(e)}")
            raise


class ExecutionService:
    """Handles execution of queries through Jenkins pipelines"""


    @staticmethod
    def execute_query(project_metadata, model_name=None, run_all=False):
        """
        Execute query by triggering Jenkins pipeline with proper status tracking

        Args:
            project_id: ID of the project to execute
            model_name: Specific model to run (optional)
            run_all: Whether to run all models

        Returns:
            dict: {
                'status': 'triggered'|'failed',
                'build_url': str,
                'build_number': int,
                'execution_id': str
            }
        """
        try:

            config = JenkinsConfig.objects.first()

            if not config:
                raise Exception("Jenkins configuration not found")

            if run_all:
                queries = QueryIntegration.objects.filter(project_id=project_metadata['project_id'])
                queries.update(
                    execution_status=QueryIntegration.ExecutionStatus.RUNNING,
                    start_time=timezone.now()
                )
                execution_id = str(queries.first().query_id)
            else:
                query = QueryIntegration.objects.filter(
                    project_id=project_metadata['project_id'],
                    adapted_query__model_name=model_name
                ).order_by('-created_at').first()
                if not query:
                    raise ValueError(f'No query found for model {model_name}')
                query.execution_status = QueryIntegration.ExecutionStatus.RUNNING
                query.start_time = timezone.now()
                query.save()
                execution_id = str(query.query_id)


            if not JenkinsService.job_exists(
                    config.jenkins_url,
                    project_metadata['project_name'],
                    config.jenkins_user,
                    config.jenkins_token
            ):
                JenkinsService.create_job(
                    config.jenkins_url,
                    project_metadata,
                    config.jenkins_user,
                    config.jenkins_token,
                    model_name,
                    run_all
                )


            build_params = {
                "PROJECT_ID": project_metadata['project_id'],
                "RUN_ALL": run_all,
                "MODEL_NAME": model_name
            }


            build_info = JenkinsService.trigger_build(
                config.jenkins_url,
                project_metadata['project_name'],
                config.jenkins_user,
                config.jenkins_token,
                params=build_params
            )
            ExecutionService._start_build_monitoring(
                project_metadata=project_metadata,
                build_number=build_info['number'],
                job_name=project_metadata['project_name'],
                model_name=model_name,
                run_all=run_all,
                build_url=build_info['url']
            )

            return {
                'status': 'triggered',
                'build_url': build_info['url'],
                'build_number': build_info['number'],
                'execution_id': execution_id
            }

        except ObjectDoesNotExist:
            raise ValueError("Project not found")
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            if run_all and 'project' in locals():
                QueryIntegration.objects.filter(project_id=project_metadata['project_id']).update(
                    execution_status=QueryIntegration.ExecutionStatus.FAILED,
                    end_time=timezone.now()
                )
            elif 'query' in locals():
                query.execution_status = QueryIntegration.ExecutionStatus.FAILED
                query.end_time = timezone.now()
                query.save()
            logger.error(f"Pipeline trigger failed: {str(e)}")
            raise Exception(f"Pipeline trigger failed: {str(e)}")

    @staticmethod
    def _start_build_monitoring(project_metadata, build_number, job_name, model_name, run_all, build_url):
        """
        Start background monitoring of Jenkins build status
        In production, this should be a Celery task
        """


        def monitor():
            try:
                config = JenkinsConfig.objects.first()
                if not config:
                    raise Exception("Jenkins configuration not found")

                max_retries = 3
                retry_count = 0
                timeout = time.time() + 7200

                while time.time() < timeout:
                    try:
                        response = JenkinsService._make_jenkins_request(
                            f"{config.jenkins_url}/job/{job_name}/{build_number}/api/json",
                            auth=HTTPBasicAuth(config.jenkins_user, config.jenkins_token),
                            timeout=30
                        )
                        build_data = response.json()

                        retry_count = 0
                        if build_data.get('result'):

                            status_map = {
                                'SUCCESS': QueryIntegration.ExecutionStatus.COMPLETED,
                                'FAILURE': QueryIntegration.ExecutionStatus.FAILED,
                                None: QueryIntegration.ExecutionStatus.FAILED


                            }


                            result = build_data.get('result')

                            if result == 'None':
                                continue
                            else:
                                status = status_map.get(result)



                            update_kwargs = {
                                'execution_status': status,
                                'end_time': timezone.now(),

                            }

                            if run_all:
                                QueryIntegration.objects.filter(project_id=project_metadata['project_id']).update(**update_kwargs)
                            else:
                                query = QueryIntegration.objects.filter(
                                    project_id=project_metadata['project_id'],
                                    adapted_query__model_name=model_name
                                ).order_by('-created_at').first()
                                if query:
                                    for attr, value in update_kwargs.items():
                                        setattr(query, attr, value)
                                    query.save()


                            ExecutionService._send_notifications(
                                project_metadata,
                                status,
                                model_name,
                                run_all,
                                build_url
                            )
                            return


                        time.sleep(10)

                    except requests.exceptions.RequestException as e:
                        retry_count += 1
                        if retry_count >= max_retries:
                            raise Exception(f"Max retries ({max_retries}) exceeded for build monitoring")

                        wait_time = min(2 ** retry_count, 30)
                        logger.warning(
                            f"Build status check failed (attempt {retry_count}/{max_retries}): {str(e)}. Retrying in {wait_time}s")
                        time.sleep(wait_time)
                        continue

                    except Exception as e:
                        logger.error(f"Unexpected error during monitoring: {str(e)}")
                        raise


                raise Exception(f"Build monitoring timeout reached after {7200} seconds")

            except Exception as e:
                logger.error(f"Build monitoring failed: {str(e)}")
                try:

                    update_kwargs = {
                        'execution_status': QueryIntegration.ExecutionStatus.FAILED,
                        'end_time': timezone.now(),

                    }

                    if run_all:
                        QueryIntegration.objects.filter(project_id=project_metadata['project_id']).update(**update_kwargs)
                    else:
                        query = QueryIntegration.objects.filter(
                            project_id=project_metadata['project_id'],
                            adapted_query__model_name=model_name
                        ).order_by('-created_at').first()
                        if query:
                            for attr, value in update_kwargs.items():
                                setattr(query, attr, value)
                            query.save()
                except Exception as db_error:
                    logger.error(f"Failed to update database status: {str(db_error)}")


        Thread(target=monitor).start()
    @staticmethod
    def _send_notifications(project_metadata, status, model_name, run_all, build_url):
        """Send notifications to users about build completion"""
        try:


            if run_all:
                queries = QueryIntegration.objects.filter(project_id=project_metadata['project_id'])
            else:
                queries = QueryIntegration.objects.filter(
                    project_id=project_metadata['project_id'],
                    adapted_query__model_name=model_name
                ).order_by('-created_at')

            for query in queries:

                message = (
                    f"Pipeline {'for all models' if run_all else f'for model {model_name}'} "
                    f"has completed with status: {status}\n"
                    f"Build URL: {build_url}"
                )
                print(f"Notification for user : {message}")
                send_mail(
                    subject=f"Pipeline {status}: {project_metadata['project_name']}",
                    message=message,
                    from_email="mouadh.fraj@elyadata.com",
                    recipient_list=["mouad.fraj@ensi-uma.tn"],
                    fail_silently=True
                )

        except Exception as e:
            logger.error(f"Notification sending failed: {str(e)}")