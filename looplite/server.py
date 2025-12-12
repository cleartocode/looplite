import re
import logging
import asyncio
import json
from datetime import datetime
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class Looplite:
    def __init__(self):
        self.routes = []
    
    def route(self, path, method=["GET"]):
        # 1. Transform <variable> to regex named groups
        def decorator(func):
            regex_path = re.sub(r'<([^>]+)>', r'(?P<\1>[^/]+)', path)
            regex_path = f"^{regex_path}$"
            compiled_path = re.compile(regex_path)

            # 2. Register the route
            for m in method:
                self.routes.append((m.upper(), compiled_path, func))
            logging.info(f"Route registered: {path} with methods {method}")
            return func
        return decorator
    
    def resolve(self, method, path):
        """
        Searches through registered routes and returns (handler, params) if found, else (None, None).
        """
        for m, regex, handler in self.routes:
            if m == method.upper():
                match = regex.match(path)
                if match:
                    return handler, match.groupdict()
        return None, None
    
    async def handle(self, reader, writer):
        # Robust HTTP request parsing
        header_data = b""
        while b"\r\n\r\n" not in header_data:
            chunk = await reader.read(1024)
            if not chunk: break
            header_data += chunk

        headers, body = header_data.split(b"\r\n\r\n", 1)
        request_text = headers.decode()

        content_length = 0
        for line in request_text.splitlines():
            if line.lower().startswith("content-length:"):
                content_length = int(line.split(":")[1].strip())
                break
        
        if (remaining := content_length - len(body)) > 0:
            body += await reader.readexactly(remaining)
        
        body_text = body.decode()

        # --- 2. Route resolution ---
        first_line = request_text.splitlines()[0]
        method, path, _ = first_line.split()

        handler, params = self.resolve(method, urlparse(path).path)

        # --- 3. Handler invocation and response construction ---
        response_body = ""
        status_code = 200

        if handler:
            try:
                result = await handler(**params)
                
                if isinstance(result, (dict, list)):
                    response_body = json.dumps(result)
                else:
                    response_body = str(result)
            except Exception as e:
                logging.error(f"Error in handler: {e}")
                status_code = 500
                response_body = json.dumps({"error": "Internal Server Error"})
        else:
            status_code = 404
            response_body = json.dumps({"error": "Not Found"})
        
        # --- 4. Send response ---
        response = (
            f"HTTP/1.1 {status_code} OK\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(response_body)}\r\n"
            "\r\n"
            f"{response_body}"
        ).encode()
        writer.write(response)
        await writer.drain()
        writer.close()
    
    async def run(self, host="127.0.0.1", port=8080):
        server = await asyncio.start_server(self.handle, host, port)
        logging.info(f"Looplite server running on {host}:{port}")
        async with server:
            await server.serve_forever()


app = Looplite()


@app.route("/", method=["GET"])
async def home():
    return {"message": "Welcome to Looplite!"}


@app.route("/user/<id>", method=["GET"])
async def get_user(id):
    return {"user_id": id, "name": "user_" + id, "status": "active"}


@app.route("/sum/<a>/<b>", method=["GET"])
async def sum(a: int, b: int):
    return {"result": int(a) + int(b)}


if __name__ == "__main__":
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
        pass
