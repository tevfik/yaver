from tree_sitter_languages import get_language
from tree_sitter import Parser
import warnings

# Capture warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    lang = get_language('python')
    print(f"Warnings caught: {len(w)}")
    if len(w) > 0:
        print(f"Warning: {w[0].message}")
