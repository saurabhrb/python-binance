import asyncio
import threading
from typing import Optional, Dict

from .client import AsyncClient


class ThreadedApiManager(threading.Thread):

    def __init__(
        self, api_key: Optional[str] = None, api_secret: Optional[str] = None,
        requests_params: Optional[Dict[str, str]] = None, tld: str = 'com',
        testnet: bool = False,
        daemon: bool = False,
        identifier: Optional[str] = ''
        
    ):
        """Initialise the BinanceSocketManager

        """
        super().__init__(daemon=daemon)
        try:
            self._loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        except RuntimeError as ex:
            if "There is no current event loop in thread" in str(ex):
                self._loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                self._loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self.identifier = identifier
        self._client: Optional[AsyncClient] = None
        self._running: bool = True
        self._socket_running: Dict[str, bool] = {}
        self._client_params = {
            'api_key': api_key,
            'api_secret': api_secret,
            'requests_params': requests_params,
            'tld': tld,
            'testnet': testnet
        }

    async def _before_socket_listener_start(self):
        ...

    async def socket_listener(self):
        self._client = await AsyncClient.create(loop=self._loop, **self._client_params)
        await self._before_socket_listener_start()
        while self._running:
            await asyncio.sleep(0.2)
        while self._socket_running:
            await asyncio.sleep(0.2)

    async def start_listener(self, socket, path: str, callback):
        async with socket as s:
            while self._socket_running[path]:
                try:
                    msg = await asyncio.wait_for(s.recv(), 3)
                except asyncio.TimeoutError:
                    ...
                    continue
                if not msg:
                    continue
                # callback(msg)
                callback_thread = threading.Thread(target=callback, name="Callback", args=(self.identifier, msg,), daemon=True)
                callback_thread.start()
        del self._socket_running[path]

    def run(self):
        self._loop.call_soon(asyncio.create_task, self.socket_listener())
        if not self._loop.is_running():
            self._loop.run_forever()
        # self._loop.run_until_complete(self.socket_listener())

    def stop_socket(self, socket_name):
        if socket_name in self._socket_running:
            self._socket_running[socket_name] = False

    async def stop_client(self):
        if not self._client:
            return
        await self._client.close_connection()

    def stop(self):
        if not self._running:
            return
        self._running = False
        self._loop.call_soon(asyncio.create_task, self.stop_client())
        for socket_name in self._socket_running.keys():
            self._socket_running[socket_name] = False
