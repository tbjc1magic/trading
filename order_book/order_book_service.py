import asyncio

from grpc import aio

from proto_generate import order_book_service_pb2
from proto_generate import order_book_service_pb2_grpc


class OrderBookServier(order_book_service_pb2_grpc.OrderBookServicer):

    def __init__(self):
        pass

    def FetchOrderBook(self):
        return order_book_service_pb2.FetchOrderBookResponse([order_book_service_pb2.Order()])


async def serve_order_book():
    server = aio.server()
    order_book_service_pb2_grpc.add_OrderBookServicer_to_server(
        OrderBookServier(), server)
    server.add_insecure_port('[::]:50051')
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    print("hello")
    asyncio.run(serve_order_book())
