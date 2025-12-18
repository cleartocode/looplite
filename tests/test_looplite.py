import pytest
from looplite.looplite import Looplite, Request, Response


@pytest.fixture
def app():
    """
    Returns a Looplite app instance for testing.
    """
    return Looplite()

# ---- 1 Unit Tests Request, Response Classes ----
def test_request_parsing_from_stream():
    """
    Test Request.from_stream method to ensure it correctly parses an HTTP request from a stream.
    """
    import asyncio

    async def mock_stream_reader(request_bytes: bytes):
        reader = asyncio.StreamReader()
        reader.feed_data(request_bytes)
        reader.feed_eof()
        return reader

    async def test():
        raw_request = (
            b"GET /test/path?param=value HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Content-Length: 11\r\n"
            b"\r\n"
            b"Hello World"
        )
        reader = await mock_stream_reader(raw_request)
        request = await Request.from_stream(reader)

        assert request.method == "GET"
        assert request.path == "/test/path"
        assert request.query_params == {"param": "value"}
        assert request.headers["Host"] == "localhost"
        assert request.headers["Content-Length"] == "11"
        assert request.body == "Hello World"

    asyncio.run(test())

def test_request_parsing_from_raw():
    """
    Test Request.from_raw method to ensure it correctly parses an HTTP request from raw text.
    """
    raw_headers = (
        "POST /api/data?item=42 HTTP/1.1\r\n"
        "Host: example.com\r\n" \
        "Content-Type: application/json\r\n" \
        "Content-Length: 15\r\n"
    )
    body_text = '{"key":"value"}'

    request = Request.from_raw(raw_headers, body_text)

    assert request.method == "POST"
    assert request.path == "/api/data"
    assert request.query_params == {"item": "42"}
    assert request.headers["Host"] == "example.com"
    assert request.headers["Content-Type"] == "application/json"
    assert request.headers["Content-Length"] == "15"
    assert request.json() == {"key": "value"}


def test_response_to_bytes():
    """
    Test Response.to_bytes method to ensure it correctly serializes a Response to bytes.
    """
    response = Response(
        status_code=200,
        headers={"Content-Type": "text/plain"},
        body="Hello, World!"
    )

    response_bytes = response.to_bytes()
    assert b"HTTP/1.1 200 OK" in response_bytes
    assert b"Content-Type: text/plain" in response_bytes
    assert b"Hello, World!" in response_bytes


def test_dependency_injection(app):
    """
    Test that dependency injection works correctly in Looplite.
    """
    
    # Simulate a handler with multiple arguments
    async def handler(item_id, sort, name, request):
        pass

    req = Request(
        method="GET",
        path="/items/123",
        query_params={"sort": "asc", "name": "test"},
        headers={},
        body='{"name": "foo", "value": 10}'
    )
    path_params = {"item_id": "123"}

    kwargs = app._get_args(handler, req, path_params)

    assert kwargs["item_id"] == "123"
    assert kwargs["sort"] == "asc"
    assert kwargs["name"] == "test"
    assert kwargs["request"] == req
    assert isinstance(kwargs["request"], Request)
    assert "value" not in kwargs  # 'value' is not a parameter of handler


# ---- Integration Tests ----

@pytest.mark.asyncio
async def test_route_logic_execution(app):
    """
    Simulates the full cycle: Route -> Injection -> Handler Execution -> Response
    """

    @app.route("/users/<id>")
    async def get_user(id, request):
        return {"id": id, "host": request.headers.get("Host")}
    
    req = Request(
        method="GET",
        path="/users/42",
        headers={"Host": "testserver"}
    )

    handler, path_params = app.get_handler_and_path_params(req.method, req.path)
    assert handler is not None

    result = await handler(**app._get_args(handler, req, path_params))

    assert result == {"id": "42", "host": "testserver"}


@pytest.mark.asyncio
async def test_manual_response_creation(app):
    """
    Tests that a handler can return a Response object directly.
    """

    @app.route("/download")
    async def download_file():
        return Response(
            status_code=200,
            headers={"Content-Disposition": "attachment; filename=\"file.txt\""},
            body="File content"
        )

        handler, _ = app.get_handler_and_path_params("GET", "/download")
        result = await handler()

        assert isinstance(result, Response)
        assert result.status_code == 200
        assert result.headers["Content-Disposition"] == 'attachment; filename="file.txt"'
        assert result.body == "File content"