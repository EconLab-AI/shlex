# brain/context_engine.py
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProjectContext:
    claude_md: str = ""
    git_log: str = ""
    git_status: str = ""
    git_diff: str = ""
    file_structure: list[str] = field(default_factory=list)
    memory_files: dict[str, str] = field(default_factory=dict)
    active_tmux_sessions: list[str] = field(default_factory=list)
    error_memories: list[str] = field(default_factory=list)

    def to_prompt_section(self) -> str:
        parts = ["# Projektkontext"]
        if self.claude_md:
            parts.append(f"\n## CLAUDE.md Regeln\n{self.claude_md}")
        if self.git_status:
            parts.append(f"\n## Git Status\n```\n{self.git_status}\n```")
        if self.git_log:
            parts.append(f"\n## Letzte Commits\n```\n{self.git_log}\n```")
        if self.git_diff:
            parts.append(f"\n## Unstaged Changes\n```\n{self.git_diff[:2000]}\n```")
        if self.file_structure:
            tree = "\n".join(self.file_structure[:100])
            parts.append(f"\n## Dateistruktur\n```\n{tree}\n```")
        if self.error_memories:
            errs = "\n".join(f"- {e}" for e in self.error_memories)
            parts.append(f"\n## Fehler-History (NICHT WIEDERHOLEN!)\n{errs}")
        return "\n".join(parts)


class ContextEngine:
    def __init__(self, project_path: str) -> None:
        self._path = Path(project_path)

    async def load_context(self) -> ProjectContext:
        ctx = ProjectContext()
        ctx.claude_md = self._read_file("CLAUDE.md")
        ctx.file_structure = self._scan_files()
        if (self._path / ".git").exists():
            ctx.git_log = await self._run_git("log", "--oneline", "-20")
            ctx.git_status = await self._run_git("status", "--short")
            ctx.git_diff = await self._run_git("diff")
        ctx.memory_files = self._load_memory_files()
        ctx.active_tmux_sessions = await self._list_tmux()
        return ctx

    def _read_file(self, name: str) -> str:
        path = self._path / name
        if path.exists():
            return path.read_text(errors="replace")[:5000]
        return ""

    def _scan_files(self) -> list[str]:
        result = []
        for root, dirs, files in os.walk(self._path):
            dirs[:] = [
                d for d in dirs
                if d not in {".git", ".venv", "venv", "__pycache__", "node_modules", ".next"}
            ]
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), self._path)
                result.append(rel)
            if len(result) > 200:
                break
        return sorted(result)

    def _load_memory_files(self) -> dict[str, str]:
        memory_dir = self._path / ".claude" / "memory"
        if not memory_dir.exists():
            return {}
        result = {}
        for f in memory_dir.glob("*.md"):
            result[f.name] = f.read_text(errors="replace")[:3000]
        return result

    async def _run_git(self, *args: str) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", *args,
                cwd=str(self._path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            return stdout.decode(errors="replace").strip()
        except Exception:
            return ""

    async def _list_tmux(self) -> list[str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "tmux", "list-sessions", "-F", "#{session_name}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            return [line for line in stdout.decode().strip().split("\n") if line]
        except Exception:
            return []
