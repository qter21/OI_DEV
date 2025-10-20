# Open WebUI Plugin Types Comparison

## 🎯 Quick Reference: Which Plugin Type?

### Use **Filter Function** (Our Implementation) When:
- ✅ Modifying requests before they reach the LLM
- ✅ Validating or enhancing responses after generation
- ✅ Adding context to existing models
- ✅ Implementing guardrails or validation
- ✅ Pre/post-processing data

**Example**: Citation validator, content filter, context injector

### Use **Pipe Function** When:
- ✅ Creating a completely new model endpoint
- ✅ Proxying to external APIs (OpenAI, Anthropic, etc.)
- ✅ Building custom agents or assistants
- ✅ Implementing specialized model behaviors

**Example**: OpenAI proxy, custom RAG model, specialized agent

---

## 📊 Side-by-Side Comparison

| Aspect | Filter Function (Ours) | Pipe Function |
|--------|----------------------|---------------|
| **Purpose** | Modify existing model behavior | Create new models |
| **Main Method** | `inlet()` + `outlet()` | `pipe()` |
| **Type Declaration** | `self.type = "filter"` | No type needed |
| **Creates Models** | No | Yes (via `pipes()`) |
| **Processes** | Pre/post-process | Complete request handling |
| **Use With** | Any existing model | Standalone model |
| **Reference** | [Filter Docs](https://docs.openwebui.com/features/plugin/functions/filter/) | [Pipe Docs](https://docs.openwebui.com/features/plugin/functions/pipe/) |

---

## 🔧 Structure Comparison

### Filter Function (What We Built)

```python
class Pipeline:
    class Valves(BaseModel):
        config_param: str = Field(default="value")
    
    def __init__(self):
        self.type = "filter"  # REQUIRED for filters
        self.name = "Filter Name"
        self.valves = self.Valves()
    
    async def on_startup(self):
        """Initialize resources"""
        pass
    
    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Pre-process: Modify request before LLM"""
        # Add context, detect patterns, etc.
        return body
    
    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Post-process: Validate/modify response"""
        # Validate citations, add badges, etc.
        return body
```

**Reference**: https://docs.openwebui.com/features/plugin/functions/filter/

---

### Pipe Function (Alternative Approach)

```python
class Pipe:
    class Valves(BaseModel):
        API_KEY: str = Field(default="")
    
    def __init__(self):
        self.name = "Model Name"
        self.valves = self.Valves()
    
    def pipes(self):
        """Define available models (optional)"""
        return [
            {"id": "model-1", "name": "Model 1"},
            {"id": "model-2", "name": "Model 2"},
        ]
    
    def pipe(self, body: dict) -> str:
        """Handle complete request and return response"""
        # Make API call, process, return
        return "Response"
```

**Reference**: https://docs.openwebui.com/features/plugin/functions/pipe/

---

## 🎯 Our Implementation: Filter Function

### Why We Chose Filter Function

1. **Enhances Existing Models**: Works with Open WebUI's built-in RAG
2. **Two-Layer Defense**:
   - **Inlet**: Pre-injects exact legal sections
   - **Outlet**: Validates all citations after generation
3. **Non-Invasive**: Doesn't replace existing functionality
4. **Flexible**: Works with any LLM model in Open WebUI

### Architecture Flow

```
User Query: "What does Penal Code 187 say?"
    │
    ▼
┌─────────────────────────────────────────┐
│  INLET FILTER (Our Plugin)              │
│  • Detects "Penal Code 187"             │
│  • Queries MongoDB for exact text       │
│  • Injects section into context         │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Open WebUI RAG (Built-in)              │
│  • Semantic search                      │
│  • Context retrieval                    │
└─────────────┬───────────────────────────┘
              │
              ▼
        Combined Context
              │
              ▼
┌─────────────────────────────────────────┐
│  LLM Generation                         │
│  • Uses exact text + RAG context       │
│  • Generates response                   │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  OUTLET FILTER (Our Plugin)             │
│  • Extracts citations from response     │
│  • Validates against MongoDB            │
│  • Marks "PEN 187 ✓" or "PEN 999 ⚠️"  │
└─────────────────────────────────────────┘
              │
              ▼
        Validated Response
```

---

## 🔄 When to Use Each Type

### Filter Function Scenarios

✅ **Citation Validation** (Our use case)
- Verify legal code citations
- Prevent hallucination
- Add verification badges

✅ **Content Filtering**
- Remove sensitive information
- Filter inappropriate content
- Sanitize outputs

✅ **Context Injection**
- Add user profile data
- Inject company policies
- Include relevant documents

✅ **Response Enhancement**
- Add formatting
- Include citations
- Append disclaimers

### Pipe Function Scenarios

✅ **API Proxy**
- Connect to OpenAI API
- Proxy to Anthropic Claude
- Route to custom endpoints

✅ **Custom Agent**
- Specialized medical advisor
- Legal research assistant
- Code review bot

✅ **Multi-Model Orchestration**
- Chain multiple models
- Ensemble responses
- A/B testing

✅ **Proprietary Systems**
- Internal AI systems
- Custom inference engines
- Specialized processors

---

## 🚀 Migration Scenarios

### If You Started with Wrong Type

**Scenario**: Built a Pipe when you needed a Filter

**Solution**: Convert structure
```python
# From Pipe:
def pipe(self, body: dict) -> str:
    result = process(body)
    return result

# To Filter:
async def inlet(self, body: dict) -> dict:
    # Pre-process
    return body

async def outlet(self, body: dict) -> dict:
    # Post-process
    return body
```

---

## 📚 Key Differences in Practice

### Filter Function: Modifies Flow

```python
# Before Filter
User → Model → Response

# With Filter
User → INLET (modify) → Model → OUTLET (validate) → Response
```

**Characteristics**:
- Works with existing models
- Transparent to user
- Enhances model behavior
- Two points of intervention

### Pipe Function: Replaces Flow

```python
# Without Pipe
User → Built-in Model → Response

# With Pipe
User → Custom Model (pipe) → Custom Response
```

**Characteristics**:
- Creates new model
- Appears in model selector
- Complete control
- Single processing point

---

## ✅ Our Implementation Verification

### Current Structure (Correct for Filter)

```python
class Pipeline:  # ✅ Correct
    class Valves(BaseModel):  # ✅ Nested
        mongodb_uri: str = Field(...)  # ✅ Configured
    
    def __init__(self):
        self.type = "filter"  # ✅ CRITICAL for filters
        self.name = "California Legal Citation Validator"
        self.valves = self.Valves()  # ✅ self.Valves()
    
    async def on_startup(self):  # ✅ Async
        # MongoDB connection
    
    async def inlet(self, body: dict, ...) -> dict:  # ✅ Pre-process
        # Citation detection & injection
    
    async def outlet(self, body: dict, ...) -> dict:  # ✅ Post-validate
        # Citation validation
```

**Status**: ✅ Correct structure for Filter Function

---

## 📖 Documentation References

### Official Open WebUI Documentation

| Resource | URL |
|----------|-----|
| **Main Docs** | https://docs.openwebui.com/ |
| **Filter Functions** | https://docs.openwebui.com/features/plugin/functions/filter/ |
| **Pipe Functions** | https://docs.openwebui.com/features/plugin/functions/pipe/ |
| **Action Functions** | https://docs.openwebui.com/features/plugin/functions/action/ |
| **Tools** | https://docs.openwebui.com/features/plugin/functions/tools/ |
| **Valves** | https://docs.openwebui.com/features/plugin/functions/valves/ |

### Key Concepts

- **Valves**: Configuration parameters (like settings/knobs)
- **Pipeline**: The main plugin class
- **Inlet**: Pre-processing hook (filters only)
- **Outlet**: Post-processing hook (filters only)
- **Pipe**: Main processing function (pipes only)

---

## 🎓 Best Practices (Both Types)

### Common to Both

1. **Valves at Top**
   ```python
   class Pipeline:  # or Pipe
       class Valves(BaseModel):  # Always first
           pass
   ```

2. **Use self.Valves()**
   ```python
   self.valves = self.Valves()  # Not Valves()
   ```

3. **Clear Descriptions**
   ```python
   api_key: str = Field(
       default="",
       description="Clear, helpful description"
   )
   ```

4. **Error Handling**
   ```python
   try:
       result = risky_operation()
   except Exception as e:
       return {"error": str(e)}
   ```

### Filter-Specific

1. **Always Set Type**
   ```python
   self.type = "filter"  # REQUIRED
   ```

2. **Return Modified Body**
   ```python
   async def inlet(self, body: dict) -> dict:
       # ... modifications ...
       return body  # Always return body
   ```

3. **Async Methods**
   ```python
   async def inlet(self, ...):  # Must be async
   async def outlet(self, ...):  # Must be async
   ```

### Pipe-Specific

1. **Return String or Stream**
   ```python
   def pipe(self, body: dict) -> str:
       return "response"
   ```

2. **Define Models with pipes()**
   ```python
   def pipes(self):
       return [{"id": "...", "name": "..."}]
   ```

---

## 🎯 Conclusion

### Our Implementation: Filter Function ✅

**Why it's correct**:
- Enhances existing Open WebUI RAG
- Pre-injects exact legal sections (inlet)
- Post-validates citations (outlet)
- Works with any LLM model
- Non-invasive enhancement

**Alternative (Pipe Function) would mean**:
- Creating a completely new model
- No integration with RAG
- User selects as separate model
- More complex architecture

**Verdict**: Filter Function is the right choice for citation validation! ✅

---

## 📞 Quick Decision Guide

```
Do you want to CREATE a new model?
├─ YES → Use Pipe Function
│         • Proxy to external API
│         • Build custom agent
│         • Specialized model
│
└─ NO → Do you want to MODIFY existing models?
          ├─ YES → Use Filter Function ✅ (Our case)
          │         • Add validation
          │         • Inject context
          │         • Enhance responses
          │
          └─ NO → Use Action or Tool Function
                    • Add UI buttons
                    • Run background tasks
                    • Extend functionality
```

---

**Our Choice**: Filter Function ✅  
**Status**: Correctly Implemented  
**Ready**: Production Deployment  

*References: [Open WebUI Filter Docs](https://docs.openwebui.com/features/plugin/functions/filter/) | [Open WebUI Pipe Docs](https://docs.openwebui.com/features/plugin/functions/pipe/)*

