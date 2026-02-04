import pytest
from pathlib import Path
from src.tools.code_analyzer.parsers.tree_sitter_parser import TreeSitterParser

class TestTreeSitterExtendedLanguages:

    def test_parse_java(self):
        code = """
public class MyJavaClass {
    public void myMethod() {
        otherMethod();
    }
    
    public MyJavaClass() {
    }
}
"""
        parser = TreeSitterParser('java')
        analysis = parser.parse(code, Path("Test.java"), Path("."))
        
        # Verify Class
        assert len(analysis.classes) == 1
        assert analysis.classes[0].name == 'MyJavaClass'
        
        # Verify Methods (including constructor)
        func_names = [f.name for f in analysis.functions]
        # Note: TreeSitter might capture constructor as generic usage depending on grammar, 
        # but my query explicitely looks for constructor_declaration
        assert 'myMethod' in func_names
        assert 'MyJavaClass' in func_names # Constructor
        
        # Verify call
        calls = [c['callee'] for c in analysis.calls]
        assert 'otherMethod' in calls

    def test_parse_javascript(self):
        code = """
class JSClass {
    constructor() {}
    myMethod() {
        console.log("hello");
    }
}

function globalFunc() {}
"""
        parser = TreeSitterParser('javascript')
        analysis = parser.parse(code, Path("test.js"), Path("."))
        
        # Verify Class
        assert analysis.classes[0].name == 'JSClass'
        
        # Verify Functions
        func_names = [f.name for f in analysis.functions]
        assert 'globalFunc' in func_names
        assert 'myMethod' in func_names
        
        # Verify Calls
        calls = [c['callee'] for c in analysis.calls]
        assert 'log' in calls

    def test_parse_rust(self):
        code = """
struct MyStruct {
    field: i32
}

impl MyStruct {
    fn new() -> Self {
        MyStruct { field: 0 }
    }
}

fn main() {
    println!("Hello");
    let x = MyStruct::new();
}
"""
        parser = TreeSitterParser('rust')
        analysis = parser.parse(code, Path("test.rs"), Path("."))
        
        # Verify Struct (Class equivalent)
        assert len(analysis.classes) >= 1
        class_names = [c.name for c in analysis.classes]
        assert 'MyStruct' in class_names
        
        # Verify Functions
        func_names = [f.name for f in analysis.functions]
        assert 'main' in func_names
        assert 'new' in func_names
        
        # Verify Calls - Rust macro calls like println! are often call_expression in tree-sitter-rust
        # but sometimes macro_invocation. My query looked for call_expression. 
        # 'MyStruct::new' might be a call_expression with scoped_identifier.
        # My generic capture might miss complex scoped calls if not defined.
        # Let's check what we got.
