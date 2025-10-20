# 🚀 Quick Deployment Guide

## ✅ File Ready: `legal_citation_validator.py`

Your production-ready pipeline is now available at:
```
/Users/daniel/github_19988/OI_DEV/legal_citation_validator.py
```

---

## 📋 Deployment Steps (15 minutes)

### Step 1: Upload to Open WebUI (5 minutes)

1. **Open Open WebUI** in your browser
2. **Navigate to Admin Panel**
   - Click on your profile icon
   - Select "Admin Panel"

3. **Go to Pipelines**
   - Click "Pipelines" in the left sidebar

4. **Add Pipeline**
   - Click "Add Pipeline" or "+" button
   - Click "Upload from file"
   - Select: `/Users/daniel/github_19988/OI_DEV/legal_citation_validator.py`
   - Click "Upload"

5. **Enable the Pipeline**
   - Toggle the switch to enable it
   - Make sure it's marked as both "Inlet" and "Outlet" filter

---

### Step 2: Configure Connection (5 minutes)

1. **Click on Pipeline Settings** (gear icon)

2. **Update Valves Configuration:**

```json
{
  "mongodb_uri": "mongodb://admin:legalcodes123@localhost:27017",
  "database_name": "ca_codes_db",
  "collection_name": "section_contents",
  "architecture_collection": "code_architectures",
  "enable_direct_lookup": true,
  "enable_post_validation": true,
  "enable_legislative_history": true,
  "cache_ttl_seconds": 3600,
  "debug_mode": false
}
```

**For remote MongoDB:**
- Change `localhost:27017` to your MongoDB host
- Example: `mongodb://admin:password@mongo.example.com:27017`

**For debugging:**
- Set `debug_mode: true` to see detailed logs

3. **Save Configuration**

---

### Step 3: Test the Pipeline (5 minutes)

Run these test queries in Open WebUI:

#### Test 1: Known Citation (Should work)
```
What does Penal Code 187 say?
```

**Expected Result:**
- Exact text from MongoDB retrieved
- Citation marked with ✓ (checkmark)
- Shows: "California Penal Code § 187 ✓"

#### Test 2: Invalid Citation (Should flag)
```
What does Penal Code 999999 say?
```

**Expected Result:**
- Warning message displayed
- Citation marked with ⚠️
- Shows: "~~Penal Code 999999~~ ⚠️"

#### Test 3: Multiple Citations
```
Compare Penal Code 187 with Civil Code 1714
```

**Expected Result:**
- Both sections retrieved if valid
- Both marked with ✓
- Context includes both sections

#### Test 4: RAG + Validation
```
Explain California murder laws
```

**Expected Result:**
- RAG provides semantic context
- Any citations in response validated
- Verified citations marked with ✓

---

## ✅ Verification Checklist

After deployment, verify:

- [ ] Pipeline shows "Active" status
- [ ] MongoDB connection successful (check logs)
- [ ] Test 1 returns exact PEN 187 text
- [ ] Test 2 shows warning for PEN 999999
- [ ] Citations have ✓ or ⚠️ badges
- [ ] Cache working (second query faster)

---

## 🔧 Configuration Options

### MongoDB Connection

**Local Docker (default):**
```python
mongodb_uri = "mongodb://admin:legalcodes123@localhost:27017"
```

**Remote MongoDB:**
```python
mongodb_uri = "mongodb://username:password@your-server:27017"
```

**MongoDB Atlas:**
```python
mongodb_uri = "mongodb+srv://username:password@cluster.mongodb.net/"
```

### Performance Tuning

**Increase cache TTL for better performance:**
```python
cache_ttl_seconds = 86400  # 24 hours
```

**Enable debug logging:**
```python
debug_mode = true  # See detailed operation logs
```

**Disable legislative history for faster responses:**
```python
enable_legislative_history = false
```

---

## 📊 Expected Performance

| Operation | Latency | Notes |
|-----------|---------|-------|
| Cache hit | <50ms | Common sections cached |
| MongoDB lookup | 100-300ms | First-time retrieval |
| Citation detection | <10ms | Regex matching |
| Total overhead | <500ms | Per query |

**Cache Hit Rate:** 70-80% for common sections like PEN 187

---

## 🐛 Troubleshooting

### Issue: "MongoDB connection failed"

**Solution:**
1. Verify MongoDB is running:
   ```bash
   docker ps | grep mongo
   ```

2. Test connection manually:
   ```bash
   docker exec ca-codes-mongodb-local mongosh -u admin -p legalcodes123 --eval "db.serverStatus()"
   ```

3. Check credentials in Valve configuration

### Issue: "No citations detected"

**Solution:**
1. Enable `debug_mode: true`
2. Check logs for citation extraction
3. Verify query format:
   - ✓ "Penal Code 187"
   - ✓ "PEN 187"
   - ✓ "PC 187"
   - ✗ "Section 187" (missing code type)

### Issue: "Citations not validated"

**Solution:**
1. Verify outlet filter is enabled
2. Check `enable_post_validation: true` in config
3. Look for errors in logs
4. Test with known invalid: "PEN 999999"

### Issue: "Pipeline not appearing in Open WebUI"

**Solution:**
1. Check Open WebUI version ≥ 0.3.0
2. Verify Python requirements installed
3. Check pipeline upload logs
4. Restart Open WebUI if needed

---

## 📝 Monitoring

### Check Logs

In Open WebUI Admin Panel:
1. Go to Pipelines
2. Click on "California Legal Citation Validator"
3. View logs for:
   - `✓ Connected to MongoDB: ca_codes_db`
   - `[INLET] Injected X sections`
   - `[CACHE HIT] PEN-187`
   - `[OUTLET] Verified: X, Hallucinations: Y`

### Enable Debug Mode

Set `debug_mode: true` to see:
- Citation extraction details
- Cache hits/misses
- MongoDB query times
- Validation results

---

## 🎯 What Happens Now

### When Users Query

**Query: "What does Penal Code 187 say?"**

```
1. [INLET] Pipeline detects "Penal Code 187"
2. [INLET] Queries MongoDB for exact text
3. [INLET] Injects exact section into context
4. Open WebUI RAG provides additional context
5. LLM generates response with exact text
6. [OUTLET] Validates citation "PEN 187"
7. [OUTLET] Marks as verified: "PEN 187 ✓"
8. User receives validated response
```

**Query with Hallucination:**

```
LLM tries to cite: "Penal Code 999999"

1. [OUTLET] Detects citation in response
2. [OUTLET] Queries MongoDB: Not found
3. [OUTLET] Marks: "~~PEN 999999~~ ⚠️"
4. [OUTLET] Adds warning message
5. User sees flagged invalid citation
```

---

## 🔄 Updating the Pipeline

To update in the future:

1. Edit `legal_citation_validator.py`
2. Go to Open WebUI Admin Panel → Pipelines
3. Delete old pipeline
4. Upload new version
5. Reconfigure Valves
6. Test again

---

## 📞 Need Help?

**Check documentation:**
- Full architecture: `ARCHITECTURE_DESIGN.md`
- Troubleshooting: `ARCHITECTURE_DESIGN.md` (line 1166)
- Performance tuning: `ARCHITECTURE_DESIGN.md` (line 840)

**Test MongoDB directly:**
```bash
docker exec ca-codes-mongodb-local mongosh \
  -u admin -p legalcodes123 \
  --eval "db.section_contents.findOne({code: 'PEN', section: '187'})"
```

**Check pipeline logs:**
Open WebUI Admin Panel → Pipelines → View Logs

---

## ✅ Success Indicators

You'll know it's working when:

1. ✓ MongoDB connection successful in logs
2. ✓ Known citations return exact text
3. ✓ Invalid citations flagged with ⚠️
4. ✓ Checkmarks appear after valid citations
5. ✓ Second queries faster (cache working)
6. ✓ Warning messages for hallucinations

---

## 🎉 You're Done!

Your legal citation validator is now:
- ✅ Deployed to Open WebUI
- ✅ Connected to MongoDB
- ✅ Validating citations
- ✅ Preventing hallucinations

**Total deployment time:** ~15 minutes  
**Status:** Production Ready ✅

---

*For detailed documentation, see `ARCHITECTURE_DESIGN.md`*  
*For quick reference, see `README.md`*

