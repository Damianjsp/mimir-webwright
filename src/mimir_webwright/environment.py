from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class RunPaths:
    run_dir: Path
    scripts_dir: Path
    screenshots_dir: Path
    log_path: Path
    json_path: Path
    csv_path: Path


@dataclass(frozen=True)
class WorkspaceEnvironment:
    root_dir: Path

    @property
    def workspace_dir(self) -> Path:
        return self.root_dir / "workspace"

    @property
    def scripts_dir(self) -> Path:
        return self.workspace_dir / "scripts"

    @property
    def runs_dir(self) -> Path:
        return self.workspace_dir / "runs"

    def prepare_run(self, task_name: str) -> RunPaths:
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
        run_dir = self.runs_dir / f"{timestamp}_{task_name}"
        screenshots_dir = run_dir / "screenshots"
        for path in (self.workspace_dir, self.scripts_dir, self.runs_dir, run_dir, screenshots_dir):
            path.mkdir(parents=True, exist_ok=True)
        return RunPaths(
            run_dir=run_dir,
            scripts_dir=self.scripts_dir,
            screenshots_dir=screenshots_dir,
            log_path=run_dir / "run.log",
            json_path=run_dir / "results.json",
            csv_path=run_dir / "results.csv",
        )

    def run_python_script(
        self,
        script_path: Path,
        run_paths: RunPaths,
        args: list[str],
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["MIMIR_WEBWRIGHT_RUN_DIR"] = str(run_paths.run_dir)
        env["MIMIR_WEBWRIGHT_SCREENSHOTS_DIR"] = str(run_paths.screenshots_dir)
        env["MIMIR_WEBWRIGHT_RESULTS_JSON"] = str(run_paths.json_path)
        env["MIMIR_WEBWRIGHT_RESULTS_CSV"] = str(run_paths.csv_path)
        process = subprocess.run(
            ["python", str(script_path), *args],
            cwd=str(self.root_dir),
            env=env,
            check=False,
            text=True,
            capture_output=True,
        )
        run_paths.log_path.write_text(
            "STDOUT\n"
            f"{process.stdout}\n\n"
            "STDERR\n"
            f"{process.stderr}",
            encoding="utf-8",
        )
        return process
