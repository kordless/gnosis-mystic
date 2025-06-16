"""
Function Inspector for Gnosis Mystic

Deep function introspection and analysis capabilities for generating
MCP tool definitions and understanding function behavior.
"""

import ast
import hashlib
import inspect
import re
import sys
import textwrap
import threading
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

try:
    from typing import Literal, TypedDict
except ImportError:
    from typing_extensions import Literal, TypedDict


@dataclass
class FunctionSignature:
    """Detailed function signature information."""

    name: str
    module: str
    qualname: str
    parameters: List[Dict[str, Any]]
    return_type: Optional[str]
    type_hints: Dict[str, Any]
    has_varargs: bool
    has_kwargs: bool
    is_async: bool
    is_generator: bool
    is_method: bool
    is_classmethod: bool
    is_staticmethod: bool


@dataclass
class FunctionMetadata:
    """Function metadata and documentation."""

    docstring: Optional[str]
    summary: Optional[str]
    description: Optional[str]
    parameters_doc: Dict[str, str]
    returns_doc: Optional[str]
    raises_doc: List[Tuple[str, str]]
    examples: List[str]
    notes: List[str]
    source_file: Optional[str]
    source_lines: Optional[Tuple[int, int]]
    complexity: int
    lines_of_code: int


@dataclass
class FunctionDependencies:
    """Function dependencies and relationships."""

    imports: Set[str]
    calls: Set[str]
    called_by: Set[str]
    global_vars: Set[str]
    closures: Set[str]
    decorators: List[str]
    ast_hash: str


@dataclass
class FunctionSchema:
    """JSON Schema for function parameters."""

    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]]
    mcp_tool_definition: Dict[str, Any]


@dataclass
class FunctionAnalysis:
    """Complete function analysis result."""

    signature: FunctionSignature
    metadata: FunctionMetadata
    dependencies: FunctionDependencies
    schema: FunctionSchema
    performance_hints: Dict[str, Any]
    security_analysis: Dict[str, Any]
    changes_detected: bool
    last_modified: Optional[float]


class FunctionInspector:
    """Deep function introspection and analysis."""

    def __init__(self, enable_caching: bool = True, cache_size: int = 1000):
        """Initialize the inspector."""
        self.enable_caching = enable_caching
        self.cache_size = cache_size
        self._cache: Dict[str, FunctionAnalysis] = {}
        self._function_registry: Dict[str, Callable] = {}
        self._call_graph: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()

    def inspect_function(self, func: Callable) -> FunctionAnalysis:
        """Comprehensive function analysis."""
        func_id = self._get_function_id(func)

        # Check cache
        if self.enable_caching and func_id in self._cache:
            cached = self._cache[func_id]
            if not self._has_function_changed(func, cached):
                return cached

        # Perform full analysis
        signature = self._analyze_signature(func)
        metadata = self._analyze_metadata(func)
        dependencies = self._analyze_dependencies(func)
        schema = self._generate_schema(func, signature)
        performance = self._analyze_performance(func, metadata)
        security = self._analyze_security(func, dependencies)

        analysis = FunctionAnalysis(
            signature=signature,
            metadata=metadata,
            dependencies=dependencies,
            schema=schema,
            performance_hints=performance,
            security_analysis=security,
            changes_detected=False,
            last_modified=self._get_modification_time(func),
        )

        # Update cache
        if self.enable_caching:
            with self._lock:
                self._cache[func_id] = analysis
                self._function_registry[func_id] = func

        return analysis

    def _get_function_id(self, func: Callable) -> str:
        """Get unique identifier for function."""
        return f"{func.__module__}.{func.__qualname__}"

    def _analyze_signature(self, func: Callable) -> FunctionSignature:
        """Analyze function signature."""
        sig = inspect.signature(func)
        type_hints = get_type_hints(func) if hasattr(func, "__annotations__") else {}

        parameters = []
        for name, param in sig.parameters.items():
            param_info = {
                "name": name,
                "kind": param.kind.name,
                "default": param.default if param.default != param.empty else None,
                "has_default": param.default != param.empty,
                "annotation": self._serialize_type(param.annotation)
                if param.annotation != param.empty
                else None,
                "type_hint": self._serialize_type(type_hints.get(name)),
            }
            parameters.append(param_info)

        return FunctionSignature(
            name=func.__name__,
            module=func.__module__,
            qualname=func.__qualname__,
            parameters=parameters,
            return_type=self._serialize_type(type_hints.get("return")),
            type_hints={k: self._serialize_type(v) for k, v in type_hints.items()},
            has_varargs=any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values()),
            has_kwargs=any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()),
            is_async=inspect.iscoroutinefunction(func),
            is_generator=inspect.isgeneratorfunction(func),
            is_method=inspect.ismethod(func),
            is_classmethod=isinstance(func, classmethod),
            is_staticmethod=isinstance(func, staticmethod),
        )

    def _analyze_metadata(self, func: Callable) -> FunctionMetadata:
        """Analyze function metadata and documentation."""
        docstring = inspect.getdoc(func)
        parsed_doc = self._parse_docstring(docstring) if docstring else {}

        # Get source information
        try:
            source_file = inspect.getsourcefile(func)
            source_lines = inspect.getsourcelines(func)
            source_code = "".join(source_lines[0])
            start_line = source_lines[1]
            end_line = start_line + len(source_lines[0]) - 1
            complexity = self._calculate_complexity(source_code)
            loc = len([line for line in source_lines[0] if line.strip()])
        except Exception:
            source_file = None
            start_line, end_line = None, None
            complexity = 0
            loc = 0

        return FunctionMetadata(
            docstring=docstring,
            summary=parsed_doc.get("summary"),
            description=parsed_doc.get("description"),
            parameters_doc=parsed_doc.get("parameters", {}),
            returns_doc=parsed_doc.get("returns"),
            raises_doc=parsed_doc.get("raises", []),
            examples=parsed_doc.get("examples", []),
            notes=parsed_doc.get("notes", []),
            source_file=source_file,
            source_lines=(start_line, end_line) if start_line else None,
            complexity=complexity,
            lines_of_code=loc,
        )

    def _analyze_dependencies(self, func: Callable) -> FunctionDependencies:
        """Analyze function dependencies."""
        dependencies = FunctionDependencies(
            imports=set(),
            calls=set(),
            called_by=set(),
            global_vars=set(),
            closures=set(),
            decorators=[],
            ast_hash="",
        )

        try:
            # Get source code
            source = inspect.getsource(func)
            tree = ast.parse(source)

            # Calculate AST hash
            dependencies.ast_hash = hashlib.sha256(ast.dump(tree).encode()).hexdigest()[:16]

            # Find the function node
            func_node = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == func.__name__:
                    func_node = node
                    break

            if func_node:
                # Analyze decorators
                for decorator in func_node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        dependencies.decorators.append(decorator.id)
                    elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                        dependencies.decorators.append(decorator.func.id)

                # Analyze function body
                visitor = DependencyVisitor()
                visitor.visit(func_node)
                dependencies.imports = visitor.imports
                dependencies.calls = visitor.calls
                dependencies.global_vars = visitor.globals

        except Exception:
            pass
        
        # Analyze closures (do this outside the AST parsing)
        if hasattr(func, "__closure__") and func.__closure__:
            for cell in func.__closure__:
                try:
                    # Try to get the value
                    value = cell.cell_contents
                    # Store type and repr for better info
                    dependencies.closures.add(f"{type(value).__name__}:{repr(value)}")
                except ValueError:
                    # Cell is empty
                    dependencies.closures.add("<empty cell>")
                except Exception:
                    dependencies.closures.add("<unknown>")

        # Update call graph
        func_id = self._get_function_id(func)
        with self._lock:
            for called in dependencies.calls:
                self._call_graph[func_id].add(called)
                # Note: called_by is populated when other functions are analyzed

        return dependencies

    def _generate_schema(self, func: Callable, signature: FunctionSignature) -> FunctionSchema:
        """Generate JSON schema for function."""
        # Generate input schema
        properties = {}
        required = []

        for param in signature.parameters:
            if param["kind"] in ["VAR_POSITIONAL", "VAR_KEYWORD"]:
                continue

            # Get the actual type hint, not the serialized string
            type_hint = None
            if hasattr(func, "__annotations__") and param["name"] in func.__annotations__:
                type_hint = func.__annotations__[param["name"]]
            
            param_schema = self._type_to_json_schema(type_hint)
            if param["has_default"]:
                param_schema["default"] = param["default"]
            else:
                required.append(param["name"])

            properties[param["name"]] = param_schema

        input_schema = {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": signature.has_kwargs,
        }

        # Generate output schema
        output_schema = None
        if signature.return_type:
            output_schema = self._type_to_json_schema(signature.return_type)

        # Generate MCP tool definition
        mcp_tool = {
            "name": signature.name,
            "description": signature.metadata.summary if hasattr(signature, "metadata") else "",
            "inputSchema": input_schema,
        }

        return FunctionSchema(
            input_schema=input_schema, output_schema=output_schema, mcp_tool_definition=mcp_tool
        )

    def _type_to_json_schema(self, type_hint: Any) -> Dict[str, Any]:
        """Convert Python type hint to JSON schema."""
        if type_hint is None or type_hint == type(None):
            return {"type": "null"}

        if isinstance(type_hint, str):
            # Handle string type hints
            type_map = {
                "str": "string",
                "int": "integer",
                "float": "number",
                "bool": "boolean",
                "list": "array",
                "dict": "object",
            }
            if type_hint == "Any":
                return {}
            return {"type": type_map.get(type_hint, "string")}

        # Handle actual types
        if type_hint == str:
            return {"type": "string"}
        elif type_hint == int:
            return {"type": "integer"}
        elif type_hint == float:
            return {"type": "number"}
        elif type_hint == bool:
            return {"type": "boolean"}
        elif type_hint == list:
            return {"type": "array"}
        elif type_hint == dict:
            return {"type": "object"}

        # Handle generic types
        origin = get_origin(type_hint)
        args = get_args(type_hint)

        if origin == list:
            schema = {"type": "array"}
            if args:
                schema["items"] = self._type_to_json_schema(args[0])
            return schema

        elif origin == dict:
            schema = {"type": "object"}
            if args and len(args) >= 2:
                schema["additionalProperties"] = self._type_to_json_schema(args[1])
            return schema

        elif origin == Union:
            # Handle Optional[T] which is Union[T, None]
            if len(args) == 2 and type(None) in args:
                non_none_type = args[0] if args[1] == type(None) else args[1]
                schema = self._type_to_json_schema(non_none_type)
                return {"anyOf": [schema, {"type": "null"}]}
            else:
                return {"anyOf": [self._type_to_json_schema(arg) for arg in args]}

        elif origin == Literal:
            return {"enum": list(args)}

        # Default fallback
        return {}

    def _parse_docstring(self, docstring: str) -> Dict[str, Any]:
        """Parse docstring to extract structured information."""
        if not docstring:
            return {}

        lines = docstring.strip().split("\n")
        result = {
            "summary": "",
            "description": "",
            "parameters": {},
            "returns": None,
            "raises": [],
            "examples": [],
            "notes": [],
        }

        # Extract summary (first line)
        if lines:
            result["summary"] = lines[0].strip()

        # Parse sections
        current_section = "description"
        current_param = None
        buffer = []

        for line in lines[1:]:
            stripped = line.strip()
            lower = stripped.lower()

            # Check for section headers
            if lower.startswith(("args:", "arguments:", "parameters:", "params:")):
                current_section = "parameters"
                continue
            elif lower.startswith(("returns:", "return:")):
                current_section = "returns"
                continue
            elif lower.startswith(("raises:", "raise:", "except:", "exceptions:")):
                current_section = "raises"
                continue
            elif lower.startswith(("example:", "examples:")):
                current_section = "examples"
                continue
            elif lower.startswith(("note:", "notes:")):
                current_section = "notes"
                continue

            # Process content based on section
            if current_section == "description":
                if stripped:
                    buffer.append(stripped)
            elif current_section == "parameters":
                # Look for parameter definitions
                param_match = re.match(r"^(\w+)\s*[:)]\s*(.*)$", stripped)
                if param_match:
                    current_param = param_match.group(1)
                    result["parameters"][current_param] = param_match.group(2)
                elif current_param and stripped:
                    result["parameters"][current_param] += " " + stripped
            elif current_section == "returns":
                if stripped:
                    if result["returns"]:
                        result["returns"] += " " + stripped
                    else:
                        result["returns"] = stripped
            elif current_section == "raises":
                exception_match = re.match(r"^(\w+)\s*[:)]\s*(.*)$", stripped)
                if exception_match:
                    result["raises"].append((exception_match.group(1), exception_match.group(2)))
            elif current_section == "examples":
                if stripped:
                    result["examples"].append(stripped)
            elif current_section == "notes":
                if stripped:
                    result["notes"].append(stripped)

        # Set description
        if buffer:
            result["description"] = " ".join(buffer)

        return result

    def _calculate_complexity(self, source_code: str) -> int:
        """Calculate cyclomatic complexity of function."""
        try:
            tree = ast.parse(source_code)
            complexity = 1  # Base complexity

            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1

            return complexity
        except Exception:
            return 0

    def _analyze_performance(self, func: Callable, metadata: FunctionMetadata) -> Dict[str, Any]:
        """Analyze performance characteristics."""
        hints = {
            "complexity": metadata.complexity,
            "lines_of_code": metadata.lines_of_code,
            "is_recursive": self._is_recursive(func),
            "has_loops": self._has_loops(func),
            "recommendations": [],
        }

        # Add recommendations based on analysis
        if hints["complexity"] > 10:
            hints["recommendations"].append("Consider breaking down this complex function")
        if hints["lines_of_code"] > 50:
            hints["recommendations"].append("Function is quite long, consider splitting")
        if hints["is_recursive"]:
            hints["recommendations"].append("Recursive function - watch for stack overflow")

        return hints

    def _analyze_security(self, func: Callable, dependencies: FunctionDependencies) -> Dict[str, Any]:
        """Analyze security aspects."""
        analysis = {
            "uses_eval": "eval" in dependencies.calls,
            "uses_exec": "exec" in dependencies.calls,
            "uses_subprocess": any("subprocess" in imp for imp in dependencies.imports),
            "uses_pickle": any("pickle" in imp for imp in dependencies.imports),
            "uses_os_system": "system" in dependencies.calls,
            "vulnerabilities": [],
        }

        # Add vulnerability warnings
        if analysis["uses_eval"] or analysis["uses_exec"]:
            analysis["vulnerabilities"].append("Dynamic code execution detected")
        if analysis["uses_subprocess"] or analysis["uses_os_system"]:
            analysis["vulnerabilities"].append("System command execution detected")
        if analysis["uses_pickle"]:
            analysis["vulnerabilities"].append("Pickle usage can be insecure with untrusted data")

        return analysis

    def _is_recursive(self, func: Callable) -> bool:
        """Check if function is recursive."""
        try:
            source = inspect.getsource(func)
            return func.__name__ in source
        except Exception:
            return False

    def _has_loops(self, func: Callable) -> bool:
        """Check if function contains loops."""
        try:
            source = inspect.getsource(func)
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.For, ast.While)):
                    return True
            return False
        except Exception:
            return False

    def _serialize_type(self, type_hint: Any) -> Optional[str]:
        """Serialize type hint to string."""
        if type_hint is None:
            return None
        if isinstance(type_hint, str):
            return type_hint
        if hasattr(type_hint, "__name__"):
            return type_hint.__name__
        return str(type_hint)

    def _has_function_changed(self, func: Callable, cached: FunctionAnalysis) -> bool:
        """Check if function has changed since last analysis."""
        try:
            # Check modification time
            current_time = self._get_modification_time(func)
            if current_time and cached.last_modified:
                if current_time > cached.last_modified:
                    return True

            # Check AST hash
            source = inspect.getsource(func)
            tree = ast.parse(source)
            current_hash = hashlib.sha256(ast.dump(tree).encode()).hexdigest()[:16]
            return current_hash != cached.dependencies.ast_hash
        except Exception:
            return True

    def _get_modification_time(self, func: Callable) -> Optional[float]:
        """Get function's source file modification time."""
        try:
            source_file = inspect.getsourcefile(func)
            if source_file:
                return Path(source_file).stat().st_mtime
        except Exception:
            pass
        return None

    def get_function_schema(self, func: Callable) -> Dict[str, Any]:
        """Generate JSON schema for function arguments."""
        analysis = self.inspect_function(func)
        return analysis.schema.input_schema

    def get_mcp_tool_definition(self, func: Callable) -> Dict[str, Any]:
        """Generate MCP tool definition for function."""
        analysis = self.inspect_function(func)
        return analysis.schema.mcp_tool_definition

    def analyze_dependencies(self, func: Callable) -> List[str]:
        """Analyze function dependencies."""
        analysis = self.inspect_function(func)
        deps = []
        deps.extend(f"import:{imp}" for imp in analysis.dependencies.imports)
        deps.extend(f"calls:{call}" for call in analysis.dependencies.calls)
        deps.extend(f"global:{var}" for var in analysis.dependencies.global_vars)
        return deps

    def get_call_graph(self) -> Dict[str, List[str]]:
        """Get the complete call graph."""
        with self._lock:
            return {caller: list(callees) for caller, callees in self._call_graph.items()}

    def detect_changes(self, func: Callable) -> bool:
        """Detect if function has changed since last inspection."""
        func_id = self._get_function_id(func)
        if func_id in self._cache:
            return self._has_function_changed(func, self._cache[func_id])
        return True

    def clear_cache(self):
        """Clear the inspection cache."""
        with self._lock:
            self._cache.clear()
            self._function_registry.clear()
            self._call_graph.clear()


class DependencyVisitor(ast.NodeVisitor):
    """AST visitor to extract dependencies."""

    def __init__(self):
        self.imports = set()
        self.calls = set()
        self.globals = set()

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module)
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.add(node.func.attr)
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            # Could be a global variable reference
            self.globals.add(node.id)
        self.generic_visit(node)


# Convenience functions
def inspect_function(func: Callable) -> Dict[str, Any]:
    """Inspect a function and return comprehensive information."""
    inspector = FunctionInspector()
    analysis = inspector.inspect_function(func)
    return {
        "name": analysis.signature.name,
        "signature": analysis.signature,
        "metadata": analysis.metadata,
        "dependencies": analysis.dependencies,
        "schema": analysis.schema.input_schema,
        "mcp_tool": analysis.schema.mcp_tool_definition,
        "performance": analysis.performance_hints,
        "security": analysis.security_analysis,
    }


def get_function_signature(func: Callable) -> str:
    """Get function signature as string."""
    return str(inspect.signature(func))


def get_function_schema(func: Callable) -> Dict[str, Any]:
    """Generate JSON schema for function arguments."""
    inspector = FunctionInspector()
    return inspector.get_function_schema(func)


def get_mcp_tool_definition(func: Callable) -> Dict[str, Any]:
    """Generate MCP tool definition for function."""
    inspector = FunctionInspector()
    return inspector.get_mcp_tool_definition(func)


def analyze_module_functions(module) -> Dict[str, FunctionAnalysis]:
    """Analyze all functions in a module."""
    inspector = FunctionInspector()
    results = {}

    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj) and obj.__module__ == module.__name__:
            results[name] = inspector.inspect_function(obj)

    return results
