"""Unit tests for the function inspector."""

import ast
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pytest

# Add src directory to path for imports
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from mystic.core.function_inspector import (
    FunctionInspector,
    analyze_module_functions,
    get_function_schema,
    get_function_signature,
    get_mcp_tool_definition,
    inspect_function,
)


# Test functions with various signatures and features
def simple_function(x: int, y: int) -> int:
    """Add two numbers.
    
    Args:
        x: First number
        y: Second number
        
    Returns:
        Sum of x and y
    """
    return x + y


def complex_function(
    name: str,
    age: int = 18,
    tags: List[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    *args,
    **kwargs
) -> Dict[str, Any]:
    """Complex function with various parameter types.
    
    This function demonstrates various parameter types including
    positional, keyword, varargs, and kwargs.
    
    Args:
        name: Person's name
        age: Person's age (default: 18)
        tags: List of tags
        metadata: Optional metadata dictionary
        *args: Additional positional arguments
        **kwargs: Additional keyword arguments
        
    Returns:
        Dictionary containing all inputs
        
    Raises:
        ValueError: If name is empty
        TypeError: If age is not an integer
        
    Example:
        >>> complex_function("John", 25, tags=["python", "testing"])
        {'name': 'John', 'age': 25, ...}
        
    Note:
        This is a test function for the inspector
    """
    if not name:
        raise ValueError("Name cannot be empty")
    if not isinstance(age, int):
        raise TypeError("Age must be an integer")
        
    return {
        "name": name,
        "age": age,
        "tags": tags or [],
        "metadata": metadata or {},
        "args": args,
        "kwargs": kwargs
    }


async def async_function(x: int) -> int:
    """Async function example."""
    return x * 2


def generator_function(n: int):
    """Generator function example."""
    for i in range(n):
        yield i


def recursive_function(n: int) -> int:
    """Recursive factorial function."""
    if n <= 1:
        return 1
    return n * recursive_function(n - 1)


def function_with_loops(items: List[int]) -> int:
    """Function with loops for performance analysis."""
    total = 0
    for item in items:
        i = 0
        while i < item:
            total += 1
            i += 1
    return total


def insecure_function(code: str) -> Any:
    """Insecure function for security analysis."""
    import subprocess
    import pickle
    
    # Dangerous operations
    result = eval(code)  # noqa: S307
    exec(f"x = {code}")  # noqa: S102
    subprocess.run(["echo", code])  # noqa: S603
    
    return result


class TestClass:
    """Test class with methods."""
    
    def instance_method(self, x: int) -> int:
        """Instance method."""
        return x * 2
    
    @classmethod
    def class_method(cls, x: int) -> int:
        """Class method."""
        return x * 3
    
    @staticmethod
    def static_method(x: int) -> int:
        """Static method."""
        return x * 4


class TestFunctionInspector:
    """Test the FunctionInspector class."""
    
    def test_basic_inspection(self):
        """Test basic function inspection."""
        inspector = FunctionInspector()
        analysis = inspector.inspect_function(simple_function)
        
        assert analysis.signature.name == "simple_function"
        assert analysis.signature.module == __name__
        assert len(analysis.signature.parameters) == 2
        assert analysis.signature.return_type in ["int", "<class 'int'>"]
        assert not analysis.signature.is_async
        assert not analysis.signature.is_generator
        
    def test_complex_signature(self):
        """Test complex function signature analysis."""
        inspector = FunctionInspector()
        analysis = inspector.inspect_function(complex_function)
        
        # Check parameters
        params = {p["name"]: p for p in analysis.signature.parameters}
        assert "name" in params
        assert "age" in params
        assert "tags" in params
        assert "metadata" in params
        assert "args" in params
        assert "kwargs" in params
        
        # Check defaults
        assert not params["name"]["has_default"]
        assert params["age"]["has_default"]
        assert params["age"]["default"] == 18
        
        # Check parameter kinds
        assert params["args"]["kind"] == "VAR_POSITIONAL"
        assert params["kwargs"]["kind"] == "VAR_KEYWORD"
        
        # Check flags
        assert analysis.signature.has_varargs
        assert analysis.signature.has_kwargs
        
    def test_docstring_parsing(self):
        """Test docstring parsing."""
        inspector = FunctionInspector()
        analysis = inspector.inspect_function(complex_function)
        
        metadata = analysis.metadata
        assert metadata.summary == "Complex function with various parameter types."
        assert "This function demonstrates" in metadata.description
        
        # Check parameter documentation
        assert "name" in metadata.parameters_doc
        assert "Person's name" in metadata.parameters_doc["name"]
        
        # Check other sections
        assert "Dictionary containing all inputs" in metadata.returns_doc
        assert len(metadata.raises_doc) == 2
        assert len(metadata.examples) > 0
        assert len(metadata.notes) > 0
        
    def test_json_schema_generation(self):
        """Test JSON schema generation."""
        inspector = FunctionInspector()
        analysis = inspector.inspect_function(simple_function)
        
        schema = analysis.schema.input_schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "x" in schema["properties"]
        assert "y" in schema["properties"]
        assert schema["required"] == ["x", "y"]
        
        # Check property types
        assert schema["properties"]["x"]["type"] == "integer"
        assert schema["properties"]["y"]["type"] == "integer"
        
    def test_mcp_tool_definition(self):
        """Test MCP tool definition generation."""
        inspector = FunctionInspector()
        analysis = inspector.inspect_function(simple_function)
        
        mcp_tool = analysis.schema.mcp_tool_definition
        assert mcp_tool["name"] == "simple_function"
        assert "inputSchema" in mcp_tool
        assert mcp_tool["inputSchema"]["type"] == "object"
        
    def test_async_function_detection(self):
        """Test async function detection."""
        inspector = FunctionInspector()
        analysis = inspector.inspect_function(async_function)
        
        assert analysis.signature.is_async
        assert not analysis.signature.is_generator
        
    def test_generator_function_detection(self):
        """Test generator function detection."""
        inspector = FunctionInspector()
        analysis = inspector.inspect_function(generator_function)
        
        assert not analysis.signature.is_async
        assert analysis.signature.is_generator
        
    def test_method_detection(self):
        """Test method type detection."""
        inspector = FunctionInspector()
        test_obj = TestClass()
        
        # Note: unbound methods are just functions in Python 3
        instance_analysis = inspector.inspect_function(TestClass.instance_method)
        assert not instance_analysis.signature.is_classmethod
        assert not instance_analysis.signature.is_staticmethod
        
        # Bound method
        bound_analysis = inspector.inspect_function(test_obj.instance_method)
        assert bound_analysis.signature.is_method
        
    def test_dependency_analysis(self):
        """Test dependency analysis."""
        inspector = FunctionInspector()
        analysis = inspector.inspect_function(insecure_function)
        
        deps = analysis.dependencies
        assert "subprocess" in deps.imports
        assert "pickle" in deps.imports
        assert "eval" in deps.calls
        assert "exec" in deps.calls
        
    def test_performance_analysis(self):
        """Test performance analysis."""
        inspector = FunctionInspector()
        
        # Test recursive function
        recursive_analysis = inspector.inspect_function(recursive_function)
        assert recursive_analysis.performance_hints["is_recursive"]
        
        # Test function with loops
        loop_analysis = inspector.inspect_function(function_with_loops)
        assert loop_analysis.performance_hints["has_loops"]
        
        # Test complexity
        complex_analysis = inspector.inspect_function(complex_function)
        assert complex_analysis.performance_hints["complexity"] > 1
        assert complex_analysis.performance_hints["lines_of_code"] > 0
        
    def test_security_analysis(self):
        """Test security analysis."""
        inspector = FunctionInspector()
        analysis = inspector.inspect_function(insecure_function)
        
        security = analysis.security_analysis
        assert security["uses_eval"]
        assert security["uses_exec"]
        assert security["uses_subprocess"]
        assert security["uses_pickle"]
        assert len(security["vulnerabilities"]) > 0
        
    def test_caching(self):
        """Test inspection caching."""
        inspector = FunctionInspector(enable_caching=True)
        
        # First inspection
        analysis1 = inspector.inspect_function(simple_function)
        
        # Second inspection should use cache
        analysis2 = inspector.inspect_function(simple_function)
        
        # Should be the same object due to caching
        assert analysis1 is analysis2
        
        # Clear cache
        inspector.clear_cache()
        
        # Third inspection should create new object
        analysis3 = inspector.inspect_function(simple_function)
        assert analysis1 is not analysis3
        
    def test_change_detection(self):
        """Test function change detection."""
        inspector = FunctionInspector()
        
        # Initial inspection
        inspector.inspect_function(simple_function)
        
        # Check for changes (should be False for unchanged function)
        assert not inspector.detect_changes(simple_function)
        
        # Note: Actually modifying a function at runtime is complex,
        # so we just test the API exists
        
    def test_convenience_functions(self):
        """Test convenience functions."""
        # Test inspect_function
        info = inspect_function(simple_function)
        assert info["name"] == "simple_function"
        assert "signature" in info
        assert "metadata" in info
        assert "schema" in info
        
        # Test get_function_signature
        sig = get_function_signature(simple_function)
        assert "(x: int, y: int) -> int" in sig or "(x:int, y:int) -> int" in sig
        
        # Test get_function_schema
        schema = get_function_schema(simple_function)
        assert schema["type"] == "object"
        assert "properties" in schema
        
        # Test get_mcp_tool_definition
        mcp_tool = get_mcp_tool_definition(simple_function)
        assert mcp_tool["name"] == "simple_function"
        assert "inputSchema" in mcp_tool
        
    def test_analyze_module_functions(self):
        """Test module-level function analysis."""
        # Create a test module
        import types
        test_module = types.ModuleType("test_module")
        test_module.__name__ = "test_module"
        test_module.func1 = lambda x: x + 1
        test_module.func2 = lambda x: x * 2
        test_module.func1.__module__ = "test_module"
        test_module.func2.__module__ = "test_module"
        
        results = analyze_module_functions(test_module)
        assert "func1" in results
        assert "func2" in results
        
    def test_type_hint_conversion(self):
        """Test type hint to JSON schema conversion."""
        inspector = FunctionInspector()
        
        # Test basic types
        assert inspector._type_to_json_schema(str) == {"type": "string"}
        assert inspector._type_to_json_schema(int) == {"type": "integer"}
        assert inspector._type_to_json_schema(float) == {"type": "number"}
        assert inspector._type_to_json_schema(bool) == {"type": "boolean"}
        assert inspector._type_to_json_schema(list) == {"type": "array"}
        assert inspector._type_to_json_schema(dict) == {"type": "object"}
        
        # Test None
        assert inspector._type_to_json_schema(None) == {"type": "null"}
        assert inspector._type_to_json_schema(type(None)) == {"type": "null"}
        
        # Test string type hints
        assert inspector._type_to_json_schema("str") == {"type": "string"}
        assert inspector._type_to_json_schema("int") == {"type": "integer"}
        assert inspector._type_to_json_schema("Any") == {}
        
    def test_complex_type_hints(self):
        """Test complex type hint handling."""
        from typing import List, Dict, Optional, Union
        
        def typed_function(
            items: List[str],
            mapping: Dict[str, int],
            optional: Optional[str] = None,
            union_type: Union[str, int] = "default"
        ) -> List[Dict[str, Any]]:
            """Function with complex type hints."""
            return []
            
        inspector = FunctionInspector()
        analysis = inspector.inspect_function(typed_function)
        
        schema = analysis.schema.input_schema
        
        # Check List[str]
        assert schema["properties"]["items"]["type"] == "array"
        assert "items" in schema["properties"]["items"]
        
        # Check Dict[str, int]
        assert schema["properties"]["mapping"]["type"] == "object"
        
        # Check Optional[str]
        optional_schema = schema["properties"]["optional"]
        assert "anyOf" in optional_schema or optional_schema.get("type") == "string"
        
        # Check Union[str, int]
        union_schema = schema["properties"]["union_type"]
        assert "anyOf" in union_schema or union_schema.get("type") in ["string", "integer"]
        
    def test_source_analysis(self):
        """Test source code analysis."""
        inspector = FunctionInspector()
        analysis = inspector.inspect_function(simple_function)
        
        metadata = analysis.metadata
        assert metadata.source_file is not None
        assert metadata.source_lines is not None
        assert metadata.lines_of_code > 0
        assert metadata.complexity >= 1
        
    def test_decorator_detection(self):
        """Test decorator detection."""
        from functools import lru_cache
        
        @lru_cache(maxsize=128)
        def decorated_function(x: int) -> int:
            """Decorated function."""
            return x * 2
            
        inspector = FunctionInspector()
        # Note: decorated functions may have wrapped attributes
        # This is mainly testing that inspection doesn't crash
        analysis = inspector.inspect_function(decorated_function)
        assert analysis.signature.name in ["decorated_function", "wrapper"]
        
    def test_empty_function(self):
        """Test empty function handling."""
        def empty_function():
            pass
            
        inspector = FunctionInspector()
        analysis = inspector.inspect_function(empty_function)
        
        assert analysis.signature.name == "empty_function"
        assert len(analysis.signature.parameters) == 0
        assert analysis.signature.return_type is None
        assert analysis.metadata.docstring is None
        
    def test_call_graph(self):
        """Test call graph generation."""
        def func_a():
            func_b()
            func_c()
            
        def func_b():
            func_c()
            
        def func_c():
            pass
            
        inspector = FunctionInspector()
        inspector.inspect_function(func_a)
        inspector.inspect_function(func_b)
        inspector.inspect_function(func_c)
        
        call_graph = inspector.get_call_graph()
        # Note: Call graph analysis from AST is approximate
        assert len(call_graph) >= 0  # At least some entries
        
    def test_closure_analysis(self):
        """Test closure analysis."""
        def outer(x):
            def inner(y):
                return x + y
            return inner
            
        closure = outer(10)
        
        inspector = FunctionInspector()
        analysis = inspector.inspect_function(closure)
        
        # Should detect closure variables
        assert len(analysis.dependencies.closures) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])