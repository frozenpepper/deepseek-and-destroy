#!/usr/bin/env python3
"""Detect the current orchestrator harness and describe checkpoint capabilities.

Detection is conservative. An explicit --harness or DSD_ORCHESTRATOR_HARNESS
wins. When evidence is ambiguous, the script reports candidates rather than
silently choosing the wrong adapter.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Iterable

KNOWN = {"codex", "claude-code", "opencode", "kilo", "unknown"}


def parent_commands(limit: int = 8) -> list[str]:
    commands: list[str] = []
    pid = os.getpid()
    for _ in range(limit):
        try:
            out = subprocess.check_output(
                ["ps", "-o", "ppid=,command=", "-p", str(pid)],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except Exception:
            break
        if not out:
            break
        parts = out.split(None, 1)
        if len(parts) != 2:
            break
        ppid, command = parts
        commands.append(command)
        try:
            pid = int(ppid)
        except ValueError:
            break
        if pid <= 1:
            break
    return commands


def score_candidates(commands: Iterable[str]) -> dict[str, int]:
    env = os.environ
    scores = {"codex": 0, "claude-code": 0, "opencode": 0, "kilo": 0}

    explicit = env.get("DSD_ORCHESTRATOR_HARNESS", "").strip().lower()
    if explicit in scores:
        scores[explicit] += 100

    if env.get("CODEX_HOME") or env.get("CODEX_THREAD_ID") or env.get("CODEX_SESSION_ID"):
        scores["codex"] += 5
    if env.get("CLAUDE_PROJECT_DIR") or env.get("CLAUDE_ENV_FILE") or env.get("CLAUDE_CODE_ENTRYPOINT"):
        scores["claude-code"] += 5
    if env.get("OPENCODE_DB") or env.get("OPENCODE_CONFIG") or env.get("OPENCODE_CLIENT"):
        scores["opencode"] += 5
    # KILO_BIN_PATH/KILO_BWRAP_CACHE exist in the installed CLI's own code but are
    # not confirmed to be exported into every child-process environment; treat as
    # a weak secondary signal only, same weight as the other harnesses' env checks.
    if env.get("KILO_BIN_PATH") or env.get("KILO_BWRAP_CACHE"):
        scores["kilo"] += 5

    joined = "\n".join(commands).lower()
    if "codex" in joined:
        scores["codex"] += 8
    if "claude" in joined:
        scores["claude-code"] += 8
    if "opencode" in joined:
        scores["opencode"] += 8
    if "kilo" in joined:
        scores["kilo"] += 8
    return scores


def capabilities(harness: str) -> dict[str, object]:
    base: dict[str, object] = {
        "harness": harness,
        "checkpoint_core": True,
        "exact_context_percent_required": False,
        "safe_boundary_fallback": True,
    }
    if harness == "codex":
        base.update(
            {
                "precompact_hook": True,
                "postcompact_hook": True,
                "postcompact_context_injection": True,
                "manual_compaction": True,
                "configurable_auto_compact_token_limit": True,
                "adapter": "CODEX.md",
            }
        )
    elif harness == "claude-code":
        base.update(
            {
                "precompact_hook": True,
                "postcompact_hook": True,
                "postcompact_context_injection": True,
                "manual_compaction": True,
                "configurable_auto_compact_token_limit": False,
                "adapter": "CLAUDE.md",
            }
        )
    elif harness == "opencode":
        base.update(
            {
                "precompact_hook": True,
                "postcompact_hook": False,
                "postcompact_context_injection": "skill-state invariant",
                "manual_compaction": True,
                "configurable_auto_compact_token_limit": "buffer/keep, not percentage",
                "adapter": "OPENCODE.md",
            }
        )
    elif harness == "kilo":
        base.update(
            {
                # Kilo's own @kilocode/plugin package declares
                # "experimental.session.compacting" with the same input/output
                # shape OpenCode's plugin interface uses. Package, export
                # shape, hook signature, ctx fields, and .kilo/plugins/*.ts
                # auto-discovery are confirmed against @kilocode/plugin 7.4.20
                # and a live `kilo serve` session (plugin instantiated on
                # session creation). NOT confirmed: the hook firing during a
                # real mid-session compaction event -- do not upgrade these to
                # True without that specific empirical verification.
                "precompact_hook": "experimental, wired+loadable; live-fire unconfirmed",
                "postcompact_hook": "experimental, autocontinue hook declared but unused; live-fire unconfirmed",
                "postcompact_context_injection": "experimental, live-fire unconfirmed",
                "manual_compaction": True,
                "configurable_auto_compact_token_limit": False,
                "adapter": "KILOCODE.md",
            }
        )
    else:
        base.update(
            {
                "precompact_hook": False,
                "postcompact_hook": False,
                "postcompact_context_injection": False,
                "manual_compaction": "unknown",
                "configurable_auto_compact_token_limit": False,
                "adapter": "COMPACTION.md generic fallback",
            }
        )
    return base


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--harness", choices=sorted(KNOWN - {"unknown"}), help="Explicit harness")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    commands = parent_commands()
    scores = score_candidates(commands)
    if args.harness:
        selected = args.harness
        confidence = "explicit"
    else:
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if ranked[0][1] <= 0 or (len(ranked) > 1 and ranked[0][1] == ranked[1][1]):
            selected = "unknown"
            confidence = "ambiguous"
        else:
            selected = ranked[0][0]
            confidence = "detected"

    result = {
        "selected": selected,
        "confidence": confidence,
        "scores": scores,
        "parent_commands": commands,
        "capabilities": capabilities(selected),
        "instruction": (
            "Use an explicit harness from the current session/system context when detection is ambiguous. "
            "Do not choose merely because another CLI is installed."
        ),
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"HARNESS={selected}")
        print(f"CONFIDENCE={confidence}")
        print(f"ADAPTER={result['capabilities']['adapter']}")
        if selected == "unknown":
            print("AMBIGUOUS: set DSD_ORCHESTRATOR_HARNESS or pass --harness.")
    return 0 if selected != "unknown" else 3


if __name__ == "__main__":
    raise SystemExit(main())
