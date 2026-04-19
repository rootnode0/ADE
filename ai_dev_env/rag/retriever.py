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

def analyze_code(content: str) -> str:
    """Performs a lightweight analysis of the code to detect patterns."""
    patterns = []
    if "APIView" in content or "ViewSet" in content:
        patterns.append("REST Framework Views detected")
    if "permission_classes" in content:
        patterns.append("Authentication/Permissions detected")
    if "@" in content:
        patterns.append("Decorators detected (requires mocking?)")
    if ".objects." in content or "QuerySet" in content:
        patterns.append("Database queries detected")
    
    if not patterns:
        return ""
    return "[ANALYSIS] " + ", ".join(patterns)

def retrieve(project_path: str, task: str, target_files: List[str]) -> RetrievedContext:
    persist_dir = os.path.join(project_path, ".ade_index")
    client = chromadb.PersistentClient(path=persist_dir)

    collection = client.get_or_create_collection(name="code_base")

    relevant_chunks: List[str] = []
    relevant_sources: List[str] = []

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

    full_contents: Dict[str, str] = {}
    for rel_path in target_files:
        full_path = os.path.join(project_path, rel_path)
        if os.path.exists(full_path):
            if os.path.isfile(full_path):
                with open(full_path, 'r') as f:
                    content = f.read()
                    analysis = analyze_code(content)
                    if analysis:
                        full_contents[rel_path] = f"{analysis}\n{content}"
                    else:
                        full_contents[rel_path] = content
            else:
                full_contents[rel_path] = f"# NOTE: {rel_path} exists but is a directory. Please check its contents."
        else:
            # Structure Awareness: Check if it's a directory instead (e.g. views/ vs views.py)
            if rel_path.endswith('.py'):
                base_dir = rel_path[:-3]
                if os.path.isdir(os.path.join(project_path, base_dir)):
                    full_contents[rel_path] = f"# NOTE: {rel_path} does not exist, but a directory '{base_dir}/' was found. Create files inside this directory if this project uses a multi-file structure."
                else:
                    full_contents[rel_path] = "# File will be created."
            else:
                full_contents[rel_path] = "# File will be created."

    return RetrievedContext(
        chunks=relevant_chunks[:3],
        source_files=relevant_sources[:3],
        full_files=full_contents
    )
