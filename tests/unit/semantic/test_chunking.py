"""
Tests for Code Chunker
"""
import pytest
from tools.code_analyzer.chunker import CodeChunker
from tools.code_analyzer.models import FileAnalysis, FunctionInfo, ClassInfo

def test_chunk_function():
    code = """
def my_func(a, b):
    '''This is a test function'''
    return a + b
"""
    file_analysis = FileAnalysis(
        file_path="test.py",
        functions=[
            FunctionInfo(
                name="my_func",
                args=["a", "b"],
                returns=None,
                docstring="This is a test function",
                start_line=1,
                end_line=3,
                body_summary="hash"
            )
        ]
    )
    
    chunker = CodeChunker()
    chunks = chunker.chunk_file(file_analysis, code.strip())
    
    assert len(chunks) == 1
    chunk = chunks[0]
    
    assert chunk.metadata["name"] == "my_func"
    assert "Type: Function" in chunk.text_content
    assert "Docstring: This is a test function" in chunk.text_content
    assert "def my_func(a, b)" in chunk.text_content

def test_chunk_class_and_methods():
    code = """
class MyClass:
    '''Class Doc'''
    def method_one(self):
        pass
"""
    file_analysis = FileAnalysis(
        file_path="classes.py",
        classes=[
            ClassInfo(
                name="MyClass",
                bases=[],
                docstring="Class Doc",
                start_line=1,
                end_line=4,
                methods=[
                    FunctionInfo(
                        name="method_one",
                        args=["self"],
                        returns=None,
                        docstring=None,
                        start_line=3,
                        end_line=4
                    )
                ]
            )
        ]
    )
    
    chunker = CodeChunker()
    chunks = chunker.chunk_file(file_analysis, code.strip())
    
    # Should have 2 chunks: 1 class, 1 method
    assert len(chunks) == 2
    
    types = [c.metadata.get("type") for c in chunks]
    assert "class" in types
    assert "method" in types
    
    method_chunk = next(c for c in chunks if c.metadata["type"] == "method")
    assert "Class: MyClass" in method_chunk.text_content
