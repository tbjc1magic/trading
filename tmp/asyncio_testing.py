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
    a = urllib.request.urlopen("https://api.binance.com/api/v3/depth?symbol=BNBBTC&limit=1000 ")
    t1 = time.time()
    a.read()
    t2 = time.time()
    print(t1 - t0, t2 - t1)


async def main1():
    t0 = time.time()
    task = asyncio.to_thread(
        urllib.request.urlopen, "https://api.binance.com/api/v3/depth?symbol=BNBBTC&limit=1000 "
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


if __name__ == "__main__":
    print("hello")
    # asyncio.ensure_future(t("t1"))
    # asyncio.ensure_future(t("t2"))
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main(loop))
    asyncio.run(main1())
    # main2()
    # asyncio.get_event_loop().run_forever()
    print("Done")
    # loop.run_forever()
