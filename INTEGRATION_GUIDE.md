# Membership Impact Analytical Dashboard - Integration Guide

## Overview

This document explains how the multi-agent system integrates various components to provide analytical insights into membership changes. It covers the integration patterns, data flow, and interaction between components.

## Integration Architecture

### Component Integration Map

```
┌──────────────────────────────────────────────────────────────────┐
│                         Integration Layer                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │   Gradio UI  │◄────►│ Orchestrator │◄────►│  BigQuery    │  │
│  │  (Dashboard) │      │    Agent     │      │    Agent     │  │
│  └──────────────┘      │              │      └──────────────┘  │
│                        │              │                         │
│                        │              │◄────►│  PDF RAG      │  │
│                        │              │      │    Agent      │  │
│                        │              │      └──────────────┘  │
│                        │              │                         │
│                        │              │◄────►│  Vertex AI    │  │
│                        └──────────────┘      │  (Gemini)     │  │
│                                               └──────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

## Integration Details

### 1. UI to Orchestrator Integration

**Location**: `app/dashboard.py` → `app/orchestrator_agent.py`

**Integration Pattern**: Direct function call

**Code Flow**:
```python
# In dashboard.py
def chat_with_agent(message, history):
    response = agent.run(message)  # OrchestratorAgent instance
    # Process response...
```

**Data Exchange**:
- **Input**: User query string
- **Output**: Dictionary with:
  - `text`: LLM-generated analysis
  - `data`: Membership metrics
  - `signals`: Analytical signals
  - `org_cd`: Organization code

**Integration Points**:
- Instantiated once at startup: `agent = OrchestratorAgent(config)`
- Called synchronously for each user query
- Error handling in `chat_with_agent()` wrapper

### 2. Orchestrator to BigQuery Agent Integration

**Location**: `app/orchestrator_agent.py` → `app/bigquery_agent.py`

**Integration Pattern**: Agent composition (has-a relationship)

**Initialization**:
```python
# In OrchestratorAgent.__init__()
self.bq_agent = BigQueryAgent(project_id, dataset="membership_analytics")
```

**Integration Flow**:
```python
# In OrchestratorAgent.run()
# Step 2: Get facts from BigQuery
membership_data = self.bq_agent.get_membership_data(org_cd)
provider_changes = self.bq_agent.get_provider_changes(org_cd)
```

**Data Exchange**:
- **Input**: Organization code (string)
- **Output**: 
  - `membership_data`: Dictionary with membership metrics
  - `provider_changes`: List of dictionaries with configuration changes

**Error Handling**:
- BigQuery errors are caught and logged
- Returns None if query fails
- Orchestrator handles None gracefully

**Integration Characteristics**:
- Synchronous calls
- Direct method invocation
- No async/threading needed (single user queries)

### 3. Orchestrator to PDF RAG Agent Integration

**Location**: `app/orchestrator_agent.py` → `app/pdf_rag_agent.py`

**Integration Pattern**: Agent composition with intelligent query building

**Initialization**:
```python
# In OrchestratorAgent.__init__()
self.rag_agent = PDFRAGAgent(config)
```

**Integration Flow**:
```python
# In OrchestratorAgent.run()
# Step 3: Build RAG query based on signals
rag_query = "membership drop explanation rules provider configuration changes..."
if signals.get('retro_dominant'):
    rag_query += " retro_term_mem_count retroactive terminations"
# ... more signal-based query expansion

rules_chunks = self.rag_agent.retrieve(rag_query, top_k=4)
rules_text = "\n\n---\n\n".join(rules_chunks)
```

**Data Exchange**:
- **Input**: 
  - Query string (dynamically built from signals)
  - `top_k=4` (number of chunks to retrieve)
- **Output**: 
  - List of rulebook text chunks (strings)
  - Joined into `rules_text` for LLM prompt

**Intelligent Query Building**:
The orchestrator builds the RAG query based on computed signals:
- Base query: Generic membership analysis terms
- Conditional additions based on signals:
  - Retroactive terminations → Add retro terms
  - Network ID changes → Add network mapping terms
  - File ID changes → Add file mapping terms
  - Plan carrier changes → Add carrier mapping terms

**Integration Characteristics**:
- Synchronous calls
- Query built dynamically based on data signals
- Context-aware retrieval (not generic search)

### 4. Orchestrator to LLM Integration

**Location**: `app/orchestrator_agent.py` → Vertex AI (via `app/prompts.py`)

**Integration Pattern**: Prompt engineering with structured data injection

**Initialization**:
```python
# In OrchestratorAgent.__init__()
vertexai.init(project=config.project_id, location=config.region)
self.llm = GenerativeModel(config.chat_model)
```

**Integration Flow**:
```python
# In OrchestratorAgent.run()
# Step 5: Generate LLM response
prompt = build_response_prompt(
    membership_for_prompt,  # Structured data
    signals,                 # Computed signals
    rules_text,              # RAG context
    len(provider_changes),   # Change count
    query                    # Original user query
)

response = self.llm.generate_content(
    SYSTEM_PROMPT + "\n\n" + prompt
)
generated_text = response.text.strip()
```

**Data Exchange**:
- **Input**: 
  - `SYSTEM_PROMPT`: Role definition and analytical approach
  - `prompt`: Data-rich prompt with:
    - Membership metrics
    - Analytical signals
    - Rulebook context (RAG chunks)
    - Provider changes count
    - User query
- **Output**: Generated text response (string)

**Prompt Construction** (`app/prompts.py`):
```python
def build_response_prompt(membership_data, signals, rules_text, 
                         provider_changes_count, query):
    # Constructs structured prompt with:
    # - Question
    # - Membership metrics (formatted)
    # - Member movement details
    # - Analytical signals (computed)
    # - Rulebook context (RAG)
    # - Provider changes count
    # - Task instructions
```

**Integration Characteristics**:
- Synchronous API calls
- Structured prompt with clear sections
- Error handling with fallback response
- Model configuration from `app/config.py`

### 5. BigQuery Integration Details

**Technology**: Google Cloud BigQuery Python Client

**Authentication**: Application Default Credentials
```bash
gcloud auth application-default login
```

**Connection**:
```python
# In BigQueryAgent.__init__()
self.client = bigquery.Client(project=project_id)
```

**Query Pattern**:
- Parameterized queries for security
- Single-row results (LIMIT 1)
- Dictionary return format

**Tables Used**:
1. **membership_impact**:
   - Columns: `org_cd`, `mbr_cnt_x202511m11_prd`, `mbr_cnt_x202512m12_prd`, 
     `dropped_mbr_cnt`, `new_mbr_cnt`, `retro_term_mem_count`, etc.
   
2. **provider_config_changes**:
   - Columns: `org_cd`, `key_type`, `keys_changed`, `test_type`, etc.

**Error Handling**:
- Exceptions caught and logged
- Returns None on error
- Orchestrator validates None before use

### 6. PDF RAG Integration Details

**Technology Stack**:
- **FAISS**: Vector similarity search
- **Vertex AI Embeddings**: Text embedding model
- **pypdf**: PDF text extraction

**Index Management**:
- Built on first use
- Cached in `app/.pdf_rag_index/`
- Auto-rebuild if index missing

**Embedding Process**:
1. Extract text from PDF
2. Chunk text (paragraph-based splitting)
3. Embed each chunk
4. Build FAISS index (cosine similarity)
5. Store index and chunks

**Retrieval Process**:
1. Embed user query
2. Search FAISS index (top-k)
3. Return relevant chunks

**Integration with Orchestrator**:
- Query built from signals (not user query directly)
- Context-aware retrieval
- Top-4 chunks passed to LLM

### 7. Configuration Integration

**Location**: `app/config.py`

**Integration Pattern**: Dependency injection

**Usage**:
```python
# Initialize config
config = Config()

# Pass to agents
orchestrator = OrchestratorAgent(config)
rag_agent = PDFRAGAgent(config)
```

**Configuration Sources**:
- Environment variables (`.env` file)
- Default values (region, model names)
- Validation (project ID required)

**Model Configuration**:
- `chat_model`: `gemini-2.5-flash`
- `embedding_model`: `text-embedding-004`
- `project_id`: From `GOOGLE_CLOUD_PROJECT`
- `region`: From `GOOGLE_CLOUD_REGION` or default

## Data Flow Integration

### Complete Integration Flow

```
User Query Entry
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ 1. Dashboard (Gradio UI)                                │
│    - Receives user query                                │
│    - Calls chat_with_agent()                            │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Orchestrator Agent                                   │
│    - extract_org_cd() → Parse organization code         │
│    - Coordinate agents                                  │
└───────────────────┬─────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌──────────────┐      ┌──────────────────┐
│ 3a. BigQuery │      │ 3b. PDF RAG      │
│    Agent     │      │    Agent         │
│              │      │                  │
│ - Query      │      │ - Build query    │
│   membership │      │   from signals   │
│   data       │      │ - Retrieve       │
│ - Query      │      │   rulebook       │
│   provider   │      │   chunks         │
│   changes    │      │                  │
└──────┬───────┘      └────────┬─────────┘
       │                       │
       └───────────┬───────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Signal Computation (Orchestrator)                    │
│    - compute_signals()                                  │
│    - Calculate metrics, patterns, indicators            │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Prompt Construction (prompts.py)                     │
│    - build_response_prompt()                            │
│    - Combine: data + signals + rulebook + query         │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 6. LLM Generation (Vertex AI)                           │
│    - SYSTEM_PROMPT + data prompt                        │
│    - Generate 4-paragraph analytical response           │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 7. Response Processing (Orchestrator)                   │
│    - Format response                                    │
│    - Return structured data                             │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 8. UI Display (Dashboard)                               │
│    - Format metrics for display                         │
│    - Generate charts                                    │
│    - Display in chatbot                                 │
└─────────────────────────────────────────────────────────┘
```

## Signal-Driven Integration Pattern

A key integration pattern is **signal-driven RAG query building**:

1. **Compute Signals First**: Orchestrator computes signals from BigQuery data
2. **Build Context-Aware Query**: RAG query is built based on signals
3. **Retrieve Relevant Context**: Only relevant rulebook sections retrieved
4. **Inject into LLM**: Rulebook context included in prompt

This pattern ensures:
- Relevant rulebook sections are retrieved
- LLM receives contextual information
- No generic/irrelevant context

## Error Handling Integration

### Integration Error Flow

```
Component Error
    │
    ├─> BigQuery Error
    │   └─> Returns None
    │       └─> Orchestrator validates
    │           └─> Returns error message
    │
    ├─> RAG Error
    │   └─> Returns empty list
    │       └─> Orchestrator uses empty rules_text
    │           └─> LLM works without rulebook context
    │
    └─> LLM Error
        └─> Exception caught
            └─> Enhanced fallback response
                └─> System remains functional
```

### Fallback Mechanisms

1. **LLM Fallback**: Enhanced analytical response without LLM
2. **Embedding Fallback**: `text-embedding-004` if `gemini-embedding-001` fails
3. **Data Validation**: Safe integer conversion for None values
4. **Empty Context**: System works with empty rulebook context

## Integration Testing Points

### Key Integration Points to Test

1. **UI → Orchestrator**:
   - Query format handling
   - Response formatting
   - Error display

2. **Orchestrator → BigQuery**:
   - Organization code extraction
   - Query execution
   - Data validation

3. **Orchestrator → RAG**:
   - Signal-based query building
   - Chunk retrieval
   - Context formatting

4. **Orchestrator → LLM**:
   - Prompt construction
   - Response generation
   - Error handling

5. **End-to-End**:
   - Complete query flow
   - Data accuracy
   - Response quality

## Performance Integration Considerations

### Caching Strategy

1. **RAG Index**: Built once, reused
2. **Config**: Instantiated once, shared
3. **Agents**: Instantiated once at startup

### Optimization Points

1. **RAG Query Building**: Dynamic, signal-based (efficient)
2. **BigQuery Queries**: Single-row, parameterized (fast)
3. **LLM Prompts**: Structured, concise (efficient)
4. **Response Formatting**: Minimal processing (fast)

## Security Integration

### Authentication Flow

1. **GCP Authentication**: Application Default Credentials
2. **BigQuery Access**: Project-level permissions
3. **Vertex AI Access**: Project-level permissions
4. **No Credentials in Code**: All via environment/auth

### Data Security

1. **Parameterized Queries**: SQL injection prevention
2. **Environment Variables**: Sensitive data isolation
3. **No Data Storage**: No persistent storage of user data
4. **Error Messages**: No sensitive data exposure

## Monitoring Integration Points

### Key Metrics to Monitor

1. **BigQuery**: Query latency, error rate
2. **RAG**: Retrieval relevance, index size
3. **LLM**: Response time, token usage, error rate
4. **Orchestrator**: End-to-end latency
5. **UI**: User interactions, error rates

### Logging Points

- BigQuery errors (console)
- RAG index building (console)
- LLM errors (console + fallback)
- Orchestrator errors (console)

## Deployment Integration

### Deployment Flow

1. **Environment Setup**: `.env` file configuration
2. **Dependencies**: `requirements.txt` installation
3. **GCP Authentication**: `gcloud auth application-default login`
4. **RAG Index**: Auto-built on first run
5. **Dashboard Launch**: `python app/dashboard.py`

### Integration Dependencies

- GCP Project with BigQuery tables
- Vertex AI API enabled
- Authentication configured
- PDF rulebook in `data/` directory
- Python virtual environment

## Summary

The integration is built on:
- **Composition Pattern**: Agents composed in orchestrator
- **Dependency Injection**: Config passed to components
- **Signal-Driven Design**: RAG queries built from signals
- **Structured Prompts**: Data injected into LLM prompts
- **Error Resilience**: Fallbacks at each integration point
- **Clean Separation**: Each component has clear responsibilities

This architecture enables:
- Modular development
- Easy testing
- Flexible updates
- Scalable design
- Maintainable codebase
