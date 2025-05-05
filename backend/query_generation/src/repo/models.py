import re

from django.db import models
from django.db.models import JSONField
from project_management.src.repo.models import ProjectMetadata

class GeneratedQuery(models.Model):
    query_id = models.AutoField(primary_key=True)
    raw_query = models.TextField()
    prepared_prompt = models.TextField()
    llm_provider = models.CharField(max_length=50)
    llm_parameters = JSONField()
    generation_time_ms = models.IntegerField()
    status = models.CharField(max_length=20)
    is_valid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    user_id = models.IntegerField()
    project = models.ForeignKey(ProjectMetadata, on_delete=models.CASCADE)

    class Meta:
        db_table = 'generated_queries'
        app_label = 'query_generation'


class LLMModel(models.Model):
    """Table to store and manage available LLM models"""

    # Provider choices
    PROVIDER_CHOICES = [
        ('groq', 'Groq'),
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('mistral', 'Mistral'),
        ('other', 'Other'),
    ]

    # Model type choices
    MODEL_TYPE_CHOICES = [
        ('chat', 'Chat/Instruction'),
        ('code', 'Code Specialized'),
        ('general', 'General Purpose'),
    ]

    # Core model identification
    name = models.CharField(
        max_length=100,
        help_text="Display name for the model (e.g., 'Llama3 70B')"
    )
    model_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique code used in API calls (e.g., 'llama3-70b')"
    )
    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        default='groq',
        help_text="Service provider for this model"
    )
    model_type = models.CharField(
        max_length=20,
        choices=MODEL_TYPE_CHOICES,
        default='chat',
        help_text="Type of model capabilities"
    )

    # API configuration
    api_model_name = models.CharField(
        max_length=100,
        help_text="Exact model name in provider's API (e.g., 'llama3-70b-8192')"
    )
    base_url = models.URLField(
        blank=True,
        null=True,
        help_text="Optional custom base URL for API endpoints"
    )

    # Model capabilities
    context_window = models.PositiveIntegerField(
        default=8192,
        help_text="Context window size in tokens"
    )
    max_output_tokens = models.PositiveIntegerField(
        default=2048,
        help_text="Maximum output tokens"
    )


    default_temperature = models.FloatField(
        default=0.3,
        help_text="Default creativity parameter (0-1)"
    )
    default_top_p = models.FloatField(
        default=0.9,
        help_text="Default nucleus sampling parameter (0-1)"
    )


    is_active = models.BooleanField(
        default=True,
        help_text="Whether this model is available for use"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Set as default model for new projects"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this model"
    )


    def __str__(self):
        return f"{self.name} ({self.provider})"

    class Meta:
        verbose_name = "AI Model"
        verbose_name_plural = "AI Models"
        ordering = ['provider', 'model_type', 'name']
        indexes = [
            models.Index(fields=['provider', 'is_active']),
            models.Index(fields=['model_type', 'is_active']),
        ]