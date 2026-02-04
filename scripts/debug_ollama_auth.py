from langchain_ollama import ChatOllama
import base64
import os
import logging

logging.basicConfig(level=logging.DEBUG)

def test_auth():
    print("Testing ChatOllama auth headers...")
    
    username = "admin"
    password = "t0751234k!2" 
    
    auth_str = f"{username}:{password}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    headers = {'Authorization': f"Basic {b64_auth}"}
    
    try:
        print("Trying with client_kwargs...")
        llm = ChatOllama(
            model="mistral",
            base_url="https://ollama.bezg.in",
            client_kwargs={'headers': headers}
        )
        print("LLM initialized with client_kwargs.")
        llm.invoke("hello")
    except TypeError as e:
        print(f"ChatOllama does not accept client_kwargs: {e}")
    except Exception as e:
        print(f"Request failed with client_kwargs: {e}")

    # try:
    #     llm = ChatOllama(
    #         model="mistral",
    #         base_url="https://ollama.bezg.in",
    #         headers=headers
    #     )


if __name__ == "__main__":
    test_auth()
