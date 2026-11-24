"""AST contract tests validating Telethon TL calls and imports across telegram_mcp."""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

from telethon.tl import functions, types

PACKAGE_ROOT = Path(__file__).resolve().parent.parent / "telegram_mcp"


def _attribute_chain(node: ast.AST) -> list[str] | None:
    parts: list[str] = []
    cur: ast.AST = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return list(reversed(parts))
    return None


def _resolve_tl_object(chain: list[str]) -> object | None:
    obj: object | None = functions if chain[0] == "functions" else types
    for part in chain[1:]:
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    return obj


def test_all_telethon_tl_constructor_calls_match_installed_signatures() -> None:
    mismatches: list[str] = []
    checked = 0

    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            chain = _attribute_chain(node.func)
            if not chain or chain[0] not in ("functions", "types") or len(chain) < 2:
                continue

            cls = _resolve_tl_object(chain)
            if cls is None:
                mismatches.append(f"{path.name}:{node.lineno} {'.'.join(chain)} not found")
                continue
            if not inspect.isclass(cls):
                continue

            checked += 1
            if any(kw.arg is None for kw in node.keywords):
                continue

            sig = inspect.signature(cls.__init__)
            pos_args = [None] * len(node.args)
            kw_args = {kw.arg: None for kw in node.keywords if kw.arg is not None}
            try:
                sig.bind(None, *pos_args, **kw_args)
            except TypeError as exc:
                mismatches.append(f"{path.name}:{node.lineno} {'.'.join(chain)}: {exc}")

    assert checked >= 100, f"Expected at least 100 TL calls, only inspected {checked}"
    assert not mismatches, "Telethon TL signature mismatches:\n" + "\n".join(mismatches)


def test_all_telethon_imports_resolve() -> None:
    broken: list[str] = []
    checked = 0

    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module or node.level != 0:
                continue
            if not node.module.startswith("telethon"):
                continue
            checked += 1
            try:
                mod = importlib.import_module(node.module)
            except Exception as exc:
                broken.append(f"{path.name}:{node.lineno} import {node.module}: {exc}")
                continue
            for alias in node.names:
                if alias.name != "*" and not hasattr(mod, alias.name):
                    broken.append(f"{path.name}:{node.lineno} {node.module}.{alias.name} missing")

    assert checked > 0
    assert not broken, "Broken Telethon imports:\n" + "\n".join(broken)
