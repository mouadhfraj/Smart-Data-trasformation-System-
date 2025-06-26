
from django.urls import path
from . import views

urlpatterns = [
    path('csrf/', views.get_csrf_token, name='get_csrf_token'),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),
    path('user/', views.user_list, name='user_list'),
    path('me/', views.current_user, name='current_user'),
]