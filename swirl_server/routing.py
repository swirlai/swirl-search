from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from swirl.middleware import WebSocketTokenMiddleware  # Import the TokenAuthMiddleware
from django.urls import path
from django.core.asgi import get_asgi_application
from swirl.consumers import Consumer

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': WebSocketTokenMiddleware(
        AuthMiddlewareStack(
            URLRouter([
                path('chatgpt-data', Consumer.as_asgi()),
            ])
        )
    )
})