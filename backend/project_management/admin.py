from django.contrib import admin
from .src.repo.models import DatabaseConfiguration, ProjectMetadata


@admin.register(DatabaseConfiguration)
class DatabaseConfigurationAdmin(admin.ModelAdmin):
    list_display = ('database_id', 'database_type', 'display_config_summary')
    search_fields = ('database_type',)
    list_per_page = 20

    def display_config_summary(self, obj):
        """Display a shortened version of config parameters"""
        return str(obj.config_parameters)[:50] + '...' if len(str(obj.config_parameters)) > 50 else str(
            obj.config_parameters)

    display_config_summary.short_description = 'Config Summary'


@admin.register(ProjectMetadata)
class ProjectMetadataAdmin(admin.ModelAdmin):
    list_display = ('project_id', 'project_name', 'database_type', 'tool', 'is_active', 'github_link')
    list_filter = ('tool', 'is_active', 'database_type')
    search_fields = ('project_name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('project_name', 'description', 'database_type')
        }),
        ('GitHub Info', {
            'fields': ('github_link', 'github_token'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        })
    )