import asyncio
import json
import logging
import threading
import time
import urllib.request

import websockets
from sortedcontainers import SortedDict

logger = logging.getLogger(__name__)
WEBSOCKET_ADDRESS = "wss://stream.binance.com:9443/ws/{}@depth"
INITIALIZATION_HTTP_ADDRESS = "https://api.binance.com/api/v3/depth?symbol={}&limit=1000"


class IllegalPatchException(Exception):
    pass


class SingleSymbolOrderBook:
    def __init__(self, symbol="bnbbtc"):
        self._symbol = symbol
        self._bid_order_book = SortedDict()
        self._ask_order_book = SortedDict()
        self._last_update_id = None
        self._lock = threading.Lock()
        self._first_patch = True
        self._websocket_address = WEBSOCKET_ADDRESS.format(symbol)
        self._initial_http_address = INITIALIZATION_HTTP_ADDRESS.format(symbol.upper())

    async def initialize(self, websocket):
        logger.info(f"{self._symbol} --- initializing.")
        contents = await asyncio.to_thread(urllib.request.urlopen(self._initial_http_address).read)
        snapshot = json.loads(contents)
        last_update_id = snapshot["lastUpdateId"]
        bid_order_book = list(map(lambda order: list(map(float, order)), snapshot["bids"]))
        ask_order_book = list(map(lambda order: list(map(float, order)), snapshot["asks"]))

        with self._lock:
            self._last_update_id = last_update_id
            self._bid_order_book.update(bid_order_book)
            self._ask_order_book.update(ask_order_book)
        logger.info(f"{self._symbol} --- initialization complete.")

    def _update(self, patch):
        self._last_update_id = patch["u"]
        for key, order_book in [("a", self._ask_order_book), ("b", self._bid_order_book)]:
            for price, quantity in patch[key]:
                if not quantity:
                    order_book.pop(price, None)
                else:
                    order_book[price] = quantity

    async def update(self, websocket):
        logger.info(f"{self._symbol} updating.")

        time.sleep(1)
        contents = await websocket.recv()
        patch = json.loads(contents)
        if patch["u"] <= self._last_update_id:
            logger.warning(f"{self._symbol} --- drop outdated patches.")
            return

        patch["a"] = map(lambda order: list(map(float, order)), patch["a"])
        patch["b"] = map(lambda order: list(map(float, order)), patch["b"])

        if self._first_patch:
            if not (patch["U"] <= self._last_update_id + 1 <= patch["u"]):
                raise IllegalPatchException("First update patch does not match last_update_id.")
            with self._lock:
                self._first_patch = False
                self._update(patch)
        else:
            if patch["U"] != self._last_update_id + 1:
                raise IllegalPatchException("Missing update event between last_update_id and coming update.")

            with self._lock:
                self._update(patch)
        logger.debug(f"{self._symbol} --- {self._ask_order_book}")
        logger.debug(f"{self._symbol} --- {self._bid_order_book}")
        logger.info(f"{self._symbol} --- updating complete.")

    async def read(self):
        return {"bids": self._bid_order_book, "asks": self._ask_order_book}

    async def run(self):
        async with websockets.connect(self._websocket_address) as websocket:
            await self.initialize(websocket)
            while True:
                await self.update(websocket)


class OrderBookManager:

    def __init__(self, symbols=None):
        self._symbols = symbols
        self._tasks = {}
        self._order_books = {}

    async def start(self, symbol=None):
        """
        Start a single order book for @symbol
        :param symbol:
        :return:
        """
        order_book = SingleSymbolOrderBook(symbol)
        self._order_books[symbol] = order_book
        self._tasks[symbol] = asyncio.create_task(order_book.run())

    async def read(self, symbol):
        return await self._order_books[symbol].read()

    async def run(self):
        for symbol in self._symbols:
            await self.start(symbol)

        while self._tasks:
            await asyncio.wait(self._tasks.values())


if __name__ == "__main__":
    logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler())
    order_book_manager = OrderBookManager(["bnbbtc", "ethbusd"])
    asyncio.run(order_book_manager.run())
