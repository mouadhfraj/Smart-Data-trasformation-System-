from django.urls import path
from .views import integrate_query, execute_query

urlpatterns = [
    path('integrate/', integrate_query, name='integrate-query'),
    path('execute/', execute_query, name='execute-query'),

]