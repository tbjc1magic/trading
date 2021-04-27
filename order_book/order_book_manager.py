import asyncio
import json
import logging
import os
import threading
import urllib.request

import pymongo
import websockets
from sortedcontainers import SortedDict

logger = logging.getLogger(__name__)
WEBSOCKET_ADDRESS = "wss://stream.binance.com:9443/ws/{}@depth"
INITIALIZATION_HTTP_ADDRESS = (
    "https://api.binance.com/api/v3/depth?symbol={}&limit=1000"
)
ORDER_BOOK_TABLE_NAME = "order_book"
ORDER_BOOK_DB_NAME = "crypto_db"


class IllegalPatchException(Exception):
    pass


class SingleSymbolOrderBook:
    def __init__(self, symbol="bnbbtc", save_data=False):
        self._symbol = symbol
        self._bid_order_book = SortedDict()
        self._ask_order_book = SortedDict()
        self._last_update_id = None
        self._lock = threading.Lock()
        self._first_patch = True
        self._websocket_address = WEBSOCKET_ADDRESS.format(symbol)
        self._initial_http_address = INITIALIZATION_HTTP_ADDRESS.format(symbol.upper())

        mongodb_user = os.getenv("MONGODB_USER").strip('"')
        mongodb_pwd = os.getenv("MONGODB_PWD").strip('"')
        mongodb_host = os.getenv("MONGODB_HOST").strip('"')
        client_url = f"mongodb://{mongodb_user}:{mongodb_pwd}@{mongodb_host}/{ORDER_BOOK_DB_NAME}"
        client = pymongo.MongoClient(client_url)
        self._db = client[ORDER_BOOK_DB_NAME]

    async def initialize(self, websocket):
        logger.info(f"{self._symbol} --- initializing.")
        contents = await asyncio.to_thread(
            urllib.request.urlopen(self._initial_http_address).read
        )
        snapshot = json.loads(contents)
        last_update_id = snapshot["lastUpdateId"]
        bid_order_book = list(
            map(lambda order: (float(order[0]) * -1, float(order[1])), snapshot["bids"])
        )
        ask_order_book = list(
            map(lambda order: list(map(float, order)), snapshot["asks"])
        )

        with self._lock:
            self._last_update_id = last_update_id
            self._bid_order_book.update(bid_order_book)
            self._ask_order_book.update(ask_order_book)
        logger.info(f"{self._symbol} --- initialization complete.")

    def _update(self, patch):
        self._last_update_id = patch["u"]
        for key, order_book in [
            ("a", self._ask_order_book),
            ("b", self._bid_order_book),
        ]:
            for price, quantity in patch[key]:
                if not quantity:
                    order_book.pop(price, None)
                else:
                    order_book[price] = quantity

    async def write_to_db(self, patch):
        data = {
            "event_time": patch["E"],
            "symbol": patch["s"],
            "first_update_id": patch["U"],
            "final_update_id": patch["u"],
            "asks": json.dumps(self._ask_order_book),
            "bids": json.dumps(self._bid_order_book),
        }
        await asyncio.to_thread(self._db[ORDER_BOOK_TABLE_NAME].insert_one, data)

    async def update(self, websocket):
        logger.info(f"{self._symbol} updating.")

        contents = await websocket.recv()
        patch = json.loads(contents)
        if patch["u"] <= self._last_update_id:
            logger.warning(f"{self._symbol} --- drop outdated patches.")
            return

        patch["a"] = map(lambda order: list(map(float, order)), patch["a"])
        patch["b"] = map(
            lambda order: (float(order[0]) * -1, float(order[1])), patch["b"]
        )

        if self._first_patch:
            if not (patch["U"] <= self._last_update_id + 1 <= patch["u"]):
                raise IllegalPatchException(
                    "First update patch does not match last_update_id."
                )
            with self._lock:
                self._first_patch = False
                self._update(patch)
        else:
            if patch["U"] != self._last_update_id + 1:
                raise IllegalPatchException(
                    "Missing update event between last_update_id and coming update."
                )

            with self._lock:
                self._update(patch)

        await self.write_to_db(patch)
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
    def __init__(self, symbols=None, save_data=False):
        self._symbols = symbols
        self._tasks = {}
        self._order_books = {}
        self._save_data = save_data

    async def start(self, symbol=None):
        """
        Start a single order book for @symbol
        :param symbol:
        :return:
        """
        order_book = SingleSymbolOrderBook(symbol, save_data=self._save_data)
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
    logging.basicConfig(filename="example.log", encoding="utf-8", level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler())
    order_book_manager = OrderBookManager(["bnbbtc", "ethbusd"])
    asyncio.run(order_book_manager.run())
