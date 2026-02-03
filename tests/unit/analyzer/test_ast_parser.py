from tools.code_analyzer.ast_parser import ASTParser
from tools.code_analyzer.models import FunctionInfo, ClassInfo

def test_parse_simple_file(sample_repo_path):
    """Test parsing the main.py from sample repo"""
    parser = ASTParser()
    main_py = sample_repo_path / "main.py"
    
    result = parser.parse_file(main_py, sample_repo_path)
    
    assert result is not None
    assert result.file_path == "main.py"
    assert len(result.functions) == 1 # 'hello'
    assert len(result.classes) == 1 # 'DemoProcessor'
    
    # Check Function
    hello_func = result.functions[0]
    assert hello_func.name == "hello"
    
    # Check Class
    demo_class = result.classes[0]
    assert demo_class.name == "DemoProcessor"
    assert len(demo_class.methods) == 2 # __init__, process
    
    # Check Method
    process_method = [m for m in demo_class.methods if m.name == "process"][0]
    assert "data" in process_method.args

def test_parse_broken_file(temp_workspace):
    """Test parsing a file with syntax error"""
    broken_file = temp_workspace / "broken.py"
    broken_file.write_text("def broken(: print('hi')") # Syntax Error
    
    parser = ASTParser()
    # It should not crash, but return None or a partial result? 
    # My implementation explicitly catches Exception and returns None with log error
    
    # We expect this might fail if parser catches logic error. 
    # But SyntaxError in ast.parse raises SyntaxError, which is Exception.
    # So it should return None.
    
    # However, ASTParser uses logging.error(), which might clutter test output.
    
    result = parser.parse_file(broken_file, temp_workspace) # Should return None
    assert result is None
