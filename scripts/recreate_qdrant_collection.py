#!/usr/bin/env python3
"""
Recreate Qdrant collection with correct vector dimensions.

Use this script when you get "Vector dimension error" because
you switched embedding models.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qdrant_client import QdrantClient
from config.config import OllamaConfig, QdrantConfig

def recreate_collection():
    print("🗑️  Recreating Qdrant Collection...")
    
    # Load config
    qdrant_config = QdrantConfig()
    ollama_config = OllamaConfig()
    
    # Construct Qdrant URL
    qdrant_url = f"http://{qdrant_config.host}:{qdrant_config.port}"
    
    print(f"Qdrant URL: {qdrant_url}")
    print(f"Current Embedding Model: {ollama_config.model_embedding}")
    
    # Connect to Qdrant
    client = QdrantClient(url=qdrant_url)
    
    collection_name = "yaver_memory"
    
    # Check if collection exists
    try:
        collections = client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        
        if exists:
            print(f"⚠️  Collection '{collection_name}' exists. Deleting...")
            client.delete_collection(collection_name)
            print(f"✅ Deleted collection '{collection_name}'")
        else:
            print(f"ℹ️  Collection '{collection_name}' does not exist yet.")
    except Exception as e:
        print(f"❌ Error checking/deleting collection: {e}")
        return
    
    # Determine vector size based on model
    # Common models:
    # - nomic-embed-text: 768
    # - bge-m3: 1024
    # - mxbai-embed-large: 1024
    
    vector_size = 1024  # Default for bge-m3
    
    if "nomic" in ollama_config.model_embedding.lower():
        vector_size = 768
    elif "bge-m3" in ollama_config.model_embedding.lower():
        vector_size = 1024
    elif "mxbai" in ollama_config.model_embedding.lower():
        vector_size = 1024
    else:
        print(f"⚠️  Unknown model '{ollama_config.model_embedding}'. Defaulting to vector size: {vector_size}")
        print(f"    If this is wrong, edit this script or manually specify vector size.")
    
    print(f"📏 Creating collection with vector size: {vector_size}")
    
    # Create collection
    from qdrant_client import models
    
    try:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE
            )
        )
        print(f"✅ Created collection '{collection_name}' with {vector_size}-dimensional vectors")
        print(f"\n🔄 Now re-run your analysis command to populate the collection:")
        print(f"   yaver analyze /path/to/repo --project-id <id> --type deep")
    except Exception as e:
        print(f"❌ Error creating collection: {e}")

if __name__ == "__main__":
    recreate_collection()
