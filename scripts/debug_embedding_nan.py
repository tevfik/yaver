import sys
from pathlib import Path
import logging

# Ensure src is in path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from tools.code_analyzer.embeddings import CodeEmbedder
from config.config import OllamaConfig

def test_nan_repro():
    logging.basicConfig(level=logging.WARNING)
    
    config = OllamaConfig()
    print(f"Loaded config. Model: {config.model_embedding}")
    
    embedder = CodeEmbedder(config=config)
    
    # 1. Repetitive Text (known NaN trigger)
    print("\n--- Test 3a: Repetitive Text (1500 chars) ---")
    repetitive_text = "Content " * 200 # ~1600 chars
    try:
        vec = embedder.embed_query(repetitive_text)
        print(f"Success. Vector len: {len(vec)}")
    except Exception as e:
        print(f"Failed with repetitive text: {e}")

    # 2. Non-Repetitive Large Text
    print("\n--- Test 3b: Unique Large Text (2000 chars) ---")
    # Generate pseudo-unique text
    words = ["apple", "banana", "cherry", "date", "elderberry", "fig", "grape"]
    unique_text = " ".join([f"{w}_{i}" for i, w in enumerate(words * 300)]) # ~2000 chars
    try:
        vec = embedder.embed_query(unique_text)
        print(f"Success. Vector len: {len(vec)}")
    except Exception as e:
        print(f"Failed with unique text: {e}")

if __name__ == "__main__":
    test_nan_repro()
