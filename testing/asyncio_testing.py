import asyncio
import time
import urllib.request


async def t(s):
    for _ in range(10):
        await asyncio.sleep(1)
        if _ == 3 and s == "t1":
            asyncio.create_task(t("t3"))
        print(s)


async def main():
    t1 = asyncio.create_task(t("t1"))
    t2 = asyncio.create_task(t("t2"))
    # done, pending = await asyncio.wait({t1, t2})
    # print(done, pending)
    await asyncio.Event().wait()


def main2():
    t0 = time.time()
    a = urllib.request.urlopen(
        "https://api.binance.com/api/v3/depth?symbol=BNBBTC&limit=1000 "
    )
    t1 = time.time()
    a.read()
    t2 = time.time()
    print(t1 - t0, t2 - t1)


async def main1():
    t0 = time.time()
    task = asyncio.to_thread(
        urllib.request.urlopen,
        "https://api.binance.com/api/v3/depth?symbol=BNBBTC&limit=1000 ",
    )
    t1 = time.time()
    print(t1 - t0)
    stream = await task
    t2 = time.time()
    print(t2 - t1)
    content_coro = asyncio.to_thread(stream.read)
    t3 = time.time()
    print(t3 - t2)
    contents = await content_coro
    t4 = time.time()
    print(t4 - t3)
    print(contents)


import pymongo
import os

ORDER_BOOK_TABLE_NAME = "order_book"
ORDER_BOOK_DB_NAME = "crypto_db"


async def main3():
    client = pymongo.MongoClient("mongodb://tbjc:tbjc19881018@192.168.86.39/crypto_db")
    r = client["crypto_db"].test.insert_one({"aaa": 1})
    print(r)

    mongodb_user = os.getenv("MONGODB_USER").strip('"')
    mongodb_pwd = os.getenv("MONGODB_PWD").strip('"')
    mongodb_host = os.getenv("MONGODB_HOST").strip('"')
    client_url = (
        f"mongodb://{mongodb_user}:{mongodb_pwd}@{mongodb_host}/{ORDER_BOOK_DB_NAME}"
    )
    client = pymongo.MongoClient(client_url)
    db = client[ORDER_BOOK_DB_NAME]
    db.test.insert_one({"bobo1de": 3})


if __name__ == "__main__":
    print("hello")
    # asyncio.ensure_future(t("t1"))
    # asyncio.ensure_future(t("t2"))
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main(loop))
    asyncio.run(main3())
    # main2()
    # asyncio.get_event_loop().run_forever()
    print("Done")
    # loop.run_forever()
