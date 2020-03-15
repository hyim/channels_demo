from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.generic.http import AsyncHttpConsumer
from .models import ObservableStatus
from json import dumps
from django.db.models.signals import post_save
from channels.layers import get_channel_layer
import asyncio
import string
from random import *
import logging
import functools
from channels.utils import await_many_dispatch
from asgiref.sync import async_to_sync
from channels.exceptions import StopConsumer


class SomeHttpConsumer(AsyncHttpConsumer):

    '''
    async def __call__(self, receive, send):
        self.send = send

        body = []
        self.channel_layer = get_channel_layer()
        if self.channel_layer is not None:
            self.channel_name = await self.channel_layer.new_channel()
            self.channel_receive = functools.partial(self.channel_layer.receive, self.channel_name)
        # Store send function
        if self._sync:
            self.base_send = async_to_sync(send)
        else:
            self.base_send = send
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            elif not message["type"].startswith('http'):

                try:
                    if self.channel_layer is not None:
                        await await_many_dispatch([self.channel_receive], self.dispatch)
                except StopConsumer:
                    # Exit cleanly
                    pass
            else:
                if "body" in message:
                    body.append(message["body"])
                if not message.get("more_body"):
                    await self.handle(b"".join(body))
                    return
    '''

    async def handle(self, body):
        await get_channel_layer().group_add('group-{}-{}'.format('normal', 67), self.channel_name)
        await self.send_headers(headers=[
            ("Content-Type", "application/json"),
        ])
        await self.send_body(b"", more_body=True)

    async def relay(self, message):
        await self.send_body(dumps(message.get('content', {})).encode('utf-8'), more_body=True)


class LongLongConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        oid = self.scope["url_route"]["kwargs"]['oid']
        stream = self.scope["url_route"]["kwargs"]['stream']
        await self.channel_layer.group_add('group-{}-{}'.format(stream, oid), self.channel_name)
        return await super().connect()

    async def relay(self, message):
        await self.send_json(message.get('content', {}))


class CommandConsumer(AsyncJsonWebsocketConsumer):

    async def receive_json(self, content, **kwargs):
        command = content.get('command', None)
        if command is not None:
            if command == "start":
                oid = ObservableStatus.objects.create().id
                await self.send_json(dict(observe_urls={'normal': '/observe/normal/{}'.format(oid),
                                                        'error': '/observe/error/{}'.format(oid)},
                                          status=200, id=oid, command='start',
                                          message='You can observe the output of id {} now!'.format(oid)))
                # TODO init observable message sending
            elif command == "stop":
                oid = content.get('oid', None)
                if oid is not None:
                    try:
                        # TODO finalize observable message sending
                        target = ObservableStatus.objects.filter(id=oid).select_for_update()
                        target.update(is_alive=False)
                        await self.send_json(dict(status=200, id=oid, command='stop', message='Emission ended!'))
                    except:
                        await self.send_json(dict(status=422, message='You must specify a valid observer id!'))
                else:
                    await self.send_json(dict(status=422, message='You must specify an observer id!'))
            else:
                await self.send_json(dict(status=200, message='echo your message: {}'.format(dumps(content))))


all_char = string.ascii_letters + string.punctuation + string.digits


def init_loop():
    logging.getLogger('asyncio').setLevel(logging.DEBUG)
    loop = None
    try:
        loop = asyncio.get_event_loop()
    except:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_forever()
#    loop.set_debug(True)
    return loop


def generate_random_string():
    return "".join(choice(all_char) for x in range(randint(10, 16)))


message_types = ['normal', 'error']


def repeat_message(oid):
    @asyncio.coroutine
    async def func(future):
        cnt = 0
        while ObservableStatus.objects.get(id=oid).is_alive:
            await asyncio.sleep(0.5)
            stream = message_types[randint(0,1)]
            group_name = 'group-{}-{}'.format(stream, oid)
            await get_channel_layer().group_send(group_name, dict(type='relay',
                                                                  content=dict(id=oid,
                                                                               message=generate_random_string()),
                                                                  count=cnt))
            cnt += 1
        else:
            stream = message_types[randint(0,1)]
            group_name = 'group-{}-{}'.format(stream, oid)

            await get_channel_layer().group_send(group_name, dict(type='relay',
                                                                  content=dict(id=oid,
                                                                               message='finished!'),
                                                                  count=cnt))
            future.set_result('done')
    return func


def init_handler(sender, instance, created, raw, using, update_fields, **kwargs):
    if created:
        loop = init_loop()
        co = repeat_message(instance.id)
        future = asyncio.Future()
        asyncio.ensure_future(co(future), loop=loop)


post_save.connect(init_handler, ObservableStatus)


