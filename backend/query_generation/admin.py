from django.contrib import admin
from django.utils.html import format_html
from .src.repo.models import GeneratedQuery,LLMModel

@admin.register(GeneratedQuery)
class GeneratedQueryAdmin(admin.ModelAdmin):
    list_display = ('query_id', 'llm_provider', 'status', 'is_valid', 'created_at')
    search_fields = ('raw_query', 'prepared_prompt')
    list_filter = ('llm_provider', 'status', 'is_valid')




@admin.register(LLMModel)
class LLMModelAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'model_code',
        'provider_badge',
        'type_badge',
        'capabilities',
        'is_active',
        'is_default',
        'status_badge',
        'created_at'
    )
    list_filter = ('provider', 'model_type', 'is_active')
    search_fields = ('name', 'model_code', 'api_model_name')
    list_editable = ('is_active', 'is_default')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name',
                'model_code',
                'provider',
                'model_type',
                'is_active',
                'is_default'
            )
        }),
        ('API Configuration', {
            'fields': (
                'api_model_name',
                'base_url'
            )
        }),
        ('Model Capabilities', {
            'fields': (
                'context_window',
                'max_output_tokens'
            )
        }),
        ('Default Parameters', {
            'fields': (
                'default_temperature',
                'default_top_p'
            )
        }),
        ('Metadata', {
            'fields': (
                'notes',
                'created_at',
                'updated_at'
            )
        }),
    )
    actions = ['activate_models', 'deactivate_models']

    def provider_badge(self, obj):
        colors = {
            'groq': 'blue',
            'openai': 'green',
            'anthropic': 'purple',
            'mistral': 'orange'
        }
        color = colors.get(obj.provider, 'gray')
        return format_html(
            '<span style="color: white; background-color: {};'
            'padding: 2px 6px; border-radius: 10px; font-size: 12px;">'
            '{}</span>',
            color,
            obj.get_provider_display()
        )
    provider_badge.short_description = "Provider"

    def type_badge(self, obj):
        return format_html(
            '<span style="background-color: #f0f0f0; padding: 2px 6px;'
            'border-radius: 10px; font-size: 12px;">{}</span>',
            obj.get_model_type_display()
        )
    type_badge.short_description = "Type"

    def capabilities(self, obj):
        return format_html(
            "<b>Context:</b> {} tokens<br>"
            "<b>Output:</b> {} tokens",
            obj.context_window,
            obj.max_output_tokens
        )
    capabilities.short_description = "Capabilities"

    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: white; background-color: green;'
                'padding: 2px 6px; border-radius: 10px; font-size: 12px;">'
                'Active</span>'
            )
        return format_html(
            '<span style="color: white; background-color: red;'
            'padding: 2px 6px; border-radius: 10px; font-size: 12px;">'
            'Inactive</span>'
        )
    status_badge.short_description = "Status"

    def activate_models(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} models")

    def deactivate_models(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} models")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

