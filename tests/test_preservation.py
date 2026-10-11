"""Focused checks for Telegram-safe splitting and exact content recovery."""
import ast
from pathlib import Path
import sys

source_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "main.py"
source = source_path.read_text(encoding="utf-8")
tree = ast.parse(source)
helpers = [
    node for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name in {"telegram_text_units", "split_text_lossless"}
]
namespace = {}
exec(compile(ast.Module(body=helpers, type_ignores=[]), "main.py", "exec"), namespace)
telegram_text_units = namespace["telegram_text_units"]
split_text_lossless = namespace["split_text_lossless"]

samples = [
    "",
    "vless://example.test:443?security=tls#complete",
    ("کانفیگ کامل 🛰️\n" * 900) + "শেষ",
    "🙂" * 12000,
]
for original in samples:
    chunks = split_text_lossless(original)
    assert "".join(chunks) == original
    assert all(telegram_text_units(chunk) <= 3300 for chunk in chunks)

print(f"PASS: exact round-trip for {len(samples)} ASCII, Persian, and Unicode samples")
