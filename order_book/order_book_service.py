import asyncio
import logging
import os

from grpc import aio
from grpc_reflection.v1alpha import reflection

from order_book_manager import OrderBookManager
from proto_generate import order_book_service_pb2
from proto_generate import order_book_service_pb2_grpc

logger = logging.getLogger(__name__)


class OrderBookServier(order_book_service_pb2_grpc.OrderBookServicer):
    def __init__(self, order_book_manager):
        self._order_book_manager = order_book_manager

    async def FetchOrderBook(
        self, request: order_book_service_pb2.FetchOrderBookRequest, context
    ):
        logger.info(f"FetchOrderBook request {request}")

        order_books = await self._order_book_manager.read("bnbbtc")
        print(order_books)

        response = order_book_service_pb2.FetchOrderBookResponse(
            orders=[order_book_service_pb2.Order(price=1.0, quantity=1.0, order_type=1)]
        )
        logger.info(f"FetchOrderBook response {response}")
        return response


async def serve_order_book(order_book_manager):
    order_book_manager = OrderBookManager(["bnbbtc", "ethbusd"])
    server = aio.server()
    order_book_service_pb2_grpc.add_OrderBookServicer_to_server(
        OrderBookServier(order_book_manager), server
    )
    service_names = (
        order_book_service_pb2.DESCRIPTOR.services_by_name["OrderBook"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)
    server.add_insecure_port("[::]:50051")
    await server.start()
    t1 = asyncio.create_task(server.wait_for_termination())
    t2 = asyncio.create_task(order_book_manager.run())
    await asyncio.Event().wait()


if __name__ == "__main__":
    logging.basicConfig(filename="example.log", encoding="utf-8", level=logging.ERROR)
    logging.getLogger().addHandler(logging.StreamHandler())
    os.environ["GRPC_TRACE"] = "all"
    # os.environ["GRPC_VERBOSITY"] = "DEBUG"
    print("hello")
    asyncio.run(serve_order_book(None))
