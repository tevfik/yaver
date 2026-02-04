# Yaver Graph Schema (Neo4j)

This document describes the property graph model used to represent code structure.

## Nodes

### `File`
Represents a source code file.
- **Labels**: `:File`
- **Properties**:
  - `id`: Unique path (e.g., `repo_name:src/main.py`)
  - `path`: Relative path
  - `language`: 'python', 'javascript', etc.
  - `repo_id`: Name of the repository
  - `commit_hash`: Git version
  - `layer`: 'API', 'CORE', 'DATA' (Auto-tagged)

### `Class`
Represents a class definition.
- **Labels**: `:Class`
- **Properties**:
  - `id`: Unique ID (e.g., `...:src/main.py::MyClass`)
  - `name`: Class name
  - `start_line`, `end_line`: Location
  - `docstring`: Summary

### `Function`
Represents a function or method.
- **Labels**: `:Function`
- **Properties**:
  - `id`: Unique ID (e.g., `...::MyClass::my_method`)
  - `name`: Function name
  - `args`: List of argument names
  - `complexity`: Cyclomatic complexity score
  - `is_async`: Boolean

## Relationships

### Structural
- `(:File)-[:CONTAINS]->(:Class)`
- `(:File)-[:DEFINES_FUNCTION]->(:Function)`
- `(:Class)-[:DEFINES_METHOD]->(:Function)`
- `(:File)-[:IMPORTS]->(:File)`

### Behavioral
- `(:Function)-[:CALLS {line: 123}]->(:Function)`
  - Represents a static function call.

## Queries (Cypher)

**Find Circular Dependencies:**
```cypher
MATCH path = (n:Function)-[:CALLS*1..5]->(n)
RETURN path
```

**Find API Entry Points:**
```cypher
MATCH (f:File {layer: 'API'})-[:DEFINES_FUNCTION]->(fn)
RETURN fn
```
