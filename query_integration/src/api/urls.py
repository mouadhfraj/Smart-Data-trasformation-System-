from django.urls import path
from .views import integrate_query, execute_query

urlpatterns = [
    path('query/integrate/', integrate_query, name='integrate-query'),
    path('query/execute/', execute_query, name='execute-query'),

]