from django.urls import path
from . import views

urlpatterns = [
    path('', views.root_view, name='root'),
    path('projects/<int:user_id>/', views.list_projects, name='list-projects'),
    path('project/initialize/', views.setup_project, name='setup-project'),
    path('project/<int:project_id>/', views.project_detail, name='project-detail'),
    path('database-configurations/<str:database_type>/', views.get_database_config, name='get-database-config'),
]