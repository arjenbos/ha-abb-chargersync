"""Build an installable ZIP without APKs, virtualenvs, caches or account data."""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    component = root / "custom_components/abb_chargersync"
    sources = sorted(
        p
        for p in component.rglob("*")
        if p.is_file() and p.suffix in {".py", ".json", ".yaml", ".png", ".js"}
    )
    sources += [
        root / p
        for p in (
            "README.md",
            "compose.yaml",
            ".env.example",
            "development/configuration.yaml",
            "docs/local-testing.md",
            "docs/actions.md",
            "docs/implementation.md",
            "docs/branding.md",
            "docs/dashboard.md",
            "scripts/generate_dashboard.py",
        )
    ]
    sources += sorted((root / "docs/assets").glob("*.xml"))
    sources += sorted((root / "dashboards").glob("*.yaml"))
    sources += sorted((root / "docs/assets").glob("dashboard-preview.*"))
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.destination, "w", ZIP_DEFLATED) as archive:
        for source in sources:
            archive.write(source, source.relative_to(root))
    print(f"Packaged {len(sources)} files: {args.destination}")


if __name__ == "__main__":
    main()
