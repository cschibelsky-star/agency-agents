#!/usr/bin/env python3
"""Instalador local opt-in de perfis consultivos; padrao dry-run, sem overwrite."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def profile(md: str) -> tuple[dict[str, str], str]:
    if not md.startswith("---\n"):
        raise ValueError("frontmatter ausente")
    parts = md.split("---\n", 2)
    if len(parts) != 3:
        raise ValueError("frontmatter invalido")
    metadata: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"')
    body = parts[2].strip()
    if not metadata.get("name") or not metadata.get("description") or not body:
        raise ValueError("perfil incompleto")
    return metadata, body


def render(md: str, tool: str) -> str:
    data, body = profile(md)
    if tool == "claude-code":
        return md
    if tool == "codex":
        return "\n".join(
            [
                "name = " + json.dumps(data["name"], ensure_ascii=False),
                "description = " + json.dumps(data["description"], ensure_ascii=False),
                "developer_instructions = " + json.dumps(body, ensure_ascii=False),
                "",
            ]
        )
    raise ValueError("tool nao suportada")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", required=True, choices=["claude-code", "codex"])
    parser.add_argument("--dest", required=True, type=Path, help="diretorio local explicito")
    parser.add_argument("--apply", action="store_true", help="escrever; padrao e dry-run")
    args = parser.parse_args(argv)
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("execution_enabled") is not False:
        raise ValueError("overlay nao esta em modo seguro")
    if manifest.get("governance", {}).get("dispatch_allowed") is not False:
        raise ValueError("despacho nao pode ser habilitado")
    items: list[tuple[Path, str]] = []
    suffix = ".md" if args.tool == "claude-code" else ".toml"
    target_dir = args.dest.expanduser()
    for agent in manifest["agents"]:
        agent_id = agent["id"]
        if not agent_id.startswith("vitrine-") or "/" in agent_id or "\\" in agent_id:
            raise ValueError("id de agente invalido")
        source = (ROOT / agent["file"]).resolve()
        if not source.is_relative_to((ROOT / "agents").resolve()):
            raise ValueError("arquivo fora de agents")
        md = source.read_text(encoding="utf-8")
        meta, _ = profile(md)
        if meta["name"] != agent["name"]:
            raise ValueError("nome inconsistente com manifesto")
        items.append((target_dir / (agent_id + suffix), render(md, args.tool)))
    for target, _ in items:
        print(("GRAVAR" if args.apply else "PREVISUALIZAR") + ": " + str(target))
    if not args.apply:
        return 0
    existing = [str(target) for target, _ in items if target.exists()]
    if existing:
        print("BLOQUEADO: arquivos ja existentes: " + ", ".join(existing), file=sys.stderr)
        return 2
    target_dir.mkdir(parents=True, exist_ok=True)
    for target, content in items:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
