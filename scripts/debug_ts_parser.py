try:
    from tools.code_analyzer.parsers.tree_sitter_parser import TreeSitterParser
    import logging
    
    logging.basicConfig(level=logging.DEBUG)
    
    print("Testing TreeSitterParser('cpp')...")
    parser = TreeSitterParser('cpp')
    print("Success!")
except Exception as e:
    print(f"Failed: {e}")
