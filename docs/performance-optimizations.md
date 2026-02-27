# Jaco Performance Optimizations

Implemented 2025-02-27. These changes address the primary user complaint that Jaco feels **slow** by optimizing the full request lifecycle: user prompt → backend → LLM → response rendering.

## Changes

### TIER 1: Quick Wins

#### 1.1 Fix JSON.stringify deep comparison during streaming
- **Files**: `ResponseMessage.svelte`, `UserMessage.svelte`, `MultiResponseMessages.svelte`
- **Problem**: On every streaming token, two full `JSON.stringify()` comparisons of the entire message object fired. For a 2000-token response = 2000 stringify cycles of large objects.
- **Fix**: Replaced with shallow field comparisons (`content.length`, `sources.length`, `done`, `error`). Only clones the message when something actually changed.

#### 1.2 Replace JSON.parse(JSON.stringify) with structuredClone
- **File**: `Chat.svelte`
- **Problem**: 11 instances of `JSON.parse(JSON.stringify())` — 2-5x slower than `structuredClone()`.
- **Fix**: Replaced with `structuredClone()` for objects/arrays. Primitive string copies (like `$chatId`) simplified to direct assignment.

#### 1.3 Increase stream delta chunk size
- **File**: `k8s/base/jaco-configmap.yaml`
- **Problem**: Default chunk size of 1 meant every single token emitted a separate websocket frame.
- **Fix**: Set `CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE: "5"`. Batches 5 tokens before emitting — 5x fewer websocket frames, well under human perception threshold.

#### 1.4 Remove console.log in streaming parser
- **File**: `src/lib/apis/streaming/index.ts`
- **Problem**: `console.log(parsedData)` logged every SSE event to browser console during streaming.
- **Fix**: Deleted the line.

#### 1.5 Increase Uvicorn workers
- **File**: `k8s/base/jaco-configmap.yaml`
- **Problem**: Single Python process handled all requests. Any blocking call blocked everyone.
- **Fix**: Set `UVICORN_WORKERS: "2"`. Redis-backed Socket.io sessions already support multi-worker.

### TIER 2: Medium Effort

#### 2.1 Debounce markdown lexing during streaming
- **File**: `Markdown.svelte`
- **Problem**: `marked.lexer()` re-parsed the entire accumulated content on every token delta — O(n²) total work across a streaming session.
- **Fix**: Debounced to at most once per 100ms during streaming. First token lexes immediately, subsequent tokens batch. When `done=true`, lexes immediately and cancels any pending debounce.

#### 2.2 MCP client connection pooling
- **Files**: `mcp/client.py`, `middleware.py`, `main.py`
- **Problem**: New MCP client created + `connect()` + `session.initialize()` on every request. Each connect = full HTTP handshake with 10s timeout.
- **Fix**: Module-level `MCPClientPool` with LRU eviction (max 32 connections, 5min TTL). Connections validated via ping before reuse. Middleware acquires from pool instead of creating new clients each request.

#### 2.3 Parallelize web search with raw user query
- **File**: `middleware.py`
- **Problem**: Sequential flow: LLM generates optimized queries (1-5s) → then searches. The raw user prompt is often a good search query already.
- **Fix**: Starts searching with the raw user prompt immediately via `asyncio.create_task()` while the LLM generates optimized queries in parallel. Results are merged with URL deduplication. Optimized queries that match the raw prompt are skipped to avoid duplicate searches.

#### 2.4 Batch event emitter DB writes
- **File**: `socket/main.py`
- **Problem**: On every `"message"` event during streaming, the emitter read the full chat JSON blob, appended one token, and wrote the full blob back.
- **Fix**: Content accumulated in memory and flushed to DB every 1 second instead of per-token. The first message event seeds from DB; subsequent deltas append in memory. The final content is still written at stream end by the streaming response handler regardless.

#### 2.5 Async parallel image conversion
- **File**: `middleware.py`
- **Problem**: Images converted to base64 sequentially — N images = N × latency.
- **Fix**: All image conversions run concurrently via `asyncio.gather()`. Failures are handled individually (non-fatal) so one bad image doesn't block others. Total time: max(latency) instead of sum(latency).

## Verification

After deploying, verify with:

1. **Streaming smoothness**: Send a prompt, observe token rendering. Should feel noticeably smoother (items 1.1, 1.2, 1.3, 1.4, 2.1).
2. **Time-to-first-token**: Measure from send click to first visible token. Should improve (items 1.3, 1.5, 2.3).
3. **Concurrent users**: Open 2 browser tabs, send prompts simultaneously. Should not block each other (item 1.5).
4. **Web search latency**: Enable web search, send a query. Should return faster (item 2.3).
5. **Browser DevTools Performance tab**: Profile during streaming. CPU usage should drop significantly (items 1.1, 1.2, 2.1).

## Future Considerations (not implemented)

- **Virtual scrolling** for long conversations (50+ messages)
- **Break up Chat.svelte** (2953 lines) into focused modules
- **Migrate chat storage** from JSON blob to normalized `chat_message` table
- **Direct SSE streaming** instead of HTTP → Socket.io relay
- **Redis cache** for web search results
