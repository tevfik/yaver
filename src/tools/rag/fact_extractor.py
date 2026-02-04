"""
Information Extractor Component
Uses LLM to extract structured facts (triples) from code comments and documentation.
Based on IntelligentAgent's extractor.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

import logging
import json
from agents.agent_base import create_llm

logger = logging.getLogger(__name__)

class FactTriple(BaseModel):
    """A single fact triple (Subject -> Predicate -> Object)"""
    subject: str = Field(description="The entity that is the subject of the fact")
    predicate: str = Field(description="The relationship or property (e.g., IS_A, HAS_PROPERTY, CALLED_BY)")
    object: str = Field(description="The entity or value that is the object of the fact")
    confidence: float = Field(default=1.0, description="Confidence score between 0.0 and 1.0")

class ExtractionResult(BaseModel):
    """Result of the extraction process"""
    triples: List[FactTriple] = Field(description="List of extracted fact triples")

class FactExtractor:
    """
    Extracts structured information from text using LLM.
    """
    
    SYSTEM_PROMPT = """You are an expert Code Knowledge Graph Engineer.
Your task is to extract structured knowledge from the given text (code comments, documentation, or user queries) in the form of RDF-style triples (Subject, Predicate, Object).

Guidelines:
1. **Entities**: Identify key entities (classes, functions, modules, libraries, concepts, architectural patterns).
2. **Relationships**: Identify relationships between them. Use standard predicates where possible (e.g., USES, IMPLEMENTS, DEPLOYS_TO, CONFIGURES, DEPENDS_ON).
3. **Granularity**: Break down complex info into atomic facts.
4. **Normalization**: Use consistent naming.
5. **Relevance**: Extract facts useful for software understanding.
6. **IMPORTANT**: Every triple MUST have non-empty subject, predicate, AND object fields. Never omit any field.

Example Input: "The AuthModule uses JWT tokens for validating users across the generic API."
Example Output:
- (AuthModule) -[USES]-> (JWT Tokens)
- (AuthModule) -[VALIDATES]-> (Users)
- (AuthModule) -[PAR_OF]-> (Generic API)
"""

    def __init__(self):
        self.llm = create_llm(model_type="extraction")
        self.parser = PydanticOutputParser(pydantic_object=ExtractionResult)
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("user", "Extract facts from this text:\n\n{text}\n\n{format_instructions}")
        ])

    def _validate_and_filter_triples(self, raw_data: Dict[str, Any]) -> List[FactTriple]:
        """
        Validate triples from raw LLM output, filtering out incomplete ones.
        
        Args:
            raw_data: Raw dict from LLM (potentially with incomplete fields)
            
        Returns:
            List of valid FactTriple objects
        """
        valid_triples = []
        
        if "triples" not in raw_data:
            return valid_triples
            
        for triple_data in raw_data["triples"]:
            # Validate that all required fields exist and are non-empty
            # Convert to string first in case LLM returns non-string types (int, float, etc.)
            subject_raw = triple_data.get("subject")
            predicate_raw = triple_data.get("predicate")
            obj_raw = triple_data.get("object")
            
            subject = str(subject_raw).strip() if subject_raw is not None else ""
            predicate = str(predicate_raw).strip() if predicate_raw is not None else ""
            obj = str(obj_raw).strip() if obj_raw is not None else ""
            
            try:
                confidence = float(triple_data.get("confidence", 1.0))
            except (ValueError, TypeError):
                confidence = 1.0
            
            # Skip if any required field is missing or empty
            if not subject or not predicate or not obj:
                logger.debug(f"Skipping incomplete triple: subject={subject}, predicate={predicate}, object={obj}")
                continue
            
            try:
                valid_triple = FactTriple(
                    subject=subject,
                    predicate=predicate,
                    object=obj,
                    confidence=confidence
                )
                valid_triples.append(valid_triple)
            except Exception as e:
                logger.debug(f"Failed to create FactTriple: {e}")
                continue
        
        return valid_triples

    def extract_facts(self, text: str) -> List[FactTriple]:
        """
        Extract facts from text.
        
        Args:
            text: The input text to analyze
            
        Returns:
            List of extracted FactTriple objects
        """
        if not text or len(text.strip()) < 10:
            return []
            
        try:
            # Get the LLM response as a string
            chain = self.prompt | self.llm
            
            response = chain.invoke({
                "text": text,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # Parse the response as JSON manually
            try:
                response_text = response.content if hasattr(response, 'content') else str(response)
                raw_data = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from the response if it contains extra text
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    raw_data = json.loads(json_match.group())
                else:
                    logger.error(f"Could not parse JSON from response: {response_text[:200]}")
                    return []
            
            # Validate and filter incomplete triples
            valid_triples = self._validate_and_filter_triples(raw_data)
            
            # Filter low confidence results
            filtered_triples = [t for t in valid_triples if t.confidence > 0.6]
            
            logger.info(f"Extracted {len(filtered_triples)} facts from text (validated {len(valid_triples)} triples)")
            return filtered_triples
            
        except Exception as e:
            logger.error(f"Error extracting facts: {e}")
            # Fallback or simple extraction could go here
            return []

