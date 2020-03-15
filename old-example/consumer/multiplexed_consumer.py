from typing import Optional, Callable, Iterable, Mapping, Any

from channels.generic.websockets import JsonWebsocketConsumer
from channels import Group
from channels.generic.websockets import WebsocketMultiplexer, WebsocketDemultiplexer
from .models import ObservableStatus
from django.db.models.signals import post_save
import threading
import time
import string
from json import dumps
from random import *


class CommandConsumer(JsonWebsocketConsumer):

    def receive(self, content, **kwargs):
        command = content.get('command', None)
        send_func = self.send
        if kwargs.get('multiplexer', None) is not None:
            # multiplexed message
            send_func = kwargs['multiplexer'].send

        if command is not None:
            if command == "start":
                oid = ObservableStatus.objects.create().id
                Group('group-{}'.format(oid)).add(self.message.reply_channel)
                send_func(dict(observe_url='/observe/{}'.format(oid),
                               status=200, id=oid, command='start',
                               message='You can observe the output of id {} now!'.format(oid)))
            elif command == "stop":
                oid = content.get('oid', None)
                if oid is not None:
                    try:
                        target = ObservableStatus.objects.filter(id=oid).select_for_update()
                        target.update(is_alive=False)
                        send_func(dict(status=200, id=oid, command='stop', message='Emission ended!'))
                    except:
                        send_func(dict(status=422, message='You must specify a valid observer id!'))
                else:
                    send_func(dict(status=422, message='You must specify an observer id!'))
            else:
                send_func(dict(status=200, message='echo your message: {}'.format(dumps(content))))


class CommandMultiplexer(WebsocketMultiplexer):
    def send(self, payload):
        self.reply_channel.send(self.encode(self.stream, payload), immediately=True)

    @classmethod
    def group_send(cls, name, stream, payload, close=False):
        message = cls.encode(stream, payload)
        if close:
            message["close"] = True
        Group(name).send(message, immediately=True)


class CommandDemultiplexer(WebsocketDemultiplexer):
    consumers = dict(normal=CommandConsumer, error=CommandConsumer)
    multiplexer_class = CommandMultiplexer


class ObserverConsumer(JsonWebsocketConsumer):

    def connect(self, message, **kwargs):
        oid = kwargs.get('oid')
        Group('group-{}'.format(oid)).add(self.message.reply_channel)
        super().connect(message, **kwargs)


class ObserverMultiplexer(WebsocketMultiplexer):
    def send(self, payload):
        self.reply_channel.send(self.encode(self.stream, payload), immediately=True)

    @classmethod
    def group_send(cls, name, stream, payload, close=False):
        message = cls.encode(stream, payload)
        if close:
            message["close"] = True
        Group(name).send(message, immediately=True)


class ObserverDemultiplexer(WebsocketDemultiplexer):
    multiplexer_class = ObserverMultiplexer
    consumers = dict(normal=ObserverConsumer, error=ObserverConsumer)


all_char = string.ascii_letters + string.punctuation + string.digits


def generate_random_string():
    return "".join(choice(all_char) for x in range(randint(10, 16)))


message_types = ['normal', 'error']


class MessageGenerateThread(threading.Thread):

    def __init__(self, group: None = ..., target: Optional[Callable[..., None]] = ..., name: Optional[str] = ...,
                 args: Iterable = ..., kwargs: Mapping[str, Any] = ..., *, daemon: Optional[bool] = ...) -> None:
        super().__init__(group, target, name, args, kwargs, daemon=daemon)
        self.oid = kwargs.get('oid')

    def run(self) -> None:
        group_name = 'group-{}'.format(self.oid)
        while ObservableStatus.objects.get(id=self.oid).is_alive:
            time.sleep(0.5)
            CommandMultiplexer.group_send(group_name, message_types[randint(0,1)],
                                           dict(id=self.oid, message=generate_random_string()))
            ObserverMultiplexer.group_send(group_name, message_types[randint(0,1)],
                                           dict(id=self.oid, message=generate_random_string()))


def init_handler(sender, instance, created, raw, using, update_fields, **kwargs):
    if created:
        thread = MessageGenerateThread(group=None, target=None, name=None, kwargs=dict(oid=instance.id))
        thread.start()


post_save.connect(init_handler, ObservableStatus)

