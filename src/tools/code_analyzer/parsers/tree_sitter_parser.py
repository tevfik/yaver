"""
Tree-sitter Parser
Generic parser implementation using Tree-sitter for multiple languages.
"""
import logging
import warnings
from pathlib import Path
from typing import Optional, List, Dict, Any
import tree_sitter
from tree_sitter import Language, Parser
import tree_sitter_languages

from ..models import FileAnalysis, ClassInfo, FunctionInfo
from .base import BaseParser

logger = logging.getLogger(__name__)

# Suppress tree-sitter deprecation warning about Language(path, name)
# This is an issue in tree_sitter_languages library, not our code
warnings.filterwarnings("ignore", category=FutureWarning, module="tree_sitter")

class TreeSitterParser(BaseParser):
    """
    Parser for C++, Java, Go, JS, etc. using Tree-sitter.
    """
    
    def __init__(self, language_name: str):
        """
        Args:
            language_name: 'cpp', 'java', 'go', 'javascript', 'typescript', etc.
        """
        self.language_name = language_name
        try:
            self.language = tree_sitter_languages.get_language(language_name)
            self.parser = Parser()
            self.parser.set_language(self.language)
            self._load_queries()
        except Exception as e:
            logger.error(f"Failed to initialize Tree-sitter for {language_name}: {e}")
            # Ensure we can see why it failed in logs if needed
            logger.debug(f"Tree-sitter init details: {e}", exc_info=True)
            raise

    def _load_queries(self):
        """Load S-expression queries for the language"""
        self.queries = {}
        
        # C++ / C Queries
        if self.language_name in ['cpp', 'c']:
            # More robust function definition query for C/C++
            # Handles:
            # 1. int foo()
            # 2. int *foo()
            # 3. static int foo()
            # 4. struct A foo()
            self.queries['functions'] = """
            (function_definition
              declarator: (function_declarator
                declarator: (identifier) @func.name)
            ) @func.def
            
            (function_definition
              declarator: (pointer_declarator
                declarator: (function_declarator
                  declarator: (identifier) @func.name))
            ) @func.def
            
            (function_definition
               declarator: (pointer_declarator
                  declarator: (pointer_declarator
                     declarator: (function_declarator
                        declarator: (identifier) @func.name)))
            ) @func.def
            """
            
            # Struct/Class Queries
            self.queries['classes'] = """
            (struct_specifier
              name: (type_identifier) @class.name
            ) @class.def
            """
            
            # Add C++ specific class specifier only for cpp lang? 
            # Or make it optional? 
            # Tree-sitter strictness might fail if node type doesn't exist in grammar
            if self.language_name == 'cpp':
                self.queries['classes'] += """
                (class_specifier
                  name: (type_identifier) @class.name
                ) @class.def
                """
            
            self.queries['calls'] = """
            (call_expression
              function: (identifier) @call.name
            ) @call.site
            
            (call_expression
              function: (field_expression
                field: (field_identifier) @call.name)
            ) @call.site
            """
        
        # Python Queries
        elif self.language_name == 'python':
            self.queries['functions'] = """
            (function_definition
              name: (identifier) @func.name
            ) @func.def
            """
            self.queries['classes'] = """
            (class_definition
              name: (identifier) @class.name
            ) @class.def
            """
            self.queries['calls'] = """
            (call
              function: (identifier) @call.name
            ) @call.site
            
            (call
              function: (attribute
                attribute: (identifier) @call.name)
            ) @call.site
            """

        # Go Queries
        elif self.language_name == 'go':
            self.queries['functions'] = """
            (function_declaration
              name: (identifier) @func.name
            ) @func.def
            
            (method_declaration
              name: (field_identifier) @func.name
            ) @func.def
            """
            self.queries['classes'] = """
            (type_spec
              name: (type_identifier) @class.name
            ) @class.def
            """
            self.queries['calls'] = """
            (call_expression
              function: (identifier) @call.name
            ) @call.site
            
            (call_expression
              function: (selector_expression
                field: (field_identifier) @call.name)
            ) @call.site
            """

        # Java Queries
        elif self.language_name == 'java':
            self.queries['functions'] = """
            (method_declaration
              name: (identifier) @func.name
            ) @func.def
            (constructor_declaration
              name: (identifier) @func.name
            ) @func.def
            """
            self.queries['classes'] = """
            (class_declaration
              name: (identifier) @class.name
            ) @class.def
            (interface_declaration
              name: (identifier) @class.name
            ) @class.def
            """
            self.queries['calls'] = """
            (method_invocation
              name: (identifier) @call.name
            ) @call.site
            """

        # JavaScript / TypeScript Queries
        elif self.language_name in ['javascript', 'typescript', 'tsx']:
            self.queries['functions'] = """
            (function_declaration
              name: (identifier) @func.name
            ) @func.def
            (method_definition
              name: (property_identifier) @func.name
            ) @func.def
            """
            self.queries['classes'] = """
            (class_declaration
              name: (identifier) @class.name
            ) @class.def
            """
            self.queries['calls'] = """
            (call_expression
              function: (identifier) @call.name
            ) @call.site
            (call_expression
              function: (member_expression
                property: (property_identifier) @call.name)
            ) @call.site
            """

        # Rust Queries
        elif self.language_name == 'rust':
            self.queries['functions'] = """
            (function_item
              name: (identifier) @func.name
            ) @func.def
            """
            self.queries['classes'] = """
            (struct_item
              name: (type_identifier) @class.name
            ) @class.def
            (trait_item
              name: (type_identifier) @class.name
            ) @class.def
            """
            self.queries['calls'] = """
            (call_expression
              function: (identifier) @call.name
            ) @call.site
            (call_expression
              function: (field_expression
                field: (field_identifier) @call.name)
            ) @call.site
            """

    def parse(self, source_code: str, file_path: Path, repo_root: Path) -> Optional[FileAnalysis]:
        if not hasattr(self, 'parser'):
            return None
            
        try:
            source_bytes = bytes(source_code, "utf8")
            tree = self.parser.parse(source_bytes)
            root_node = tree.root_node
            
            rel_path = file_path.relative_to(repo_root).as_posix()
            
            analysis = FileAnalysis(
                file_path=rel_path,
                language=self.language_name,
                loc=len(source_code.splitlines()),
                content_hash=""
            )
            
            # Extract based on loaded queries
            if 'functions' in self.queries:
                self._extract_functions(root_node, source_bytes, analysis)
                
            if 'classes' in self.queries:
                self._extract_classes(root_node, source_bytes, analysis)

            if 'calls' in self.queries:
                self._extract_calls(root_node, source_bytes, analysis)

            # Post-process: Resolve callers based on function ranges
            for call in analysis.calls:
                for func in analysis.functions:
                    if func.start_line <= call['line'] <= func.end_line:
                        call['caller'] = func.name
                        break
                if call['caller'] == 'unknown':
                     call['caller'] = '<global>'
            
            return analysis
            
        except Exception as e:
            logger.error(f"Tree-sitter parse failed for {file_path}: {e}")
            return None

    def _extract_calls(self, root_node, source_bytes, analysis: FileAnalysis):
        query = self.language.query(self.queries['calls'])
        captures = query.captures(root_node)
        
        # We need to find "call.name" within "call.site"
        # Since captures are flat [(node, name), ...], we iterate
        
        current_call = {}
        
        for node, name in captures:
            if name == 'call.site':
                # New call site
                pass
            elif name == 'call.name':
                call_name = source_bytes[node.start_byte:node.end_byte].decode('utf8')
                start_line = node.start_point[0] + 1
                
                analysis.calls.append({
                    'caller': 'unknown', # Context resolution needed later
                    'callee': call_name,
                    'line': start_line
                })

    def _extract_functions(self, root_node, source_bytes, analysis: FileAnalysis):
        query = self.language.query(self.queries['functions'])
        captures = query.captures(root_node)
        
        # Capture processing is tricky because it's a flat list.
        # We assume @func.def contains @func.name
        
        # Organize by definition node
        functions_map = {} # node.id -> info
        
        # First pass: Identify all function definitions
        for node, name in captures:
            if name == 'func.def':
                functions_map[node.id] = {
                    'node': node,
                    'name': 'unknown',
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                }
        
        # Second pass: Associate names with definitions
        for node, name in captures:
            if name == 'func.name':
                # Traverse up to find the parent function definition
                parent = node
                while parent:
                    if parent.id in functions_map:
                        functions_map[parent.id]['name'] = source_bytes[node.start_byte:node.end_byte].decode('utf8')
                        break
                    parent = parent.parent

        for info in functions_map.values():
            analysis.functions.append(FunctionInfo(
                name=info['name'],
                args=[], # TODO: Extract args
                returns=None,
                docstring=None,
                start_line=info['start_line'],
                end_line=info['end_line']
            ))

    def _extract_classes(self, root_node, source_bytes, analysis: FileAnalysis):
        query = self.language.query(self.queries['classes'])
        captures = query.captures(root_node)
        
        classes_map = {}
        
        # First pass: Identify all class definitions
        for node, name in captures:
            if name == 'class.def':
                classes_map[node.id] = {
                    'node': node,
                    'name': 'unknown',
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1
                }
                
        # Second pass: Associate names with classes
        for node, name in captures:
            if name == 'class.name':
                 parent = node
                 while parent:
                    if parent.id in classes_map:
                        classes_map[parent.id]['name'] = source_bytes[node.start_byte:node.end_byte].decode('utf8')
                        break
                    parent = parent.parent
                    
        for info in classes_map.values():
            # TODO: Extract methods inside class
            analysis.classes.append(ClassInfo(
                name=info['name'],
                bases=[],
                docstring=None,
                start_line=info['start_line'],
                end_line=info['end_line']
            ))

    def _extract_cpp_entities(self, node, source: str, analysis: FileAnalysis):
        # deprecated by generic _extract methods above
        pass


