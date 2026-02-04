import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src"))
)

from tools.rag.rag_service import RAGService


class TestStructuralRetrieval(unittest.TestCase):
    def setUp(self):
        self.mock_neo4j = MagicMock()
        self.mock_qdrant = MagicMock()
        self.mock_embedder = MagicMock()
        self.mock_config = MagicMock()

        # Mock LLM and Prompts to avoid loading files or calling Ollama
        with patch("tools.rag.rag_service.ChatOllama") as MockLLM, patch.object(
            RAGService, "_init_prompts"
        ):
            self.rag = RAGService(
                self.mock_neo4j, self.mock_qdrant, self.mock_embedder, self.mock_config
            )
            self.rag.llm = MagicMock()  # Assign mock LLM instance

            # Setup LLM to return entities for extraction
            mock_response = MagicMock()
            mock_response.content = "MyClass, my_function, API_Layer"
            self.rag.llm.invoke.return_value = mock_response

    def test_structural_retrieval_flow(self):
        # Arrange
        question = "How does MyClass work?"

        # Mock Neo4j responses
        self.mock_neo4j.fuzzy_search.return_value = [
            {"id": "node1", "name": "MyClass", "type": "Class"}
        ]

        self.mock_neo4j.get_neighborhood.return_value = [
            {
                "direction": "OUT",
                "relation": "CALLS",
                "name": "my_function",
                "type": "Function",
            },
            {
                "direction": "IN",
                "relation": "INHERITS",
                "name": "BaseClass",
                "type": "Class",
            },
            {
                "direction": "OUT",
                "relation": "BELONGS_TO",
                "name": "API_Layer",
                "type": "Concept",
            },
        ]

        # Act
        context = self.rag.retrieve_context(question, strategy="STRUCTURE")

        # Assert
        # 1. Check if fuzzy search was called with extracted keywords
        # The extraction prompt mock returns "MyClass, my_function, API_Layer"
        self.mock_neo4j.fuzzy_search.assert_any_call("MyClass", limit=2)

        # 2. Check if neighborhood was fetched for the found node
        self.mock_neo4j.get_neighborhood.assert_called_with("node1")

        # 3. Check context content
        self.assertIn("--- STRUCTURAL CONTEXT (Graph) ---", context)
        self.assertIn("Entity: MyClass (Class)", context)
        self.assertIn("--[CALLS]--> my_function (Function)", context)
        self.assertIn("<--[INHERITS]-- BaseClass (Class)", context)
        self.assertIn("--[BELONGS_TO]--> API_Layer (Concept)", context)

    def test_no_structural_match(self):
        # Arrange
        question = "What is X?"
        self.mock_neo4j.fuzzy_search.return_value = []

        # Act
        context = self.rag.retrieve_context(question, strategy="STRUCTURE")

        # Assert
        self.mock_neo4j.fuzzy_search.assert_called()
        self.assertNotIn("--- STRUCTURAL CONTEXT", context)


if __name__ == "__main__":
    unittest.main()
