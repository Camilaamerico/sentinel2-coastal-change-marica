"""Check the content staged for publication; uses only Python's standard library."""
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 25 * 1024 * 1024
FIGURES = {
    f"outputs/figures/{name}.png" for name in (
        "mndwi_comparison", "mndwi_change_comparison",
        "ndvi_comparison", "ndvi_change_comparison",
        "ndwi_comparison", "ndwi_change_comparison",
        "recanto_mndwi_overview", "recanto_overview_zoom",
    )
}
PRODUCTS = FIGURES | {
    "outputs/tables/change_summary.csv",
    "outputs/tables/recanto_change_summary.csv",
    *(f"outputs/vectors/recanto_waterlines/waterline_mndwi_{y}.geojson"
      for y in (2019, 2022, 2025)),
}


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def forbidden(name):
    path = PurePosixPath(name)
    parts = {p.lower() for p in path.parts}
    excluded = {".venv", "venv", "env", "__pycache__", ".pytest_cache",
                ".mypy_cache", ".ruff_cache", ".ipynb_checkpoints", ".cache",
                "work", "tmp", "temp", "build", "dist", ".idea", ".vscode"}
    if parts & excluded or any(p.endswith(".safe") for p in parts):
        return True
    if name.startswith(("data/raw/", "data/processed/")):
        return name not in {"data/raw/.gitkeep", "data/processed/.gitkeep"}
    if name.startswith("outputs/"):
        return name not in PRODUCTS
    if name in {"src/change_summary.csv", "project_tree.txt"}:
        return True
    if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
        return True
    return path.suffix.lower() in {
        ".tif", ".tiff", ".jp2", ".zip", ".7z", ".gz", ".tar",
        ".pyc", ".pyo", ".pyd", ".log", ".tmp", ".temp", ".bak",
        ".ovr", ".pem", ".key",
    } or name.endswith(".aux.xml")


def main():
    try:
        records = git("ls-files", "--stage", "-z").split(b"\0")
    except subprocess.CalledProcessError:
        print("Initialize Git and stage the intended files before running this check.")
        return 1
    problems, names, total = [], set(), 0
    for record in filter(None, records):
        meta, raw_name = record.split(b"\t", 1)
        mode, oid, stage = meta.decode().split()
        name = raw_name.decode("utf-8")
        names.add(name)
        if stage != "0" or mode not in {"100644", "100755"}:
            problems.append(f"Unmerged or non-regular file: {name}")
            continue
        size = int(git("cat-file", "-s", oid))
        total += size
        if forbidden(name):
            problems.append(f"Local/generated file staged: {name}")
        if size > MAX_BYTES:
            problems.append(f"File exceeds 25 MiB: {name} ({size} bytes)")
    for missing in sorted(PRODUCTS - names):
        problems.append(f"Missing final product: {missing}")
    if git("diff", "--name-only"):
        problems.append("Unstaged changes exist. Review and stage the intended version before publication.")
    print(f"Staged: {len(names)} files, {total / 1024**2:.2f} MiB")
    if problems:
        print("\n".join(problems))
        return 1
    print("Publication file checks passed; review git diff --cached before committing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
