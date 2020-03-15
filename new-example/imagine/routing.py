from django.conf.urls import url

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.http import AsgiHandler
from consumer.long_long_consumer import LongLongConsumer, CommandConsumer, SomeHttpConsumer

application = ProtocolTypeRouter({
    "websocket": AuthMiddlewareStack(
        URLRouter([
            url(r'^observe/(?P<stream>normal|error)/(?P<oid>[0-9]+)$', LongLongConsumer),
            url(r'^command', CommandConsumer),
        ])
    ),
    "http": AuthMiddlewareStack(
        URLRouter([
            url(r'', AsgiHandler)
        ])
    )
})
