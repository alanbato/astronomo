"""Tests for syntax highlighting utilities."""

from textual.content import Content

from astronomo.syntax import highlight_code, normalize_language


class TestNormalizeLanguage:
    """Test language normalization."""

    def test_normalize_common_languages(self):
        """Test that common language names are normalized correctly."""
        assert normalize_language("python") == "python"
        assert normalize_language("javascript") == "javascript"
        assert normalize_language("rust") == "rust"
        assert normalize_language("go") == "go"

    def test_normalize_aliases(self):
        """Test that common language aliases are normalized."""
        assert normalize_language("py") == "python"
        assert normalize_language("js") == "javascript"
        assert normalize_language("ts") == "typescript"
        assert normalize_language("sh") == "bash"
        assert normalize_language("rb") == "ruby"
        assert normalize_language("md") == "markdown"
        assert normalize_language("rs") == "rust"
        assert normalize_language("yml") == "yaml"

    def test_normalize_case_insensitive(self):
        """Test that language normalization is case insensitive."""
        assert normalize_language("Python") == "python"
        assert normalize_language("JAVASCRIPT") == "javascript"
        assert normalize_language("Rust") == "rust"
        assert normalize_language("PY") == "python"
        assert normalize_language("JS") == "javascript"

    def test_normalize_with_extra_text(self):
        """Test that only the first word is used for language detection."""
        # Some Gemini pages use "python example" as alt text
        assert normalize_language("python example code") == "python"
        assert normalize_language("js snippet") == "javascript"
        assert normalize_language("rust code example") == "rust"

    def test_normalize_empty_and_none(self):
        """Test that empty and None values return None."""
        assert normalize_language(None) is None
        assert normalize_language("") is None
        assert normalize_language("   ") is None

    def test_normalize_unknown_language(self):
        """Test that unknown languages are passed through."""
        result = normalize_language("unknownlang")
        assert result == "unknownlang"

    def test_normalize_cpp_aliases(self):
        """Test C++ language aliases."""
        assert normalize_language("c++") == "cpp"
        assert normalize_language("cxx") == "cpp"

    def test_normalize_csharp_aliases(self):
        """Test C# language aliases."""
        assert normalize_language("c#") == "csharp"
        assert normalize_language("cs") == "csharp"


class TestHighlightCode:
    """Test syntax highlighting."""

    def test_highlight_python(self):
        """Test highlighting Python code returns Content."""
        code = "def hello():\n    return 'Hello, World!'"
        result = highlight_code(code, language="python")
        assert isinstance(result, Content)
        # The content should contain the original code
        assert "def" in str(result)
        assert "hello" in str(result)

    def test_highlight_javascript(self):
        """Test highlighting JavaScript code returns Content."""
        code = "function hello() { return 'Hello'; }"
        result = highlight_code(code, language="javascript")
        assert isinstance(result, Content)
        assert "function" in str(result)

    def test_highlight_unknown_language(self):
        """Test that unknown languages don't raise exceptions."""
        code = "some code in unknown language"
        result = highlight_code(code, language="nonexistent_language_xyz")
        assert isinstance(result, Content)
        assert "some code" in str(result)

    def test_highlight_no_language(self):
        """Test highlighting without language (auto-detection)."""
        code = "def hello(): pass"
        result = highlight_code(code, language=None)
        assert isinstance(result, Content)
        assert "def" in str(result)

    def test_highlight_empty_code(self):
        """Test highlighting empty code."""
        result = highlight_code("", language="python")
        assert isinstance(result, Content)

    def test_highlight_multiline_code(self):
        """Test highlighting multiline code."""
        code = """def greet(name):
    return f'Hello, {name}!'

if __name__ == '__main__':
    print(greet('World'))
"""
        result = highlight_code(code, language="python")
        assert isinstance(result, Content)
        assert "greet" in str(result)
        assert "name" in str(result)
