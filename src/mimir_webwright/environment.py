"""Workspace-aware command execution utilities."""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path


class Environment:
    """Run commands and manage generated scripts and run artifacts."""

    def __init__(self, workspace_dir: str = "workspace") -> None:
        self.workspace = Path(workspace_dir)
        self.workspace.mkdir(exist_ok=True)
        (self.workspace / "scripts").mkdir(exist_ok=True)
        (self.workspace / "runs").mkdir(exist_ok=True)

    def run(self, command: str, timeout: int = 60) -> str:
        """Execute a shell command in the workspace and return combined output."""
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(self.workspace),
            check=False,
        )
        return result.stdout + result.stderr

    def save_script(self, name: str, content: str) -> Path:
        """Persist a generated Python script in the scripts directory."""
        path = self.workspace / "scripts" / f"{name}.py"
        path.write_text(content, encoding="utf-8")
        return path

    def new_run(self) -> Path:
        """Create and return a timestamped run directory."""
        run_dir = self.workspace / "runs" / datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir.mkdir(parents=True)
        return run_dir
