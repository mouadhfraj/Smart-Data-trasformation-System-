import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from .consumers import ExecutionConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_system.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path('ws/execution/<str:execution_id>/', ExecutionConsumer.as_asgi()),
        ])
    ),
})