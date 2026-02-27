import asyncio
import logging
import time
from collections import OrderedDict
from typing import Optional
from contextlib import AsyncExitStack

import anyio

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
import httpx
from open_webui.env import AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL

log = logging.getLogger(__name__)


def create_insecure_httpx_client(headers=None, timeout=None, auth=None):
    """Create an httpx AsyncClient with SSL verification disabled.

    Note: verify=False must be passed at construction time because httpx
    configures the SSL context during __init__. Setting client.verify = False
    after construction does not affect the underlying transport's SSL context.
    """
    kwargs = {
        "follow_redirects": True,
        "verify": False,
    }
    if timeout is not None:
        kwargs["timeout"] = timeout
    if headers is not None:
        kwargs["headers"] = headers
    if auth is not None:
        kwargs["auth"] = auth
    return httpx.AsyncClient(**kwargs)


class MCPClientPool:
    """LRU connection pool for MCP clients, keyed by (url, auth_header).

    Idle connections are evicted after ``ttl`` seconds and the pool holds
    at most ``max_size`` entries.
    """

    def __init__(self, max_size: int = 32, ttl: int = 300):
        self._max_size = max_size
        self._ttl = ttl
        # key → (MCPClient, last_used_timestamp)
        self._pool: OrderedDict[str, tuple["MCPClient", float]] = OrderedDict()
        self._lock = asyncio.Lock()

    def _make_key(self, url: str, headers: Optional[dict]) -> str:
        auth = (headers or {}).get("Authorization", "")
        return f"{url}||{auth}"

    async def acquire(self, url: str, headers: Optional[dict] = None) -> "MCPClient":
        key = self._make_key(url, headers)
        async with self._lock:
            await self._evict_stale()
            if key in self._pool:
                client, _ = self._pool.pop(key)
                # Verify the session is still alive
                try:
                    await asyncio.wait_for(client.session.send_ping(), timeout=3)
                    self._pool[key] = (client, time.monotonic())
                    self._pool.move_to_end(key)
                    log.debug(f"MCP pool hit for {url}")
                    return client
                except Exception:
                    log.debug(f"MCP pooled connection stale for {url}, reconnecting")
                    try:
                        await client.disconnect()
                    except Exception:
                        pass

        # Cache miss — create a new client (outside the lock)
        client = MCPClient()
        await client.connect(url=url, headers=headers)

        async with self._lock:
            # Evict oldest if at capacity
            while len(self._pool) >= self._max_size:
                _, (old_client, _) = self._pool.popitem(last=False)
                try:
                    await old_client.disconnect()
                except Exception:
                    pass
            self._pool[key] = (client, time.monotonic())

        return client

    async def release(self, url: str, headers: Optional[dict] = None):
        """Mark a client as available (update last-used timestamp)."""
        key = self._make_key(url, headers)
        async with self._lock:
            if key in self._pool:
                client, _ = self._pool[key]
                self._pool[key] = (client, time.monotonic())

    async def remove(self, url: str, headers: Optional[dict] = None):
        """Remove and disconnect a client from the pool (e.g. on error)."""
        key = self._make_key(url, headers)
        async with self._lock:
            entry = self._pool.pop(key, None)
        if entry:
            client, _ = entry
            try:
                await client.disconnect()
            except Exception:
                pass

    async def _evict_stale(self):
        """Remove entries older than TTL. Must be called while holding _lock."""
        now = time.monotonic()
        stale_keys = [
            k for k, (_, ts) in self._pool.items() if now - ts > self._ttl
        ]
        for key in stale_keys:
            client, _ = self._pool.pop(key)
            try:
                await client.disconnect()
            except Exception:
                pass

    async def close_all(self):
        async with self._lock:
            for client, _ in self._pool.values():
                try:
                    await client.disconnect()
                except Exception:
                    pass
            self._pool.clear()


# Module-level singleton pool
mcp_client_pool = MCPClientPool()


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = None

    async def connect(self, url: str, headers: Optional[dict] = None):
        async with AsyncExitStack() as exit_stack:
            try:
                if AIOHTTP_CLIENT_SESSION_TOOL_SERVER_SSL:
                    self._streams_context = streamablehttp_client(url, headers=headers)
                else:
                    self._streams_context = streamablehttp_client(
                        url,
                        headers=headers,
                        httpx_client_factory=create_insecure_httpx_client,
                    )

                transport = await exit_stack.enter_async_context(self._streams_context)
                read_stream, write_stream, _ = transport

                self._session_context = ClientSession(
                    read_stream, write_stream
                )  # pylint: disable=W0201

                self.session = await exit_stack.enter_async_context(
                    self._session_context
                )
                with anyio.fail_after(10):
                    await self.session.initialize()
                self.exit_stack = exit_stack.pop_all()
            except Exception as e:
                await asyncio.shield(self.disconnect())
                raise e

    async def list_tool_specs(self) -> Optional[dict]:
        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.list_tools()
        tools = result.tools

        tool_specs = []
        for tool in tools:
            name = tool.name
            description = tool.description

            inputSchema = tool.inputSchema

            # TODO: handle outputSchema if needed
            outputSchema = getattr(tool, "outputSchema", None)

            tool_specs.append(
                {"name": name, "description": description, "parameters": inputSchema}
            )

        return tool_specs

    async def call_tool(
        self, function_name: str, function_args: dict
    ) -> Optional[dict]:
        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.call_tool(function_name, function_args)
        if not result:
            raise Exception("No result returned from MCP tool call.")

        result_dict = result.model_dump(mode="json")
        result_content = result_dict.get("content", {})

        if result.isError:
            raise Exception(result_content)
        else:
            return result_content

    async def list_resources(self, cursor: Optional[str] = None) -> Optional[dict]:
        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.list_resources(cursor=cursor)
        if not result:
            raise Exception("No result returned from MCP list_resources call.")

        result_dict = result.model_dump()
        resources = result_dict.get("resources", [])

        return resources

    async def read_resource(self, uri: str) -> Optional[dict]:
        if not self.session:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.read_resource(uri)
        if not result:
            raise Exception("No result returned from MCP read_resource call.")
        result_dict = result.model_dump()

        return result_dict

    async def disconnect(self):
        # Clean up and close the session
        await self.exit_stack.aclose()

    async def __aenter__(self):
        await self.exit_stack.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.exit_stack.__aexit__(exc_type, exc_value, traceback)
        await self.disconnect()
