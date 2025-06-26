from django.db import models
from project_management.src.repo.models import ProjectMetadata

class QueryIntegration(models.Model):

    query_id = models.AutoField(primary_key=True)
    original_query = models.TextField()
    adapted_query = models.JSONField()
    target_tool = models.CharField(max_length=20)
    project = models.ForeignKey(ProjectMetadata, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    execution = models.ForeignKey(
        'Execution',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='integrated_queries'
    )
    user_id = models.IntegerField(null=False)

    class Meta:
        db_table = 'query_integration'

class Execution(models.Model):
    class ExecutionStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    execution_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(ProjectMetadata, on_delete=models.CASCADE)
    queries = models.ManyToManyField(
        QueryIntegration,
        related_name='executions'
    )
    user_id = models.IntegerField(null=False,default=1)
    model_name = models.CharField(max_length=100, default="All models")
    target_tool = models.CharField(max_length=20)
    execution_status = models.CharField(
        max_length=20,
        choices=ExecutionStatus.choices,
        default=ExecutionStatus.PENDING
    )
    logs = models.TextField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'executions'

from django.db import models
from django.contrib.auth.models import User


class JenkinsConfig(models.Model):
    """
    Stores Jenkins configuration for the application
    """
    name = models.CharField(max_length=100, unique=True, help_text="Configuration name")
    jenkins_url = models.URLField(verbose_name="Jenkins URL")
    jenkins_user = models.CharField(max_length=100, verbose_name="API Username")
    jenkins_token = models.CharField(max_length=200, verbose_name="API Token")
    backend_url = models.URLField(verbose_name="Backend URL")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Jenkins Configuration"
        verbose_name_plural = "Jenkins Configurations"