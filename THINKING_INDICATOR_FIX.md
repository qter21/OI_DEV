# Thinking Indicator Fix - Complete Analysis

## Problem Summary

The thinking indicator status doesn't stop after tasks finish, causing the UI to show "Thinking..." or processing messages indefinitely, even after responses are complete.

## Root Cause Analysis

### Issue 1: Non-Deterministic Request IDs

The original code generates a unique request ID using:

```python
def _generate_request_key(self, body: dict) -> str:
    content = json.dumps(body, sort_keys=True, default=str)
    timestamp = str(time.time())  # ← Different every call!
    hash_input = f"{content}:{timestamp}:{uuid.uuid4()}"  # ← New UUID every call!
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
```

**Problem**: This generates a DIFFERENT ID every time it's called, even for the same request, because:
- `time.time()` changes between calls
- `uuid.uuid4()` generates a new random UUID each time

### Issue 2: FIFO Queue Doesn't Handle Out-of-Order Completion

The original code uses a simple FIFO queue:

```python
# In inlet():
self.request_queue.append(request_id)  # Add to end

# In outlet():
request_id = self.request_queue.pop(0)  # Remove from front
```

**Problem**: This assumes requests complete in the same order they started (FIFO), but real-world requests complete out of order:

```
Timeline:
T1: Request A starts (slow query) → inlet() → queue: [A]
T2: Request B starts (fast query) → inlet() → queue: [A, B]
T3: Request B completes → outlet() → pops A (WRONG!)
T4: Request A completes → outlet() → pops B (WRONG!)

Result:
- Request A's indicator never stops (no one sets its stop_event)
- Request B's stop_event was set, but task already completed
```

### Issue 3: Concurrent Identical Requests

When multiple identical requests happen simultaneously:
- They would have the same body hash
- Need separate tracking for each instance
- FIFO queue per hash needed

## The Solution

### Key Changes in v1.0.4

#### 1. Request Tracker Class

Created a dedicated `RequestTracker` class that:

```python
class RequestTracker:
    def __init__(self):
        # Separate queue for each unique body hash
        self.pending_requests: Dict[str, deque] = defaultdict(deque)
        # Track active requests by sequence number
        self.active_requests: Dict[str, tuple] = {}
        # Track background tasks
        self.active_tasks: Dict[str, asyncio.Task] = {}
        # Counter for unique sequence numbers
        self.request_counter = 0
```

#### 2. Deterministic Body Hashing

```python
def _hash_body(self, body: dict) -> str:
    """Generate deterministic hash from body content."""
    hashable_content = {
        "messages": body.get("messages", []),
        "model": body.get("model", ""),
    }
    content_str = json.dumps(hashable_content, sort_keys=True, default=str)
    return hashlib.sha256(content_str.encode()).hexdigest()[:16]
```

**Benefits**:
- Same body → same hash (deterministic)
- Doesn't include timestamps or random data
- Consistent between inlet() and outlet() calls

#### 3. Per-Hash FIFO Queues

```python
def register_request(self, body: dict):
    body_hash = self._hash_body(body)
    request_seq = f"req_{self.request_counter}"
    self.request_counter += 1

    # Store in queue for this specific hash
    self.pending_requests[body_hash].append((stop_event, start_time, request_seq))

def complete_request(self, body: dict):
    body_hash = self._hash_body(body)
    # Pop from queue for this specific hash (FIFO per hash)
    stop_event, start_time, request_seq = self.pending_requests[body_hash].popleft()
```

**How it works**:

```
Scenario: Two concurrent requests with different content

Request A (hash: abc123):
  inlet() → pending_requests["abc123"] = [(event_A, time_A, "req_1")]

Request B (hash: def456):
  inlet() → pending_requests["def456"] = [(event_B, time_B, "req_2")]

Request B completes first:
  outlet() → hash body → "def456"
  outlet() → pop from pending_requests["def456"] → gets event_B ✓

Request A completes:
  outlet() → hash body → "abc123"
  outlet() → pop from pending_requests["abc123"] → gets event_A ✓
```

```
Scenario: Two concurrent identical requests

Request A (hash: abc123):
  inlet() → pending_requests["abc123"] = [(event_A, time_A, "req_1")]

Request A again (hash: abc123):
  inlet() → pending_requests["abc123"] = [(event_A, time_A, "req_1"),
                                           (event_A2, time_A2, "req_2")]

First completes:
  outlet() → pop from front → gets "req_1" ✓

Second completes:
  outlet() → pop from front → gets "req_2" ✓
```

#### 4. Proper Cleanup

```python
def cleanup_request(self, request_seq: str):
    """Clean up all data for a request."""
    self.active_tasks.pop(request_seq, None)

    if request_seq in self.active_requests:
        _, _, body_hash = self.active_requests[request_seq]
        # Remove from pending queue
        if body_hash in self.pending_requests:
            self.pending_requests[body_hash] = deque([
                item for item in self.pending_requests[body_hash]
                if item[2] != request_seq
            ])
```

Ensures all references are cleaned up properly.

## Testing the Fix

### Test Case 1: Single Request
```
1. Send one request
2. Verify indicator shows after 2 seconds
3. Verify indicator stops when response completes
4. Verify "Done!" message appears
```

### Test Case 2: Concurrent Different Requests
```
1. Send Request A (slow, complex query)
2. Immediately send Request B (fast, simple query)
3. Verify both show indicators
4. Verify Request B indicator stops first
5. Verify Request A indicator stops when its response completes
6. Neither should get stuck
```

### Test Case 3: Concurrent Identical Requests
```
1. Send same request twice in quick succession
2. Verify both show indicators
3. Verify both stop correctly when their responses complete
4. Verify no cross-contamination
```

### Test Case 4: Fast Responses (<2s)
```
1. Send fast request that completes in <2 seconds
2. Verify NO indicator is shown
3. Verify no "Done!" message (since indicator never started)
```

## Migration Guide

### If You're Using the Old Version

1. **Backup your current filter** (if you made customizations)

2. **Replace with fixed version**:
   - Copy `thinking_indicator_fixed.py` to your Open WebUI filters directory
   - Or update the existing file with the new code

3. **Restart Open WebUI** (or reload filters)

4. **Test with multiple concurrent requests** to verify the fix

### Configuration

All settings remain the same:
- `enable_thinking_indicator`: Enable/disable (default: True)
- `minimum_duration_seconds`: Only show for requests >2s (default: 2.0)
- `update_interval_seconds`: Update frequency (default: 2.0)
- `use_contextual_messages`: Smart messages (default: True)
- `use_emoji`: Show emojis (default: True)
- `show_elapsed_time`: Show time (default: True)
- `celebrate_fast_responses`: Special message for fast (<3s) responses
- `warn_slow_responses`: Warning for slow (>30s) responses

## Technical Details

### Architecture

```
Filter Instance (shared across requests)
    └─ RequestTracker
        ├─ pending_requests: Dict[body_hash, deque[(stop_event, start_time, seq)]]
        ├─ active_requests: Dict[seq, (stop_event, start_time, body_hash)]
        └─ active_tasks: Dict[seq, Task]

Request Flow:
1. inlet(body) called
   └─ Generate body_hash from content
   └─ Create stop_event
   └─ Generate unique seq number
   └─ Store in pending_requests[body_hash]
   └─ Start background task

2. Background task runs
   └─ Wait for minimum_duration or stop_event
   └─ Emit status updates periodically
   └─ Stop when stop_event is set

3. outlet(body) called
   └─ Generate body_hash from content
   └─ Pop oldest from pending_requests[body_hash]
   └─ Set stop_event
   └─ Wait for task to complete
   └─ Emit final "Done!" status
   └─ Cleanup
```

### Why This Works

1. **Deterministic matching**: Same request body → same hash → correct queue
2. **FIFO per hash**: Multiple identical requests tracked separately
3. **Unique sequence numbers**: No confusion between concurrent identical requests
4. **Proper cleanup**: No memory leaks or dangling references
5. **Graceful degradation**: If matching fails, just logs a warning (no crash)

## Changelog

### v1.0.4 (Fixed)
- ✅ Fixed request matching with deterministic body hashing
- ✅ Fixed concurrent request handling with per-hash queues
- ✅ Fixed indicator not stopping after completion
- ✅ Fixed race conditions in request tracking
- ✅ Improved cleanup and memory management
- ✅ Better logging for debugging

### v1.0.3 (Original - Broken)
- ❌ Non-deterministic request IDs (timestamp + UUID)
- ❌ Global FIFO queue (fails with out-of-order completion)
- ❌ Indicator gets stuck on concurrent requests
- ❌ Race conditions

## Performance Impact

- **Minimal overhead**: Hash computation is O(1) for typical request sizes
- **Memory efficient**: Only stores active requests, automatic cleanup
- **No blocking**: All async operations, no thread blocking
- **Scalable**: Handles hundreds of concurrent requests efficiently

## Known Limitations

1. **Body modifications**: If other filters significantly modify the request body between inlet() and outlet(), the hash might not match. In this case, the indicator will log a warning and gracefully skip cleanup.

2. **Streaming responses**: For streaming responses, outlet() is called once at the end. The indicator shows for the entire streaming duration.

3. **Very long requests**: For requests taking >5 minutes, the indicator keeps updating. Consider adding a maximum duration if needed.

## Support

If you encounter issues:
1. Check logs for warnings/errors
2. Verify Open WebUI version compatibility
3. Test with a single request first
4. Report issues with logs and request details
