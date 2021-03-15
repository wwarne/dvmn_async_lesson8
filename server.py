import asyncio
import json
import warnings
from typing import Optional, Any

import aioredis
import trio
import trio_asyncio
from quart import websocket, request
from quart_trio import QuartTrio

import settings
from db import Database
from smsc import SmscApiError, request_smsc
from utils import redis2frontend

app = QuartTrio(__name__)

@app.before_serving
async def create_db_pool():
    """Create and bind db_pool before start serving requests."""
    redis = await trio_asyncio.asyncio_as_trio(aioredis.create_redis_pool)(
        settings.REDIS_URI,
        password=settings.REDIS_PASSWORD,
        encoding='utf-8'
    )
    app.db = Database(redis)

@app.after_serving
async def close_db_pool():
    """Close redis connections on shutdown."""
    if hasattr(app, 'db'):
        app.db.redis.close()
        await trio_asyncio.asyncio_as_trio(app.db.redis.wait_closed)()


@app.route('/')
async def index():
    index_page = trio.Path('templates/index.html')
    return await index_page.read_text()

@app.websocket('/ws')
async def ws():
    while True:
        all_mailings = await trio_asyncio.asyncio_as_trio(app.db.list_sms_mailings)()
        all_data = await trio_asyncio.asyncio_as_trio(app.db.get_sms_mailings)(*all_mailings)
        sms_data = [redis2frontend(item) for item in all_data]
        response = {
            'msgType': 'SMSMailingStatus',
            'SMSMailings': sms_data,
        }
        await websocket.send(json.dumps(response))
        await trio.sleep(1)


@app.route('/send/', methods=['POST'])
async def create():
    form = await request.form
    message_text = form['text']
    phones_list = ['112', '911']
    try:
        send_result = await request_smsc('send', settings.SMSC_LOGIN, settings.SMSC_PASSWORD, {
            'phones': ','.join(phones_list),
            'mes': message_text,
        })
    except SmscApiError as e:
        return {
            'errorMessage': f'получено {e}'
        }
    await trio_asyncio.asyncio_as_trio(app.db.add_sms_mailing)(
        sms_id=send_result['id'],
        phones=phones_list,
        text=message_text,
    )
    return send_result

async def async_main(host: str = '127.0.0.1',
                     port: int = 5000,
                     debug: Optional[bool] = None,
                     use_reloader: bool = True,
                     ca_certs: Optional[str] = None,
                     certfile: Optional[str] = None,
                     keyfile: Optional[str] = None,
                     **kwargs: Any,
                     ):
    """
    Modified version of Quart's app.run().

    Modification is done to integrate trio_asyncio and Quart together.
    """
    async with trio_asyncio.open_loop() as loop:
        assert loop == asyncio.get_event_loop()
        # this line fix problem with aioredis
        # https://github.com/python-trio/trio-asyncio/issues/63
        asyncio._set_running_loop(asyncio.get_event_loop())

        if kwargs:
            warnings.warn(
                f"Additional arguments, {','.join(kwargs.keys())}, are not supported.\n"
                "They may be supported by Hypercorn, which is the ASGI server Quart "
                "uses by default. This method is meant for development and debugging."
            )

        scheme = "https" if certfile is not None and keyfile is not None else "http"
        print(f"Running on {scheme}://{host}:{port} (CTRL + C to quit)")  # noqa: T001, T002

        await app.run_task(host, port, debug, use_reloader, ca_certs, certfile, keyfile)

if __name__ == '__main__':
    trio.run(async_main)
