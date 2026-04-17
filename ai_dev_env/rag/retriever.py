import os
import chromadb
from pydantic import BaseModel
from typing import List, Dict

class RetrievedContext(BaseModel):
    chunks: List[str]           # Relevant code snippets
    source_files: List[str]     # Files these snippets came from
    full_files: Dict[str, str]  # Full content of the target files

def build_context_block(ctx: RetrievedContext) -> str:
    """Assembles a clean context string for injection into coder prompt."""
    block = "--- RELEVANT CODE CONTEXT ---\n"
    for i, chunk in enumerate(ctx.chunks):
        block += f"[Source: {ctx.source_files[i]}]\n{chunk}\n\n"

    block += "--- TARGET FILES (full content) ---\n"
    for path, content in ctx.full_files.items():
        block += f"[File: {path}]\n{content}\n\n"
    return block

def retrieve(project_path: str, task: str, target_files: List[str]) -> RetrievedContext:
    persist_dir = os.path.join(project_path, ".ade_index")
    client = chromadb.PersistentClient(path=persist_dir)

    # Use get_or_create so first-run (pre-index) doesn't crash
    collection = client.get_or_create_collection(name="code_base")

    relevant_chunks: List[str] = []
    relevant_sources: List[str] = []

    # Only query if collection actually has data
    if collection.count() > 0:
        query_str = f"{task} {' '.join(target_files)}"
        results = collection.query(
            query_texts=[query_str],
            n_results=min(5, collection.count())
        )
        for i, dist in enumerate(results['distances'][0]):
            if dist < 0.7:
                relevant_chunks.append(results['documents'][0][i])
                relevant_sources.append(results['metadatas'][0][i]['file'])

    # Always fetch full content of target_files
    full_contents: Dict[str, str] = {}
    for rel_path in target_files:
        full_path = os.path.join(project_path, rel_path)
        if os.path.exists(full_path):
            with open(full_path, 'r') as f:
                full_contents[rel_path] = f.read()
        else:
            full_contents[rel_path] = "# File will be created."

    return RetrievedContext(
        chunks=relevant_chunks[:3],
        source_files=relevant_sources[:3],
        full_files=full_contents
    )
