import logging
import asyncio
import json
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

ROUTES = {}

def route(path):
    def decorator(func):
        ROUTES[path] = func
        return func
    return decorator

def json_response(status: int, body: dict):
    encoded = json.dumps(body).encode()
    return (
        f"HTTP/1.1 {status} OK\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(encoded)}\r\n"
        f"\r\n"
    ).encode() + encoded

@route("/")
async def home():
    return 200, {"message": "Welcome to looplite!"}

@route("/status")
async def status():
    return 200, {
        "status": "ok",
        "server_time": datetime.utcnow().isoformat()
    }

async def handle(reader, writer):
    try:
        data = await reader.read(1024)
        request = data.decode(errors="ignore")
        lines = request.splitlines()
        if not lines:
            raise ValueError("Empty request")

        method, path, _ = lines[0].split()
        logging.info(f"Received request {method} {path}")
        if method != "GET":
            raise NotImplementedError("Only GET is supported")

        if path in ROUTES:
            status_code, body = await ROUTES[path]()
            response = json_response(status_code, body)
        else:
            response = json_response(404, {"error": "Not Found", "path": path})
    except NotImplementedError as e:
        response = json_response(405, {"error": str(e)})
    except Exception as e:
        response = json_response(500, {"error": "Internal Server Error", "detail": str(e)})

    writer.write(response)
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def main():
    server = await asyncio.start_server(handle, "127.0.0.1", 8080)
    logging.info("looplite server started")
    logging.info(f"Listening on {server.sockets[0].getsockname()}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server stopped by user")