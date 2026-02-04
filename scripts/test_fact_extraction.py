import sys
from pathlib import Path
import logging

# Ensure src is in path
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from tools.rag.fact_extractor import FactExtractor
    from agents import agent_base
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# FORCE LOCAL CONFIG FOR TESTING - REMOVED
# def mock_get_config():
#     return {
#         'OLLAMA_BASE_URL': 'http://localhost:11434',
#         'OLLAMA_MODEL_GENERAL': 'llama3.2:3b-instruct-q4_K_M',
#         # 'OLLAMA_MODEL_GENERAL': 'qwen2.5-coder:7b-instruct-q4_K_M',
#         'OLLAMA_MODEL_CODE': 'qwen2.5-coder:7b-instruct-q4_K_M'
#     }

# Patch the get_config_dict in agent_base to bypass broken user config
# agent_base.get_config_dict = mock_get_config

def test_extraction():
    logging.basicConfig(level=logging.INFO)
    
    print("Initializing FactExtractor...")
    try:
        extractor = FactExtractor()
    except Exception as e:
        print(f"Failed to init extractor (likely missing API key): {e}")
        return

    sample_code = """
    class AuthenticationManager:
        \"\"\"
        Handles user login and JWT token generation.
        Uses Redis for session storage.
        \"\"\"
        def login(self, user, password):
            # Validate credentials against Postgres DB
            pass
    """
    
    print("Extracting facts from sample code...")
    try:
        facts = extractor.extract_facts(sample_code)
        
        print(f"Found {len(facts)} facts:")
        for f in facts:
            print(f" - ({f.subject}) -[{f.predicate}]-> ({f.object})")
            
    except Exception as e:
        print(f"Extraction failed: {e}")

if __name__ == "__main__":
    test_extraction()
