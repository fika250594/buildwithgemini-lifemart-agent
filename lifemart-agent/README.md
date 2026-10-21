# LifeMart Concierge 🛒🌿

An intelligent, multi-tool everyday living and pantry assistant built on Google Agent Development Kit (ADK) and deployed to Google Cloud Agent Platform.

![LifeMart Concierge Demo](demo.gif)

---

## Overview

**LifeMart Concierge** helps households browse smart grocery and home essentials, safely filter allergens across conversations using persistent memory, calculate multi-item bundle discounts and taxes, track pantry replenishment timelines, compute distance-based delivery fees, and generate photorealistic product visuals and showcase videos.

---

## Implemented Architecture & Google Cloud Integrations

The agent is implemented in `app/agent.py` and configured with:

1. **Vertex AI Memory Bank (`PreloadMemoryTool` & `VertexAiMemoryBankService`)**
   - Automatically saves conversation sessions across turns.
   - Proactively remembers user-stated allergies (dairy, peanuts, gluten), household size, and dietary restrictions to enforce ingredient safety checks across separate sessions.

2. **Cloud Firestore Database**
   - Live inventory management (`products` collection) and order persistence (`orders` collection).
   - Functions implemented:
     - `list_products`: Query inventory filtered by category (`groceries`, `household`, `pantry`).
     - `search_products`: Search items by name, description, or tags.
     - `add_product` & `update_product_stock`: Real-time stock increments and inventory management.
     - `checkout_order`: Verifies inventory, decrements stock, and commits order confirmation records.

3. **Multimodal Image Generation (`gemini-3.1-flash-lite-image`)**
   - `generate_product_image`: Generates photorealistic product and bundle visuals in the Vertex AI `global` region.
   - Saves images to the Playground via `tool_context.save_artifact` and uploads directly to Google Cloud Storage.

4. **Showcase Video Generation (`gemini-omni-flash-preview`)**
   - `generate_item_video`: Generates short continuous showcase videos of pantry items using Google's Omni foundation model in the Vertex AI `global` region.
   - Saves video artifacts locally and publishes public MP4 assets to Cloud Storage.

5. **Google Cloud Storage (GCS)**
   - Serves as the public asset bucket for generated product images and demo videos.

6. **Agent Engine Sandbox Code Executor (`AgentEngineSandboxCodeExecutor`)**
   - Executes arbitrary sandboxed Python code for custom mathematical formulas, household consumption rates, and complex basket pricing simulations.

7. **A2UI v0.8 & Rich Display Cards**
   - Formats product listings, order summaries, and cart totals into clean, responsive A2UI cards (`Card`, `Column`, `Row`, `Text`, `Image`).
   - Wired via `DirectJsonPromptGenerator` and `a2ui_callback`.

8. **Google Maps Geocoding & Places Tools**
   - `geocode_address`: Converts delivery addresses into coordinates.
   - `calculate_shipping_fee_by_distance`: Computes distance-based delivery tiers (Hyper-Local, Regional Metro, Extended Delivery).
   - `find_nearby_places`: Searches for nearby grocery hubs and supermarkets.

9. **External Benchmark Price Comparison**
   - `fetch_global_market_products`: Compares internal catalog items with external marketplace listings.

---

## Project Structure

```
.
├── app/
│   ├── __init__.py          # App initialization
│   ├── agent.py             # Root agent, tools, memory callback, and A2UI wiring
│   └── a2ui_utils.py        # A2UI after_model_callback handler
├── frontend/
│   ├── static/
│   │   └── index.html       # Chat web frontend with custom emerald pantry theme & A2UI renderer
│   ├── main.py              # FastAPI A2A proxy server
│   └── requirements.txt     # Frontend proxy dependencies
├── agents-cli-manifest.yaml # Agent Engine runtime configuration
├── pyproject.toml           # Agent dependencies (ADK, GenAI SDK, Firestore, A2UI)
├── demo.gif                 # Screen recording demo of the chat UI
└── README.md
```

---

## Local Development & Setup

### Prerequisites

- Python 3.11+
- `uv` package manager or `pip`
- Google Cloud SDK (`gcloud`) authenticated to a GCP project

### 1. Running the Agent in Local ADK Playground

Install dependencies and start the ADK Web playground:

```bash
# Set Google Cloud environment variables
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT="<YOUR_GCP_PROJECT_ID>"
export GOOGLE_CLOUD_LOCATION="global"

# Start ADK Web with memory bank
uv run adk web . --port 8000 --reload_agents
```

### 2. Running the Custom Chat Frontend

Run the FastAPI A2A proxy and chat UI:

```bash
cd frontend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_NUMBER>/locations/<LOCATION>/reasoningEngines/<ENGINE_ID>"
export AGENT_DIRECTORY="app"
python main.py
```

---

## Deploying

### Deploy Agent to Agent Engine
```bash
agents-cli deploy --project <YOUR_GCP_PROJECT_ID>
```

### Deploy Frontend to Cloud Run
```bash
cd frontend
gcloud run deploy lifemart-frontend \
  --source . \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="<YOUR_AGENT_RESOURCE_NAME>",AGENT_DIRECTORY="app"
```
