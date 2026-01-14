# Membership Impact Analytical Dashboard

A multi-agent AI system that provides analytical insights into membership changes by combining real-time BigQuery data, contextual PDF rulebook information, and AI-powered reasoning using Google's Gemini models.

## 🎯 Features

- **Multi-Agent Architecture**: Specialized agents for data querying, RAG retrieval, and orchestration
- **Real-Time Analytics**: Query BigQuery for membership and provider configuration data
- **Contextual Reasoning**: Semantic search through PDF rulebooks using FAISS vector embeddings
- **Interactive Dashboard**: Gradio-based UI with chat interface and visual analytics
- **Dual Agent Framework**: Support for both SDK-based and ADK-based orchestrators
- **Intelligent Analysis**: LLM-powered explanations with rulebook context

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Gradio Dashboard UI                      │
│  ┌──────────────┐              ┌──────────────────────┐   │
│  │ Chat Interface│              │ Analytics Panel      │   │
│  └──────┬───────┘              └──────────────────────┘   │
└─────────┼───────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│              Orchestrator Agent (SDK or ADK)                 │
│  • Query parsing & org code extraction                       │
│  • Agent coordination                                        │
│  • Signal computation                                        │
│  • Response generation                                       │
└─────────┬───────────────────────────────────────────────────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌─────────┐  ┌─────────┐
│BigQuery │  │ PDF RAG │
│ Agent   │  │ Agent   │
└────┬────┘  └────┬────┘
     │            │
     ▼            ▼
┌─────────┐  ┌─────────┐
│BigQuery │  │  FAISS  │
│Database │  │  Index  │
└─────────┘  └─────────┘
```

### Components

1. **Orchestrator Agent** (`app/orchestrator_agent.py` or `app/adk_orchestrator.py`)
   - Coordinates all agents
   - Computes analytical signals (movement, churn, retroactive terminations)
   - Generates LLM responses with context

2. **BigQuery Agent** (`app/bigquery_agent.py`)
   - Queries membership data for organizations
   - Retrieves provider configuration changes
   - Connects to Google BigQuery

3. **PDF RAG Agent** (`app/pdf_rag_agent.py`)
   - Extracts text from PDF rulebooks
   - Builds FAISS vector index using Vertex AI embeddings
   - Performs semantic search for relevant context

4. **Dashboard** (`app/dashboard.py`)
   - Gradio-based UI
   - Chat interface for user queries
   - Visual analytics with charts and metrics

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Google Cloud Project with:
  - BigQuery API enabled
  - Vertex AI API enabled (for embeddings)
  - Service account with BigQuery read permissions
- Google AI API key (for Gemini models)

### Installation

1. **Clone the repository** (if applicable) or navigate to the project directory:
   ```bash
   cd /path/to/AI_POC
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   
   Create a `.env` file in the project root:
   ```bash
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_CLOUD_REGION=us-central1
   GOOGLE_AI_API_KEY=your-api-key
   USE_ADK=false  # Set to 'true' to use ADK orchestrator
   ```

5. **Set up Google Cloud authentication**:
   ```bash
   gcloud auth application-default login
   ```

6. **Prepare PDF rulebook**:
   - Place your PDF rulebook in `data/` directory
   - Default: `data/Membership_Impact_Rulebook_v3_Aligned_to_BigQuery.pdf`

### Running the Dashboard

**Option 1: Using the shell script**:
```bash
./run_dashboard.sh
```

**Option 2: Direct Python execution**:
```bash
source .venv/bin/activate
python app/dashboard.py
```

The dashboard will start on `http://localhost:7860` (or the next available port).

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GOOGLE_CLOUD_PROJECT` | Your GCP project ID | Yes | - |
| `GOOGLE_CLOUD_REGION` | GCP region | No | `us-central1` |
| `GOOGLE_AI_API_KEY` | Google AI API key for Gemini | Yes | - |
| `USE_ADK` | Use ADK orchestrator instead of SDK | No | `false` |

### Model Configuration

Edit `app/config.py` to change models:
- `chat_model`: LLM model (default: `gemini-2.5-flash`)
- `embedding_model`: Embedding model (default: `text-embedding-004`)

### BigQuery Dataset

Default dataset: `membership_analytics`

Expected tables:
- Membership data table
- Provider configuration changes table

## 📖 Usage

### Using SDK-Based Orchestrator (Default)

The SDK-based orchestrator is the default and proven implementation:

```bash
# Ensure USE_ADK is not set or set to false
export USE_ADK=false
python app/dashboard.py
```

**Features**:
- Direct method calls
- Custom orchestration logic
- Fully tested and stable

### Using ADK-Based Orchestrator

Switch to ADK orchestrator for framework-based agent execution:

```bash
export USE_ADK=true
python app/dashboard.py
```

**Features**:
- ADK framework patterns
- Built-in tool management
- Session-based execution
- Event-based processing

**Note**: ADK orchestrator automatically falls back to SDK if execution fails.

### Example Queries

1. **Basic membership analysis**:
   ```
   Give me analysis for S5660_P801
   ```

2. **Membership drop investigation**:
   ```
   Why did membership drop for S4802_P141?
   ```

3. **Membership increase analysis**:
   ```
   Explain the membership increase for S5660_P801
   ```

### Response Format

The system provides:
- **Text Analysis**: 4 concise paragraphs (2-3 lines each)
  - Direct answer with key finding
  - Main cause/reason based on data signals
  - Reasoning from rulebook framework
  - Key insight/conclusion
- **Visual Analytics**: Charts and metrics in the right panel
  - Key metrics (prior/current members, net change)
  - Member movement breakdown
  - Analytical signals

## 📁 Project Structure

```
AI_POC/
├── app/
│   ├── dashboard.py              # Gradio UI and main entry point
│   ├── orchestrator_agent.py    # SDK-based orchestrator
│   ├── adk_orchestrator.py      # ADK-based orchestrator
│   ├── adk_tools.py             # ADK FunctionTools
│   ├── bigquery_agent.py         # BigQuery data queries
│   ├── pdf_rag_agent.py         # PDF RAG with FAISS
│   ├── prompts.py               # LLM prompts and templates
│   └── config.py                # Configuration management
├── data/
│   └── Membership_Impact_Rulebook_v3_Aligned_to_BigQuery.pdf
├── scripts/
│   └── build_membership_impact_from_cms.py
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (create this)
├── run_dashboard.sh             # Dashboard launcher script
├── setup.sh                     # Setup script
├── README.md                    # This file
└── INTEGRATION_GUIDE.md         # Detailed integration documentation
```

## 🔧 Troubleshooting

### Common Issues

1. **"Missing key inputs argument" Error**:
   - Ensure `GOOGLE_AI_API_KEY` is set in `.env` or environment
   - Check that the API key is valid

2. **"Event loop is closed" Error (ADK)**:
   - This is a non-critical cleanup warning
   - Events are processed successfully before cleanup
   - The application continues normally

3. **BigQuery Permission Errors**:
   - Verify service account has BigQuery read permissions
   - Check that BigQuery API is enabled
   - Ensure dataset and tables exist

4. **Model Not Found Errors**:
   - Verify Vertex AI API is enabled
   - Check model name in `config.py`
   - Ensure billing is enabled for your GCP project

5. **PDF RAG Not Working**:
   - Verify PDF file exists in `data/` directory
   - Check that Vertex AI embeddings API is accessible
   - Ensure FAISS index is built (happens automatically on first use)

### Debugging

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check which orchestrator is being used:
- Look for console output: `✅ Using ADK Orchestrator Agent` or `✅ Using SDK Orchestrator Agent (default)`

## 🧪 Testing

### Test SDK Orchestrator

```python
from app.orchestrator_agent import OrchestratorAgent
from app.config import Config

config = Config()
agent = OrchestratorAgent(config)
result = agent.run("Give me analysis for S5660_P801")
print(result['text'])
```

### Test ADK Orchestrator

```python
from app.adk_orchestrator import ADKOrchestratorAgent
from app.config import Config

config = Config()
agent = ADKOrchestratorAgent(config)
result = agent.run("Give me analysis for S5660_P801")
print(result['text'])
```

## 📚 Dependencies

Key dependencies (see `requirements.txt` for full list):
- `gradio`: Dashboard UI
- `google-cloud-aiplatform`: Vertex AI integration
- `google-cloud-bigquery`: BigQuery queries
- `google-adk`: Agent Development Kit (optional, for ADK orchestrator)
- `faiss-cpu`: Vector similarity search
- `pypdf`: PDF text extraction
- `plotly`: Interactive charts
- `pandas`: Data manipulation

## 🔄 SDK vs ADK Comparison

| Feature | SDK-Based | ADK-Based |
|---------|-----------|-----------|
| **Pattern** | Custom Python class | Framework-based |
| **Execution** | Direct method calls | Event-based via Runner |
| **Tools** | Custom agent classes | ADK FunctionTools |
| **Session** | Manual management | Built-in session service |
| **Status** | ✅ Production-ready | ✅ Implemented, tested |
| **Fallback** | N/A | Falls back to SDK on error |

## 📝 License

[Add your license information here]

## 🤝 Contributing

[Add contribution guidelines if applicable]

## 📧 Support

[Add support contact information if applicable]

---

For detailed integration documentation, see [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md).
