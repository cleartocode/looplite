import re
import logging
import asyncio
import json
from typing import Union
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass, field
import inspect

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@dataclass
class Request:
    method: str
    path: str
    headers: dict = field(default_factory=dict)
    query_params: dict = field(default_factory=dict)
    body: str = ""

    def json(self):
        try:
            return json.loads(self.body)
        except json.JSONDecodeError:
            return None
    
    @classmethod
    def from_raw(cls, header_text: str, body_text: str):
        """
        Alternative constructor to create Request from raw HTTP request string.

        HTTP Request Format:
        GET /path?query=param HTTP/1.1
        Header1: value1
        Header2: value2

        body content
        """

        header_lines = header_text.splitlines()
        if not header_lines:
            raise ValueError("Empty HTTP request")

        # 1. Parse Method and Path
        method, path, _ = header_lines[0].split()

        # 2. Parse URL & query params
        parsed_url = urlparse(path)
        path = parsed_url.path
        raw_query_params = parse_qs(parsed_url.query)
        query_params = {k: v[0] for k, v in raw_query_params.items()}

        # 3. Parse Headers
        headers = {}
        for line in header_lines[1:]:
            if ": " in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        return cls(
            method=method,
            path=parsed_url.path,
            headers=headers,
            query_params=query_params,
            body=body_text
        )
    
    @classmethod
    async def from_stream(cls, reader: asyncio.StreamReader):
        """
        Alternative constructor to create Request from asyncio StreamReader.
        It reads bytes from the socket until the full HTTP request is received.
        Splits headers from body based on double CRLF.
        Returns a Request instance.

        ```
        HTTP Request Format:
        GET /path?query=param HTTP/1.1
        Header1: value1
        Header2: value2

        Body Content
        ```
        """

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

        return cls.from_raw(request_text, body_text)



@dataclass
class Response:
    body: any = None
    status_code: int = 200
    headers: dict = field(default_factory=dict)
    content_type: str = "text/plain"

    def json(self) -> Union[dict, list, None]:
        if isinstance(self.body, (dict, list)):
            return self.body
    
        try:
            if isinstance(self.body, bytes):
                return json.loads(self.body.decode())
            return json.loads(str(self.body))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
    
    def to_bytes(self) -> bytes:
        if isinstance(self.body, (dict, list)):
            body_bytes = json.dumps(self.body).encode("utf-8")
            self.headers.setdefault("Content-Type", "application/json")
        elif isinstance(self.body, str):
            body_bytes = self.body.encode("utf-8")
            self.headers.setdefault("Content-Type", self.content_type)
        elif isinstance(self.body, bytes):
            body_bytes = self.body
            self.headers.setdefault("Content-Type", self.content_type)
        else:
            body_bytes = str(self.body).encode("utf-8")
            self.headers.setdefault("Content-Type", self.content_type)

        self.headers["Content-Length"] = str(len(body_bytes))

        status_map = {200: "200 OK", 404: "404 Not Found", 500: "500 Internal Server Error"}
        status_text = status_map.get(self.status_code, "Unknown Status")

        header_lines = "".join(f"{k}: {v}\r\n" for k, v in self.headers.items())

        header = (
            f"HTTP/1.1 {status_text}\r\n"
            f"{header_lines}"
            f"\r\n"
        )

        return header.encode("utf-8") + body_bytes


class Looplite:
    def __init__(self):
        self.routes = []
    
    def _get_args(self, handler, request: Request, params: dict) -> dict:
        """
        Gets arguments for the handler function based on its signature.
        It matches parameters from path variables, query parameters, and body JSON.
        """
        sig = inspect.signature(handler)
        bound_args = sig.bind_partial()

        if "request" in sig.parameters:
            bound_args.arguments["request"] = request

        # 1. Path parameters
        for name, value in params.items():
            if name in sig.parameters:
                bound_args.arguments[name] = value

        # 2. Query parameters
        for name, param in sig.parameters.items():
            if name in request.query_params and name not in bound_args.arguments:
                bound_args.arguments[name] = request.query_params[name]

        # 3. Body parameters (assuming JSON body)
        body_json = request.json() or {}
        for name, param in sig.parameters.items():
            if name in body_json and name not in bound_args.arguments:
                bound_args.arguments[name] = body_json[name]

        return bound_args.arguments
    
    def route(self, path: str, method=["GET"]) -> callable:
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
    
    def get_handler_and_path_params(self, method: str, path: str) -> tuple:
        """
        Searches through registered routes and returns (handler, path_params) if found, else (None, None).
        """
        for m, regex, handler in self.routes:
            if m == method.upper():
                match = regex.match(path)
                if match:
                    return handler, match.groupdict()
        return None, None

    
    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """
        Main request handler that processes incoming HTTP requests.
        """

        # 1. Request Object Creation
        request = await Request.from_stream(reader)
        logging.info(f"Received {request.method} request for {request.path}")
        # 2. Route resolution
        handler, path_params = self.get_handler_and_path_params(request.method, request.path)

        response = None
        if handler:
            try:
                # 1. Prepare argument to pass to handler
                # 2. Call handler
                result = await handler(**self._get_args(handler, request, path_params))
                # 3. Create Response
                response = result if isinstance(result, Response) else Response(body=result)
            except Exception as e:
                logging.error(f"Error in handler: {e}")
                response = Response(
                    status_code=500,
                    body={"error": "Internal Server Error"}
                )
        else:
            response = Response(
                status_code=404,
                body={"error": "Not Found"}
            )
        
        # 4. Send response
        writer.write(response.to_bytes())
        await writer.drain()
        writer.close()
    
    async def run(self, host="127.0.0.1", port=8080):
        server = await asyncio.start_server(self.handle, host, port)
        logging.info(f"Looplite server running on {host}:{port}")
        async with server:
            await server.serve_forever()


app = Looplite()


if __name__ == "__main__":
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
        pass
