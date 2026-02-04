import sys
from pathlib import Path
import logging

# Ensure src is in path
sys.path.append(str(Path(__file__).parent / "src"))

from tools.code_analyzer.embeddings import CodeEmbedder
from config.config import OllamaConfig

def test_embeddings_auth():
    logging.basicConfig(level=logging.INFO)
    print("Testing CodeEmbedder Authentication...")
    
    # Init config (will pick up environment variables)
    config = OllamaConfig()
    print(f"Config loaded. URL: {config.base_url}, User: {config.username}, Model: {config.model_embedding}")
    
    if not config.username:
        print("WARNING: No username configured. This test might pass even if auth is broken, as it falls back to no-auth.")
    
    try:
        embedder = CodeEmbedder(config=config)
        print("Embedder initialized.")
        
        test_text = "def hello_world(): print('hello')"
        print("Attempting to embed sample text...")
        
        vector = embedder.embed_query(test_text)
        
        print(f"Success! Generated vector of length: {len(vector)}")
        if len(vector) > 0:
            print("Embedding auth verification PASSED.")
        else:
            print("Embedding auth verification FAILED (empty vector).")
            
    except Exception as e:
        print(f"Embedding auth verification FAILED with error: {e}")
        # Print full stack trace if needed, but error message is usually enough for 401
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_embeddings_auth()
