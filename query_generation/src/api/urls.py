from django.urls import path
from .views import generate_query

urlpatterns = [
    path('query/generate/', generate_query, name='generate-query'),

]