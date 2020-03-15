from channels.routing import route_class
from consumer.multiplexed_consumer import *


channel_routing = [
    route_class(CommandDemultiplexer, path="/command"),
    route_class(ObserverDemultiplexer, path="/observe/(?P<oid>[a-zA-Z0-9\-]+)"),
]