#!/usr/bin/env python3
"""Seed the Make MCP server config and editable Hermes skill in HERMES_HOME."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import yaml


INSTALL_DIR = Path(os.environ.get("HERMES_INSTALL_DIR", "/opt/hermes"))
HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/opt/data"))
CONFIG_PATH = HERMES_HOME / "config.yaml"
SKILL_NAME = "make-meta-forms-to-google-sheets-blueprint"
SKILL_SOURCE = (
    INSTALL_DIR
    / "integrations"
    / "make-mcp"
    / "hermes-skills"
    / SKILL_NAME
    / "SKILL.md"
)
SKILL_DEST = HERMES_HOME / "skills" / SKILL_NAME / "SKILL.md"


MAKE_MCP_SERVER = {
    "command": "node",
    "args": ["/opt/hermes/integrations/make-mcp/server.js"],
    "env": {
        "MAKE_API_TOKEN": "${MAKE_API_TOKEN}",
        "MAKE_ZONE": "${MAKE_ZONE}",
        "MAKE_TEAM_ID": "${MAKE_TEAM_ID}",
        "MAKE_ORGANIZATION_ID": "${MAKE_ORGANIZATION_ID}",
    },
    "tools": {
        "include": [
            "make_list_teams",
            "make_get_team",
            "make_list_connections",
            "make_list_hooks",
            "make_ping_hook",
            "make_list_team_scenarios",
            "make_list_organization_scenarios",
            "make_get_scenario",
            "make_get_scenario_blueprint",
            "make_create_meta_lead_ads_hook",
            "make_create_scenario",
            "make_update_scenario",
            "make_disable_hook",
        ],
        "prompts": False,
        "resources": False,
    },
}


def seed_skill() -> None:
    if SKILL_DEST.exists():
        print(f"Make MCP skill already exists at {SKILL_DEST}; preserving local copy")
        return
    if not SKILL_SOURCE.exists():
        print(f"Warning: Make MCP skill source not found at {SKILL_SOURCE}")
        return
    SKILL_DEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SKILL_SOURCE, SKILL_DEST)
    print(f"Seeded editable Make MCP skill at {SKILL_DEST}")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def write_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, sort_keys=False, default_flow_style=False)


def seed_mcp_config() -> None:
    config = load_config()
    servers = config.setdefault("mcp_servers", {})
    if not isinstance(servers, dict):
        print("Warning: config.yaml mcp_servers is not a mapping; leaving it unchanged")
        return
    if "make_local" in servers:
        print("Make MCP server config already exists as mcp_servers.make_local; preserving it")
        return
    servers["make_local"] = MAKE_MCP_SERVER
    write_config(config)
    print("Seeded mcp_servers.make_local in config.yaml")


def main() -> None:
    seed_skill()
    seed_mcp_config()


if __name__ == "__main__":
    main()
