"""Static import audit: does every name a module imports actually exist?

Why this exists: FastAPI and pydantic cannot be installed in every environment
this repo is developed in, so ``import routers.tickets`` is sometimes impossible
to execute. But the failure mode that actually bites -- a router importing a
symbol that was deleted when the data layer was rebuilt -- is detectable without
running anything. This walks each module's AST, collects its ``from X import a,
b`` statements for *first-party* modules only, and checks each name against the
target module's own top-level definitions.

    python tools/check_imports.py

Exit code 1 if any first-party import cannot be satisfied, so it can be wired
into CI or a pre-demo check. Third-party imports (fastapi, PIL, ...) are listed
separately as "needs install" and never fail the run.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

# Modules that belong to this project. Anything else is a third-party install
# concern, not a broken reference.
FIRST_PARTY_ROOTS = {"database", "config", "models", "domain", "services",
                     "routers", "utils", "tools", "track1_engine"}

STDLIB_OK = True


def module_path(dotted: str) -> Path | None:
    """Resolve 'services.tickets' -> backend/services/tickets.py, if it exists.

    Also resolves first-party packages that live beside the backend (notably
    ``track1_engine``), and accepts a plain directory as a package: PEP 420
    namespace packages import fine without an ``__init__.py``, so demanding one
    would report working imports as broken.
    """
    parts = dotted.split(".")
    for root in (BACKEND, BACKEND.parent):
        candidate = root.joinpath(*parts).with_suffix(".py")
        if candidate.exists():
            return candidate
        package = root.joinpath(*parts)
        if (package / "__init__.py").exists():
            return package / "__init__.py"
        if package.is_dir():
            return package
    return None


def top_level_names(path: Path) -> set[str]:
    """Every name a module exposes at module level, including re-exports."""
    if path.is_dir():
        # A namespace package exposes its submodules and nothing else.
        return {p.stem for p in path.glob("*.py")} | {
            d.name for d in path.iterdir() if d.is_dir()}
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, (ast.Try, ast.If)):
            # try/except ImportError fallbacks and `if TYPE_CHECKING:` blocks
            # still define module-level names.
            for sub in ast.walk(node):
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef,
                                    ast.ClassDef)):
                    names.add(sub.name)
                elif isinstance(sub, ast.ImportFrom):
                    for alias in sub.names:
                        names.add(alias.asname or alias.name)
                elif isinstance(sub, ast.Import):
                    for alias in sub.names:
                        names.add(alias.asname or alias.name.split(".")[0])
                elif isinstance(sub, ast.Assign):
                    for target in sub.targets:
                        if isinstance(target, ast.Name):
                            names.add(target.id)
    return names


def audit(path: Path) -> tuple[list[str], set[str]]:
    """Return (problems, third_party_roots) for one file."""
    problems: list[str] = []
    third_party: set[str] = set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return [f"SYNTAX ERROR line {exc.lineno}: {exc.msg}"], third_party

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level or not node.module:
                continue  # relative import, resolved differently
            root = node.module.split(".")[0]
            if root not in FIRST_PARTY_ROOTS:
                third_party.add(root)
                continue
            target = module_path(node.module)
            if target is None:
                problems.append(f"imports from '{node.module}' which does not "
                                f"exist (line {node.lineno})")
                continue
            available = top_level_names(target)
            for alias in node.names:
                if alias.name == "*":
                    continue
                # `from services import tickets` is legitimate when tickets is a
                # submodule rather than a name bound in services/__init__.py.
                if module_path(f"{node.module}.{alias.name}") is not None:
                    continue
                if alias.name not in available:
                    problems.append(f"'{alias.name}' is not defined in "
                                    f"{node.module} (line {node.lineno})")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in FIRST_PARTY_ROOTS:
                    if module_path(alias.name) is None:
                        problems.append(f"imports module '{alias.name}' which "
                                        f"does not exist (line {node.lineno})")
                else:
                    third_party.add(root)
    return problems, third_party


def main() -> int:
    targets = sorted(
        p for p in BACKEND.rglob("*.py")
        if not any(part in {"venv", ".venv", "__pycache__", "node_modules",
                            "site-packages"}
                   for part in p.parts)
    )
    broken = 0
    all_third_party: set[str] = set()
    for path in targets:
        problems, third_party = audit(path)
        all_third_party |= third_party
        rel = path.relative_to(BACKEND)
        if problems:
            broken += 1
            print(f"\n{rel}")
            for problem in problems:
                print(f"    {problem}")

    print(f"\n{len(targets)} files audited, {broken} with unresolved "
          f"first-party imports.")
    external = sorted(r for r in all_third_party
                      if r not in sys.stdlib_module_names)
    print(f"third-party imports seen: {', '.join(external) or 'none'}")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
