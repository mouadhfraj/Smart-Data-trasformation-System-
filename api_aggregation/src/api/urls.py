from django.urls import path
from .views import (
    query_auto_generate,
    query_integrate_execute,
    query_auto_execute
)

urlpatterns = [
    path('projects/<int:project_id>/query/generate/', query_auto_generate),
    path('projects/<int:project_id>/query/integrate-execute/', query_integrate_execute),
    path('projects/<int:project_id>/query/run/ ', query_auto_execute),
]