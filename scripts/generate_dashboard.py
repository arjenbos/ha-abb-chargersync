"""Customize the native Lovelace dashboard without connecting to Home Assistant."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "dashboards/chargersync.yaml"
ENTITY_PATTERN = re.compile(
    r"\b(?:sensor|binary_sensor|button|number|select|switch|lock)\.charger_[a-z0-9_]+\b"
)


class DashboardDumper(yaml.SafeDumper):
    def ignore_aliases(self, data: Any) -> bool:
        return True


def _text(dumper: yaml.SafeDumper, value: str):
    return dumper.represent_scalar(
        "tag:yaml.org,2002:str", value, style="|" if "\n" in value else None
    )


DashboardDumper.add_representer(str, _text)


def customize(value: Any, prefix: str, name: str, mapping: dict[str, str]) -> Any:
    """Replace entity IDs in cards, conditions, actions, and Markdown templates."""
    if isinstance(value, dict):
        return {key: customize(item, prefix, name, mapping) for key, item in value.items()}
    if isinstance(value, list):
        return [customize(item, prefix, name, mapping) for item in value]
    if isinstance(value, str):
        return ENTITY_PATTERN.sub(
            lambda match: mapping.get(match[0], match[0].replace(".charger_", f".{prefix}_", 1)),
            value,
        ).replace("CHARGER_DISPLAY_NAME", name)
    return value


def generate(prefix: str, name: str, mapping: dict[str, str] | None = None) -> dict:
    if not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", prefix):
        raise ValueError(
            "Entity prefix must contain lowercase letters, numbers and single underscores"
        )
    if not name.strip() or any(c in name for c in "\r\n{}<>"):
        raise ValueError("Charger name must be plain text on a single line")
    mapping = mapping or {}
    template = yaml.safe_load(TEMPLATE.read_text())
    template_entities = set(ENTITY_PATTERN.findall(TEMPLATE.read_text()))
    for source, target in mapping.items():
        if not isinstance(source, str) or source not in template_entities:
            raise ValueError(f"Unknown template entity ID: {source}")
        if not isinstance(target, str) or not re.fullmatch(r"[a-z_]+\.[a-z0-9_]+", target):
            raise ValueError(f"Invalid target entity ID for {source}")
        if source.split(".")[0] != target.split(".")[0]:
            raise ValueError(f"Entity domains must match for {source}")
    return customize(template, prefix, name.strip(), mapping)


def generate_from_registry(path: Path, name: str, status_entity: str | None = None) -> dict:
    """Match original integration names within one device, including renamed IDs."""
    registry = json.loads(path.read_text())
    entries = [e for e in registry["data"]["entities"] if e.get("platform") == "abb_chargersync"]
    candidates = [e for e in entries if e.get("original_name") == "Charging status"]
    if status_entity:
        candidates = [e for e in candidates if e["entity_id"] == status_entity]
    if len(candidates) != 1 or not candidates[0].get("device_id"):
        raise ValueError("Select exactly one charger's charging-status entity with --status-entity")
    status = candidates[0]
    template_entities = set(ENTITY_PATTERN.findall(TEMPLATE.read_text()))
    mapping = {}
    for entry in entries:
        if entry.get("device_id") != status["device_id"]:
            continue
        domain = entry["entity_id"].split(".")[0]
        slug = re.sub(r"[^a-z0-9]+", "_", (entry.get("original_name") or "").lower()).strip("_")
        source = f"{domain}.charger_{slug}"
        if source in template_entities:
            if source in mapping:
                raise ValueError(f"Multiple entities match {source}; use an explicit entity map")
            mapping[source] = entry["entity_id"]
    prefix = status["entity_id"].split(".")[1].removesuffix("_charging_status")
    return generate(prefix, name, mapping)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entity-prefix", help="For sensor.driveway_charging_status, use driveway")
    parser.add_argument(
        "--from-registry", type=Path, help="Read only the HA entity registry to match actual IDs"
    )
    parser.add_argument(
        "--status-entity", help="Choose the charger when the registry contains multiple chargers"
    )
    parser.add_argument("--name", default="Home charger", help="Dashboard heading")
    parser.add_argument(
        "--entity-map",
        type=Path,
        help="Optional JSON object mapping template IDs to actual entity IDs",
    )
    parser.add_argument("--output", type=Path, required=True, help="Destination dashboard YAML")
    args = parser.parse_args()
    try:
        mapping = json.loads(args.entity_map.read_text()) if args.entity_map else {}
        if not isinstance(mapping, dict):
            raise ValueError("Entity map must be a JSON object")
        if args.from_registry:
            if args.entity_prefix or args.entity_map:
                raise ValueError("Use --from-registry without --entity-prefix or --entity-map")
            config = generate_from_registry(args.from_registry, args.name, args.status_entity)
        elif args.entity_prefix:
            config = generate(args.entity_prefix, args.name, mapping)
        else:
            raise ValueError("Provide --entity-prefix or --from-registry")
    except (ValueError, KeyError, OSError) as err:
        parser.error(str(err))
    if args.output.resolve() == TEMPLATE:
        parser.error("Choose an output path other than the source template")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.dump(config, Dumper=DashboardDumper, sort_keys=False, allow_unicode=True)
    )
    print(f"Created dashboard: {args.output}")


if __name__ == "__main__":
    main()
