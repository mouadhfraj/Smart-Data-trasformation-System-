import uuid
from django.db import models
from project_management.src.repo.models import ProjectMetadata

class QueryIntegration(models.Model):
    class ExecutionStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    query_id = models.AutoField(primary_key=True)
    original_query = models.TextField()
    adapted_query = models.JSONField()
    target_tool = models.CharField(max_length=20)
    project = models.ForeignKey(ProjectMetadata, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    execution_status = models.CharField(
        max_length=20,
        choices=ExecutionStatus.choices,
        default=ExecutionStatus.PENDING
    )
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'query_integration'