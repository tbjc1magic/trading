import asyncio
import logging
import os

from grpc import aio
from grpc_reflection.v1alpha import reflection
from order_book_protos import order_book_service_pb2
from order_book_protos import order_book_service_pb2_grpc

from order_book_manager import OrderBookManager

logger = logging.getLogger(__name__)


class InsufficientOrdersInTheMarket(Exception):
    pass


class UnsupportedOrderType(Exception):
    pass


class OrderBookServier(order_book_service_pb2_grpc.OrderBookServicer):
    def __init__(self, order_book_manager):
        self._order_book_manager = order_book_manager

    async def FetchOrderBook(
        self, request: order_book_service_pb2.FetchOrderBookRequest, context
    ):
        logger.info(f"FetchOrderBook request {request}")

        order_books = await self._order_book_manager.read(request.symbol)
        response = order_book_service_pb2.FetchOrderBookResponse(
            orders=[
                order_book_service_pb2.Order(
                    price=p, quantity=q, order_type=order_book_service_pb2.OrderType.ASK
                )
                for p, q in order_books["asks"].items()
            ]
            + [
                order_book_service_pb2.Order(
                    price=p * -1,
                    quantity=q,
                    order_type=order_book_service_pb2.OrderType.BID,
                )
                for p, q in order_books["bids"].items()
            ]
        )
        logger.info(f"FetchOrderBook response {request.symbol}")
        return response

    async def GetWorstOrderPrice(
        self, request: order_book_service_pb2.FetchOrderBookRequest, context
    ):
        order_books = await self._order_book_manager.read(request.symbol)
        quantity = 0
        if request.order_type == order_book_service_pb2.OrderType.ASK:
            order_book = order_books["asks"]
            for key in iter(order_book):
                quantity += order_book[key]
                if quantity >= request.quantity:
                    return order_book_service_pb2.GetWorstOrderPriceResponse(price=key)
        elif request.order_type == order_book_service_pb2.OrderType.BID:
            order_book = order_books["bids"]
            for key in iter(order_book):
                quantity += order_book[key]
                if quantity >= request.quantity:
                    return order_book_service_pb2.GetWorstOrderPriceResponse(
                        price=key * -1
                    )
        else:
            raise UnsupportedOrderType()

        raise InsufficientOrdersInTheMarket()


async def serve_order_book():
    order_book_manager = OrderBookManager(["bnbbtc", "ethbusd"], save_data=True)
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
    await asyncio.gather(server.wait_for_termination(), order_book_manager.run())


if __name__ == "__main__":
    format = "%(asctime)-15s %(message)s"
    logging.basicConfig(
        filename="example.log", format=format, encoding="utf-8", level=logging.INFO
    )
    logging.getLogger().addHandler(logging.StreamHandler())
    os.environ["GRPC_TRACE"] = "all"
    # os.environ["GRPC_VERBOSITY"] = "DEBUG"
    print("hello")
    asyncio.run(serve_order_book())
