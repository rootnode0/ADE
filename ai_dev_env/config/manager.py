import os
from pydantic import BaseModel

class ADEConfig(BaseModel):
    # Base URLs
    ollama_base_url: str = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

    # Model Mapping — aligned to locally installed models
    # Reasoning/planning  → deepseek-r1:7b  (chain-of-thought, structured output)
    # Code generation     → qwen2.5-coder:7b (strong code model)
    # Debug analysis      → deepseek-r1:7b  (same reasoning model)
    # Embedding/RAG       → nomic-embed-text
    # Lightweight tasks   → llama3.2:1b

    planner_model: str = os.getenv("ADE_MODEL_PLANNER", "deepseek-r1:7b")
    coder_model: str   = os.getenv("ADE_MODEL_CODER",   "qwen2.5-coder:7b")
    debug_model: str   = os.getenv("ADE_MODEL_DEBUG",   "deepseek-r1:7b")
    embed_model: str   = os.getenv("ADE_MODEL_EMBED",   "nomic-embed-text")
    fast_model: str    = os.getenv("ADE_MODEL_FAST",    "llama3.2:1b")

    # Hardware Limits
    num_parallel: int   = int(os.getenv("OLLAMA_NUM_PARALLEL",   "1"))
    context_length: int = int(os.getenv("OLLAMA_CONTEXT_LENGTH", "4096"))
    gpu_layers: int     = int(os.getenv("ADE_GPU_LAYERS",        "0"))    # CPU-ONLY to prevent OOM

config = ADEConfig()
