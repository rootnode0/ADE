import os
import hashlib
from typing import List
import chromadb
from chromadb.config import Settings
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

class ADEIndexer:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.project_name = os.path.basename(project_path)
        self.persist_dir = os.path.join(project_path, ".ade_index")

        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(name="code_base")

        # Initialize Embeddings (Always runs on CPU)
        self.embeddings = OllamaEmbeddings(
            model="nomic-embed-text",
            base_url="http://localhost:11434"
        )

        # Code-aware splitter: Priorities class and def boundaries
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=64,
            separators=["\nclass ", "\ndef ", "\n\n", "\n", " ", ""]
        )

    def _get_chunk_id(self, file_path: str, content: str) -> str:
        """Generate a content-addressed ID."""
        return hashlib.sha256(f"{file_path}{content}".encode()).hexdigest()[:16]

    def index_project(self) -> int:
        """Index all Python files. Returns number of new chunks added."""
        chunks_added = 0
        exclude_dirs = {'.venv', '__pycache__', 'migrations', 'node_modules', '.git'}

        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                if not file.endswith('.py'):
                    continue

                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.project_path)

                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                docs = self.splitter.split_text(content)

                for doc in docs:
                    chunk_id = self._get_chunk_id(rel_path, doc)

                    # Check if ID exists to allow incremental indexing
                    existing = self.collection.get(ids=[chunk_id])
                    if not existing['ids']:
                        self.collection.add(
                            ids=[chunk_id],
                            documents=[doc],
                            metadatas=[{"file": rel_path, "project": self.project_name}]
                        )
                        chunks_added += 1
        return chunks_added

def index_project(project_path: str) -> int:
    indexer = ADEIndexer(project_path)
    return indexer.index_project()
