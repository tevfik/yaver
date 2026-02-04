
import sys
import tree_sitter_languages

def check_c_support():
    print("Checking Tree-sitter languages...")
    try:
        lang = tree_sitter_languages.get_language('c')
        print("✅ Language 'c' is available.")
    except Exception as e:
        print(f"❌ Language 'c' is NOT available: {e}")

    try:
        lang = tree_sitter_languages.get_language('cpp')
        print("✅ Language 'cpp' is available.")
    except Exception as e:
        print(f"❌ Language 'cpp' is NOT available: {e}")

if __name__ == "__main__":
    check_c_support()
