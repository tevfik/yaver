from src.tools.code_analyzer.models import FileAnalysis
print(f"Has resolved_imports: {hasattr(FileAnalysis, 'resolved_imports')}")
print(f"Fields: {FileAnalysis.__dataclass_fields__.keys()}")
