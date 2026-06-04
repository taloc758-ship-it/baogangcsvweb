from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

# Import the application module so PyInstaller bundles its dependencies.
import app as _bundled_app  # noqa: F401


def get_runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def main() -> None:
    base_dir = get_runtime_dir()
    app_path = Path(os.environ.get("CSVWEB_APP_PATH", str(base_dir / "app.py"))).resolve()
    if not app_path.exists():
        raise FileNotFoundError(f"未找到外置 app.py：{app_path}")

    os.chdir(base_dir)
    runpy.run_path(str(app_path), run_name="__main__")


if __name__ == "__main__":
    main()
