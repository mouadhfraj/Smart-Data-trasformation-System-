from django.contrib import admin
from .src.repo.models import QueryIntegration, Execution, JenkinsConfig
from django import forms

class QueryIntegrationAdmin(admin.ModelAdmin):
    list_display = ('query_id', 'project', 'target_tool',  'created_at', 'execution')
    list_filter = ('target_tool', 'created_at', 'execution')
    search_fields = ('original_query', 'adapted_query')
    readonly_fields = ('query_id', 'created_at')
    fieldsets = (
        (None, {
            'fields': ('query_id', 'project', 'target_tool', 'execution')
        }),
        ('Query Details', {
            'fields': ('original_query', 'adapted_query'),
            'classes': ('collapse',)
        }),

    )
    raw_id_fields = ('execution',)

admin.site.register(QueryIntegration, QueryIntegrationAdmin)


class ExecutionAdmin(admin.ModelAdmin):
    list_display = ('execution_id', 'project', 'user_id', 'model_name', 'target_tool', 'execution_status', 'start_time')
    list_filter = ('execution_status', 'target_tool', 'model_name')
    search_fields = ('project__name', 'user_id')
    readonly_fields = ('execution_id', 'start_time', 'end_time')
    fieldsets = (
        (None, {
            'fields': ('execution_id', 'project', 'user_id')
        }),
        ('Execution Details', {
            'fields': ('model_name', 'target_tool', 'queries'),
            'classes': ('wide',)
        }),
        ('Status Info', {
            'fields': ('execution_status', 'start_time', 'end_time'),
            'classes': ('wide',)
        }),
    )
    filter_horizontal = ('queries',)

admin.site.register(Execution, ExecutionAdmin)


class JenkinsConfigForm(forms.ModelForm):
    class Meta:
        model = JenkinsConfig
        fields = '__all__'
        widgets = {
            'jenkins_token': forms.PasswordInput(render_value=True),
        }


@admin.register(JenkinsConfig)
class JenkinsConfigAdmin(admin.ModelAdmin):
    form = JenkinsConfigForm
    list_display = ('name', 'jenkins_url')
    fieldsets = (
        (None, {
            'fields': ('name', 'created_by')
        }),
        ('Jenkins Configuration', {
            'fields': (
                'jenkins_url',
                'jenkins_user',
                'jenkins_token',
                'backend_url'
            )
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)