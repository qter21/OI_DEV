# Deployment Guide - California Legal Citation Validator v2.7.5

## 🎉 First Stable Production Release

Version 2.7.5 is the **first production-ready stable version** with comprehensive testing, security hardening, and API migration complete.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Deployment Options](#deployment-options)
3. [Option 1: Open WebUI Admin Panel (Recommended)](#option-1-open-webui-admin-panel-recommended)
4. [Option 2: Docker Image Update](#option-2-docker-image-update)
5. [Option 3: Hot-Patch Running Container](#option-3-hot-patch-running-container)
6. [Configuration](#configuration)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)
9. [Migration from v2.6.x](#migration-from-v26x)

---

## Prerequisites

### Required
- Open WebUI instance (v0.3.0+)
- Access to CodeCond API (https://www.codecond.com/api/v2)
- Python 3.11+ (for the filter runtime)

### Python Dependencies
```python
httpx>=0.24.0
pydantic>=2.0.0
```

These are installed automatically by Open WebUI when the filter is loaded.

---

## Deployment Options

Choose the deployment method based on your setup:

| Method | Best For | Downtime | Complexity |
|--------|----------|----------|------------|
| **Option 1: Admin Panel** | Quick updates, testing | None | Low |
| **Option 2: Docker Image** | Production, CI/CD | ~30-60s | Medium |
| **Option 3: Hot-Patch** | Emergency fixes | None | High |

---

## Option 1: Open WebUI Admin Panel (Recommended)

### Step 1: Access Admin Panel
1. Navigate to your Open WebUI instance
2. Log in as an administrator
3. Go to **Admin Panel** → **Functions** (or **Filters**)

### Step 2: Edit Filter
1. Find "California Legal Citation Validator" in the list
2. Click **Edit** (pencil icon)
3. You'll see the current filter code

### Step 3: Update Code
1. Open `legal_citation_validator.py` from this repository
2. Select ALL code (Cmd+A / Ctrl+A)
3. Copy the code (Cmd+C / Ctrl+C)
4. In the Admin Panel, select ALL existing code
5. Paste the new code (Cmd+V / Ctrl+V)
6. Click **Save**

### Step 4: Verify Version
1. Check the filter header shows:
   ```python
   version: 2.7.5
   ```
2. Check the priority valve:
   ```python
   priority: int = Field(
       default=100,
       ...
   )
   ```

### Step 5: Test
1. Open a chat with a model
2. Send: `EVID 761`
3. Verify the response includes Evidence Code Section 761 content
4. Check that it's NOT showing Family Code Section 761

---

## Option 2: Docker Image Update

### Step 1: Update Source Code

```bash
# Navigate to your danshari deployment directory
cd /path/to/danshari-deploy

# Update legal_citation_validator.py
cp /path/to/OI_DEV/legal_citation_validator.py ./filters/

# Verify version
grep "version:" ./filters/legal_citation_validator.py
# Should show: version: 2.7.5
```

### Step 2: Rebuild Docker Image

```bash
# Build new image
docker build -t danshari:v2.7.5 .

# Tag for your registry (adjust for your setup)
docker tag danshari:v2.7.5 us-west2-docker.pkg.dev/project-anshari/danshari-repo/danshari:v2.7.5
docker tag danshari:v2.7.5 us-west2-docker.pkg.dev/project-anshari/danshari-repo/danshari:latest

# Push to registry
docker push us-west2-docker.pkg.dev/project-anshari/danshari-repo/danshari:v2.7.5
docker push us-west2-docker.pkg.dev/project-anshari/danshari-repo/danshari:latest
```

### Step 3: Deploy to GCloud

```bash
# SSH to your GCloud instance
gcloud compute ssh danshari-v-25 --zone=us-west2-a

# Navigate to deployment directory
cd /home/dx/danshari-deploy

# Pull latest image
docker compose pull app

# Restart service
docker compose restart app

# Verify container is healthy
docker compose ps
# Should show: Up XX seconds (healthy)
```

### Step 4: Verify Logs

```bash
# Check startup logs for version
docker logs danshari-compose --tail 100 | grep "legal_citation\|v2.7"

# You should see:
# legal_citation_validator - INFO - [INLET v2.7.5] Processing query...
```

---

## Option 3: Hot-Patch Running Container

⚠️ **Warning**: This is for emergency fixes only. Changes will be lost on container restart.

### Step 1: Copy Filter to Container

```bash
# From your local machine
gcloud compute ssh danshari-v-25 --zone=us-west2-a --command='cat > /tmp/legal_citation_validator.py' < legal_citation_validator.py
```

### Step 2: Replace Filter in Container

```bash
# SSH to GCloud instance
gcloud compute ssh danshari-v-25 --zone=us-west2-a

# Find filter location in container
docker exec danshari-compose find / -name "function_code_citation_validator.py" 2>/dev/null

# Copy new version
docker cp /tmp/legal_citation_validator.py danshari-compose:/path/to/filters/

# Restart Open WebUI process (if needed)
docker exec danshari-compose pkill -HUP python
```

### Step 3: Verify

```bash
# Check logs
docker logs danshari-compose --tail 50 | grep "v2.7.5"
```

---

## Configuration

### Priority Setting (CRITICAL)

The most important configuration for v2.7.5 is the **priority** valve:

```python
priority: int = Field(
    default=100,  # MAXIMUM - runs FIRST before all other filters
    description="Filter execution priority (higher = runs first)",
    ge=0,
    le=100,
)
```

**Why Priority 100?**
- Ensures Legal Citation Validator runs **BEFORE** Prompt Enhancer
- Prevents RAG from interfering with exact citation lookups
- Guarantees API-fetched content is injected before any modifications

### Recommended Valve Settings

```python
# Core functionality
enable_direct_lookup: bool = True      # Enable API lookups
enable_post_validation: bool = True    # Validate LLM responses

# API settings
api_base_url: str = "https://www.codecond.com/api/v2"
api_timeout_seconds: int = 5

# Performance
cache_ttl_seconds: int = 3600          # 1 hour cache
enable_context_preload: bool = True    # Pre-warm cache

# UI
show_status: bool = True               # Show "Fetching..." status
enable_legislative_history: bool = True

# Debug (production: False)
debug_mode: bool = False
show_performance_metrics: bool = False
```

---

## Verification

### Test Cases

#### Test 1: Evidence Code (EVID)
```
Query: EVID 761
Expected: California Evidence Code Section 761 (cross-examination definition)
NOT: Family Code Section 761 (community property)
```

#### Test 2: Multiple Codes
```
Query: What's the difference between EVID 761 and FAM 761?
Expected: Both sections retrieved, clearly labeled with code names
```

#### Test 3: Compound Query
```
Query: Show me sections 760, 761, and 762 of the Evidence Code
Expected: All three sections retrieved and displayed
```

#### Test 4: Priority Verification
```
Query: EVID 761
Check logs for: [INLET v2.7.5] BEFORE any [ENHANCER] logs
```

### Check Logs

```bash
# View real-time logs
docker logs -f danshari-compose 2>&1 | grep "legal\|INLET\|OUTLET"

# Expected patterns:
# [INLET v2.7.5] Processing query...
# [INLET-REGEX] Extracted citations from query: [{'code': 'EVID', 'section': '761', ...}]
# [API CALL] GET /codes/EVID/sections/761
# [INLET] Injected 1 sections
```

### Verify Priority

```bash
# Check filter load order
docker logs danshari-compose --since 5m | grep "load_function_module"

# Legal validator should load BEFORE prompt enhancer
# Expected:
# Loaded module: function_code_citation_validator  <- FIRST
# Loaded module: function__prompt_enhancer        <- SECOND
```

---

## Troubleshooting

### Issue 1: LLM Shows Wrong Code (e.g., FAM 761 instead of EVID 761)

**Symptoms:**
- Query: "EVID 761"
- Response shows Family Code Section 761

**Diagnosis:**
```bash
# Check if inlet is extracting correctly
docker logs danshari-compose --tail 200 | grep "INLET-REGEX"

# Check priority
docker logs danshari-compose --tail 200 | grep "priority"
```

**Solution:**
1. Verify priority is set to 100 (maximum)
2. Check that Legal Validator loads BEFORE Prompt Enhancer
3. Restart container if needed

### Issue 2: No API Calls Being Made

**Symptoms:**
- Logs show `[INLET-REGEX] Extracted citations` but no `[API CALL]`
- No sections injected

**Diagnosis:**
```bash
# Check if enable_direct_lookup is True
docker exec danshari-compose python -c "
from filters.legal_citation_validator import Filter
f = Filter()
print(f'Direct lookup enabled: {f.valves.enable_direct_lookup}')
"
```

**Solution:**
1. Check `enable_direct_lookup` valve is `True`
2. Verify API endpoint is accessible
3. Check circuit breaker status in logs

### Issue 3: API Timeout Errors

**Symptoms:**
```
[API ERROR] HTTP request timeout after 5s
```

**Solution:**
```python
# Increase timeout in valve settings
api_timeout_seconds: int = 10  # Increase from 5 to 10
```

### Issue 4: Cache Not Working

**Symptoms:**
- Every query shows `[CACHE MISS]`
- Performance is slow

**Diagnosis:**
```bash
# Check cache stats in logs
docker logs danshari-compose | grep "Cache.*hit rate"
```

**Solution:**
1. Verify `cache_ttl_seconds` is set appropriately
2. Check that multiple queries for same section show cache hits
3. Monitor cache size: should be < 1000 entries

---

## Migration from v2.6.x

### Breaking Changes
None - v2.7.5 is fully backward compatible with v2.6.x

### New Features to Enable
1. **Priority 100**: Ensures first execution
2. **API Integration**: No MongoDB credentials needed
3. **Multi-version Support**: Handles sections with multiple versions
4. **Debug Logging**: Better troubleshooting

### Migration Steps

1. **Backup Current Configuration**
   ```bash
   # Export current filter settings from Admin Panel
   # Or backup docker-compose.yml
   ```

2. **Update Code**
   - Use Option 1 (Admin Panel) for quickest update
   - Use Option 2 (Docker) for production deployments

3. **Verify Configuration**
   - Check priority = 100
   - Check api_base_url = "https://www.codecond.com/api/v2"
   - Test with "EVID 761"

4. **Monitor Logs**
   ```bash
   # Watch for any errors after deployment
   docker logs -f danshari-compose --since 1m | grep ERROR
   ```

5. **Validate Performance**
   - Cache hit rate should be 85-90%
   - API calls should complete in 100-300ms
   - No circuit breaker openings

---

## Production Checklist

- [ ] Version v2.7.5 confirmed in logs
- [ ] Priority set to 100
- [ ] API endpoint accessible
- [ ] Test query "EVID 761" returns Evidence Code (not Family Code)
- [ ] Cache hit rate > 80%
- [ ] No circuit breaker triggers
- [ ] Debug mode disabled (`debug_mode: False`)
- [ ] Performance metrics disabled in production (`show_performance_metrics: False`)
- [ ] Logs show `[INLET v2.7.5]` on startup
- [ ] Filter loads BEFORE Prompt Enhancer

---

## Support

### Documentation
- `CHANGELOG.md` - Version history
- `SECURITY.md` - Security policy
- `README.md` - Project overview

### Issues
Report issues on GitHub: [Add your repository URL]

### Logs
When reporting issues, include:
```bash
# Version info
docker logs danshari-compose --tail 100 | grep "v2.7"

# Error logs
docker logs danshari-compose --tail 500 | grep ERROR

# Query logs
docker logs danshari-compose --tail 200 | grep "INLET\|OUTLET\|API"
```

---

## Performance Benchmarks (v2.7.5)

| Metric | Target | Typical | Notes |
|--------|--------|---------|-------|
| Cache Hit Rate | >80% | 85-90% | With context preload |
| API Latency | <500ms | 100-300ms | 5s timeout |
| Cache Hit Latency | <100ms | <50ms | In-memory |
| Filter Priority | 100 | 100 | Maximum (runs first) |
| Circuit Breaker Threshold | 5 failures | 5 | 60s timeout |

---

## Version History

- **v2.7.5** - First stable production release (2025-10-21)
- **v2.7.0-v2.7.4** - API migration and debugging
- **v2.6.x** - MongoDB-based implementation
- **v2.0.0** - Cache validation fixes
- **v1.0.0** - Initial release

---

**Last Updated**: October 21, 2025
**Version**: 2.7.5
**Status**: ✅ Production Ready
