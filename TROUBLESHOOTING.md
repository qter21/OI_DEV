# Troubleshooting Guide

## Common Issues and Solutions

### 1. "404: Model not found" or "400 Bad Request" Error

**Symptoms:**
- Chat displays "404: Model not found" error
- Browser console shows "400 Bad Request" on `/api/chat/completions`
- Error persists even after updating filters/functions

**Root Cause:**
Open WebUI Anthropic Manifold Pipes require **full pipe model IDs** with the `anthropic.` prefix. Short model names like `"claude-haiku-4-5"` don't work.

**Solution:**

#### Fix 1: Update Agent/Model Configuration
1. Go to **Workspace → Models** in Open WebUI
2. Find your agent/model (e.g., `cafamilylawagent-clone`)
3. Click to edit
4. Check the **"Model" field** - if it shows a short name like:
   - ❌ `claude-haiku-4-5`
   - ❌ `claude-sonnet-4-5`
5. Replace with the **full pipe ID**:
   - ✅ `anthropic.claude-haiku-4-5-20251001`
   - ✅ `anthropic.claude-sonnet-4-5-20251022`
6. Save changes

#### Fix 2: Update Filter/Function Model IDs
Check all filters and functions that make LLM calls:

**Prompt Enhancer** (if using):
```python
# Line 298 and 435 in prompt_enhancer.py
model_id: Optional[str] = Field(
    default="anthropic.claude-haiku-4-5-20251001",  # Must use full pipe ID
    description="Model to use for prompt enhancement"
)
```

**Legal Citation Validator** (if using LLM extraction):
```python
# Line 365-367 in legal_citation_validator.py
llm_extraction_model: str = Field(
    default="anthropic.claude-haiku-4-5-20251001",  # Must use full pipe ID
    description="Model for LLM extraction"
)
```

**AnthropicPipe** (main integration):
- This file uses model names passed from the chat interface
- Ensure the chat is using a valid model ID (see Fix 1)

#### Fix 3: Verify Model List
1. In Open WebUI, go to **Settings → Connections**
2. Check that Anthropic Manifold Pipe is connected
3. Click **Refresh** to update available models
4. Verify models appear with the `anthropic.` prefix

### 2. Filter Not Running / Inlet Skipped

**Symptoms:**
- Legal citations not being retrieved
- No database lookups happening
- Filter logs show "Skipping: no legal keywords detected"

**Solution:**

#### Check Priority Settings
Open WebUI runs filters in priority order (higher = first):

```python
# legal_citation_validator.py line 299-304
priority: int = Field(
    default=100,  # MAXIMUM priority - runs FIRST
    description="Filter execution priority (higher = runs first). Set to 100 to run before ALL other filters including Prompt Enhancer.",
    ge=0,
    le=100,
)
```

**Priority Recommendations:**
- Legal Citation Validator: **100** (must run first to extract citations before other filters modify the query)
- Thinking Indicator: **15** (cosmetic, can run anytime)
- Prompt Enhancer: **10** (runs after citation extraction)
- Other filters: **0-50** (depending on requirements)

### 3. Prompt Enhancer Wrapping Citations

**Symptoms:**
- User asks "EVID 761" but inlet doesn't extract it
- Logs show inlet received modified query like "Can you explain Evidence Code Section 761?"
- Citations are missed by regex extraction

**Root Cause:**
Prompt Enhancer runs before Legal Citation Validator and rewrites the query.

**Solution:**
Set Legal Citation Validator priority to **100** (maximum) to ensure it runs **before** Prompt Enhancer:

```python
priority: int = Field(default=100, ...)
```

### 4. Outlet Not Called for Pipes

**Symptoms:**
- Thinking indicator doesn't stop
- Validation not happening on responses
- Outlet logs never appear

**Root Cause:**
Open WebUI **does NOT call outlet()** for streaming Pipe responses. Only for non-streaming OpenAI API responses.

**Solution:**
Use stale request cleanup instead of relying on outlet():

```python
# thinking_indicator.py line 115-120
stale_request_timeout_seconds: float = Field(
    default=90.0,  # Cleanup after 90 seconds
    description="Maximum age for a request before considering it stale. Note: outlet() is NOT called for Pipes."
)
```

For validation filters, either:
1. **Disable outlet validation** when using Pipes (recommended)
2. Use **inlet-only validation** by injecting verified content
3. Implement **WebSocket-based validation** (advanced)

### 5. Docker Restart Doesn't Fix Changes

**Symptoms:**
- Updated filter code but changes don't apply
- Restarted Docker container but old version still runs

**Root Cause:**
Filter/function code is stored in the **Open WebUI database**, not in Docker image files.

**Solution:**
1. Update the filter/function code **in the Open WebUI UI**:
   - Go to **Workspace → Functions** or **Workspace → Filters**
   - Click the filter/function to edit
   - Paste the updated code
   - Click **Save**
2. Docker restart is **NOT required** for filter/function updates
3. Changes apply **immediately** on next request

### 6. Circuit Breaker Open - API Disabled

**Symptoms:**
- Logs show "Circuit breaker OPEN - skipping API lookup"
- No citations being retrieved
- Error started after multiple API failures

**Root Cause:**
The circuit breaker protection triggered after 5+ consecutive API failures.

**Solution:**
1. **Wait 60 seconds** - circuit breaker automatically resets
2. Check API connectivity:
   ```bash
   curl https://www.codecond.com/api/v2/codes/PEN/sections/187
   ```
3. If API is down, increase timeout:
   ```python
   # legal_citation_validator.py line 309-314
   api_timeout_seconds: int = Field(
       default=10,  # Increase if API is slow
       description="Timeout for API requests in seconds"
   )
   ```

### 7. Cache Not Working / Always Missing

**Symptoms:**
- Every citation lookup hits the API
- Logs show "CACHE MISS" for repeated sections
- Cache hit rate shows 0%

**Solution:**

Check TTL settings:
```python
# legal_citation_validator.py line 327-332
cache_ttl_seconds: int = Field(
    default=3600,  # 1 hour
    description="Cache TTL for frequently accessed sections",
    ge=60,
    le=86400,
)
```

Clear cache if corrupt:
```python
# In Python shell or via API
filter_instance.section_cache.clear()
```

## Debugging Tips

### Enable Debug Logging

**Legal Citation Validator:**
```python
debug_mode: bool = Field(
    default=True,  # Enable verbose logging
    description="Enable verbose debug logging"
)
```

**Check Docker Logs:**
```bash
# SSH to server
gcloud compute ssh danshari-v-25 --zone=us-west2-a

# View last 100 lines
docker logs danshari-compose --tail=100

# Follow logs in real-time
docker logs danshari-compose -f

# Search for specific errors
docker logs danshari-compose --since=10m | grep -i "error"
docker logs danshari-compose --since=10m | grep -i "400"
docker logs danshari-compose --since=10m | grep -i "model not found"
```

### Verify Filter Installation

Check that filters are active:
```bash
# In Docker logs, look for startup messages
docker logs danshari-compose | grep "STARTING UP"

# Should see:
# "🔧 California Legal Citation Validator v2.7.6 - STARTING UP"
# "🎨 Thinking Indicator v1.0.7 - STARTING UP"
```

### Test Citation Extraction

In filter debug logs, check:
```
[INLET-DEBUG] Raw user message: 'what does EVID 761 say?'
[INLET-REGEX] Extracted citations from query: [{'code': 'EVID', 'section': '761', ...}]
[API CALL] GET /codes/EVID/sections/761
[API RESULT] Found section - code=EVID, section=761, content_length=...
```

## Model ID Reference

### Valid Anthropic Pipe Model IDs

Always use **full pipe IDs** with `anthropic.` prefix:

```
✅ anthropic.claude-haiku-4-5-20251001
✅ anthropic.claude-sonnet-4-5-20251022
✅ anthropic.claude-opus-4-5-20251022
✅ anthropic.claude-sonnet-3-7-20250219
✅ anthropic.claude-3-5-sonnet-20241022
✅ anthropic.claude-3-5-haiku-20241022
```

### Invalid Model IDs (Will cause 400/404 errors)

```
❌ claude-haiku-4-5
❌ claude-sonnet-4-5
❌ claude-3-5-sonnet
❌ haiku-4-5
❌ sonnet-4-5
```

### Where Model IDs Are Used

1. **Chat Interface** - User selects model from dropdown
2. **Agent Configuration** - Agent's default model setting
3. **Filter/Function ValveSettings** - LLM extraction, enhancement, etc.
4. **System Prompts** - If prompt specifies a model override

## Support

If issues persist:

1. Check logs for specific error messages
2. Verify all model IDs use full pipe format (`anthropic.xxx`)
3. Confirm filter priority settings (Legal Citation Validator should be 100)
4. Ensure filters are updated via UI, not just file edits
5. Check API connectivity to codecond.com
6. Review circuit breaker state in logs

For production deployment issues, see [DEPLOYMENT_GUIDE_V2.7.5.md](DEPLOYMENT_GUIDE_V2.7.5.md).
