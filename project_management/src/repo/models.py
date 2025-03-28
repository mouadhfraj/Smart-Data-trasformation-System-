from django.db import models
from django.utils import timezone

class DatabaseConfiguration(models.Model):
    database_id = models.AutoField(primary_key=True)
    database_type = models.CharField(max_length=50, unique=True, null=False)
    config_parameters = models.JSONField(null=False)


    class Meta:
        db_table = 'database_configurations'
        verbose_name = 'Database Configuration'
        verbose_name_plural = 'Database Configurations'

    def __str__(self):
        return f"{self.database_type} (ID: {self.database_id})"


class ProjectMetadata(models.Model):
    TOOL_CHOICES = [
        ('dbt', 'DBT'),
        ('sqlmesh', 'SQLMesh'),
    ]

    project_id = models.AutoField(primary_key=True)
    project_name = models.CharField(max_length=255, unique=True, null=False)
    description = models.TextField(null=True, blank=True)
    database_type = models.ForeignKey(
        DatabaseConfiguration,
        to_field='database_type',
        db_column='database_type',
        on_delete=models.PROTECT,
        related_name='projects'
    )
    database_metadata = models.JSONField(null=False)
    github_link = models.URLField(null=True, blank=True)
    github_token = models.CharField(max_length=255, null=True, blank=True)
    tool = models.CharField(max_length=10, choices=TOOL_CHOICES, null=False)
    user_id = models.IntegerField(null=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'project_metadata'
        verbose_name = 'Project Metadata'
        verbose_name_plural = 'Projects Metadata'
        indexes = [
            models.Index(fields=['project_name']),
            models.Index(fields=['user_id']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.project_name} (ID: {self.project_id})"