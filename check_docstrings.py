"""Report any module, class, method or function in the project that has no docstring.

Run from the project folder:  python check_docstrings.py
It prints nothing but "All good" when everything is documented. Migrations are
skipped because Django generates them.
"""
import ast
import pathlib
import sys

SKIP_DIRS = {"venv", ".venv", "migrations", "__pycache__", ".git"}


def missing_docstrings(path):
    """Return a list of 'file:line name' strings for undocumented items in one file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    problems = []
    if not ast.get_docstring(tree) and tree.body:
        problems.append(f"{path}:1 module")
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if not ast.get_docstring(node):
                problems.append(f"{path}:{node.lineno} {node.name}")
    return problems


def main():
    """Check every .py file under the current folder and exit 1 if anything is missing."""
    problems = []
    for path in sorted(pathlib.Path(".").rglob("*.py")):
        if SKIP_DIRS & set(path.parts):
            continue
        problems += missing_docstrings(path)
    print("\n".join(problems) if problems else "All good: everything has a docstring.")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
