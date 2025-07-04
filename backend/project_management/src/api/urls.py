from django.urls import path
from . import views

urlpatterns = [
    path('', views.root_view, name='root'),
    path('<int:user_id>/projects/', views.list_projects, name='list-projects'),
    path('projects/initialize/', views.setup_project, name='setup-project'),
    path('projects/<int:project_id>/', views.project_detail, name='project-detail'),
    path('projects/<int:project_id>/restore', views.restore_project, name='restore_project'),
    path('database-configurations/<str:database_type>/', views.get_database_config, name='get-database-config'),
    path('projects/<int:project_id>/database-schema/', views.retrieve_database_schema, name='retrieve_database_schema'),

]