try:
    import tree_sitter
    from tree_sitter import Parser
    import tree_sitter_languages
    print(f"tree_sitter version: {tree_sitter.__version__}")
except Exception as e:
    print(f"Import error: {e}")

try:
    print("Getting language cpp...")
    lang = tree_sitter_languages.get_language('cpp')
    print(f"Language object: {lang}, type: {type(lang)}")
    
    print("Initializing Parser...")
    parser = Parser()
    print("Parser initialized.")
    
    print("Setting language...")
    parser.set_language(lang)
    print("Language set.")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
