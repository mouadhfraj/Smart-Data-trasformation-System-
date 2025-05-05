from django.urls import path
from .views import integrate_query, execute_query, executions_details, get_execution , get_project_models

urlpatterns = [
    path('query/integrate/', integrate_query, name='integrate-query'),
    path('query/execute/', execute_query, name='execute-query'),
    path('query/<int:user_id>/executions_details/', executions_details, name='executions_details'),
    path('query/executions/<str:execution_id>/', get_execution, name='get_execution'),
    path('projects/<int:project_id>/models/', get_project_models, name='get_project_models'),

]