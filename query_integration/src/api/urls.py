from django.urls import path
from .views import integrate_query, execute_query, workflow_callback

urlpatterns = [
    path('integrate/', integrate_query, name='integrate-query'),
    path('execute/', execute_query, name='execute-query'),
    path('workflow/callback/', workflow_callback, name='workflow-callback')
]