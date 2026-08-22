import ast
import io
import tokenize

from _repo import REPO_ROOT, iter_python_files

DocstringOwner = ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef


def has_comment_token(source: str) -> bool:
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    return any(token.type == tokenize.COMMENT for token in tokens)


def has_docstring(tree: ast.Module) -> bool:
    nodes: list[DocstringOwner] = [tree]
    nodes.extend(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    )
    return any(ast.get_docstring(node) is not None for node in nodes)


def test_no_comments_or_docstrings_in_repository_python_source() -> None:
    offenders: list[str] = []
    for path in iter_python_files(REPO_ROOT):
        if ".venv" in path.parts or ".nox" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        if not source.strip():
            continue
        violation = has_comment_token(source) or has_docstring(
            ast.parse(source, filename=str(path))
        )
        if violation:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, f"Python comments or docstrings found: {offenders}"


def test_violation_detected_for_comment() -> None:
    source = "x = 1  # a comment\n"
    assert has_comment_token(source)


def test_violation_detected_for_docstring() -> None:
    source = 'def f() -> int:\n    """doc"""\n    return 1\n'
    assert has_docstring(ast.parse(source))
