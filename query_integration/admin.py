from django.contrib import admin
from .src.repo.models import QueryIntegration

class QueryIntegrationAdmin(admin.ModelAdmin):
    list_display = ('query_id', 'project', 'target_tool', 'execution_status', 'created_at')
    list_filter = ('target_tool', 'execution_status', 'created_at')
    search_fields = ('original_query', 'adapted_query')
    readonly_fields = ('query_id', 'created_at', 'start_time', 'end_time')
    fieldsets = (
        (None, {
            'fields': ('query_id', 'project', 'target_tool')
        }),
        ('Query Details', {
            'fields': ('original_query', 'adapted_query'),
            'classes': ('collapse',)
        }),
        ('Execution Info', {
            'fields': ('execution_status', 'start_time', 'end_time'),
            'classes': ('wide',)
        }),
    )

admin.site.register(QueryIntegration, QueryIntegrationAdmin)