#!/usr/bin/env python3
"""CLI entry point for Shared Skills Bridge.

Usage:
    python scripts/install.py --source ./shared-skills --target kimi
    python scripts/install.py --source ./shared-skills --target hermes --mode link
    python scripts/install.py --source ./shared-skills --target both --check
    python scripts/install.py --source ./shared-skills --target both --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running directly without package installation
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bidirectional import (
    discover_hermes_additions,
    discover_kimi_additions,
    sync_hermes_to_shared,
    sync_kimi_to_shared,
    update_baseline,
    update_kimi_baseline,
)
from src.installer import InstallResult, check_sync, install_skill, resolve_target_dir
from src.models import InstallMode, Platform
from src.scanner import scan_skills


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Share AI skills between Kimi Code CLI and Hermes Agent",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("shared-skills"),
        help="Source directory containing shared skills (default: ./shared-skills)",
    )
    parser.add_argument(
        "--target",
        choices=["kimi", "hermes", "both"],
        required=False,
        help="Target platform to install skills to",
    )
    parser.add_argument(
        "--mode",
        choices=["copy", "link"],
        default="copy",
        help="Installation mode: copy files or create symlinks (default: copy)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check for differences without installing",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing skills",
    )
    parser.add_argument(
        "--bidirectional",
        action="store_true",
        help="Also sync skills created directly in Hermes back to shared source and then to Kimi",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update both Hermes and Kimi baselines to current state",
    )
    return parser.parse_args()


def _install_to_platform(
    skills: list,
    platform: Platform,
    mode: InstallMode,
    force: bool,
) -> int:
    """Install all skills to a single platform. Returns exit code."""
    target_dir = resolve_target_dir(platform)
    print(f"\n[DIR] Target: {target_dir} ({platform.value})")

    copied = skipped = linked = errors = 0

    for skill in skills:
        result = install_skill(skill, platform, mode, force)
        if result is InstallResult.COPIED:
            print(f"  [OK] {skill.name}")
            copied += 1
        elif result is InstallResult.LINKED:
            print(f"  [LINK] {skill.name}")
            linked += 1
        elif result is InstallResult.SKIPPED:
            print(f"  [SKIP] {skill.name} (exists, use --force to overwrite)")
            skipped += 1
        else:
            print(f"  [ERR] {skill.name} (error)")
            errors += 1

    print(
        f"\nSummary: {copied} copied, {linked} linked, {skipped} skipped, {errors} errors"
    )
    return 1 if errors else 0


def _check_platform(skills: list, platform: Platform) -> None:
    """Print sync differences for a platform."""
    diffs = check_sync(skills, platform)
    if not diffs:
        print(f"  ✨ {platform.value}: up to date")
        return

    print(f"\n[DIFF] Differences for {platform.value}:")
    for diff in diffs:
        icon = "[ADD]" if diff.status == "ADD" else "[UPD]"
        print(f"  {icon} {diff.skill_name}: {diff.status}")


def main() -> int:
    args = _parse_args()
    source_dir = args.source.resolve()

    if not source_dir.exists():
        print(f"Error: source directory does not exist: {source_dir}", file=sys.stderr)
        return 1

    # Handle baseline update only
    if args.update_baseline:
        update_baseline()
        update_kimi_baseline()
        print("[BASELINE] Hermes and Kimi baselines updated to current state.")
        return 0

    if not args.target:
        print("Error: --target is required (unless using --update-baseline)", file=sys.stderr)
        return 1

    # Optional: reverse sync from both platforms to shared source
    if args.bidirectional:
        # Hermes side
        print("[BIDIR] Scanning Hermes for new skills...")
        hermes_additions = discover_hermes_additions()
        if hermes_additions:
            print(f"[BIDIR] Found {len(hermes_additions)} new skill(s) in Hermes:")
            for s in hermes_additions:
                print(f"   - {s.name}")
            copied = sync_hermes_to_shared(hermes_additions, source_dir)
            if copied:
                print(f"[BIDIR] Copied to shared source: {', '.join(copied)}")
        else:
            print("[BIDIR] No new Hermes skills detected.")

        # Kimi side
        print("[BIDIR] Scanning Kimi for new skills...")
        kimi_additions = discover_kimi_additions()
        if kimi_additions:
            print(f"[BIDIR] Found {len(kimi_additions)} new skill(s) in Kimi:")
            for s in kimi_additions:
                print(f"   - {s.name}")
            copied = sync_kimi_to_shared(kimi_additions, source_dir)
            if copied:
                print(f"[BIDIR] Copied to shared source: {', '.join(copied)}")
        else:
            print("[BIDIR] No new Kimi skills detected.")
        print()

    skills = scan_skills(source_dir)
    if not skills:
        print(f"No valid skills found in {source_dir}")
        return 0

    print(f"[SCAN] Found {len(skills)} skill(s) in {source_dir}")
    for s in skills:
        print(f"   - {s.name}")

    mode = InstallMode(args.mode)
    platforms: list[Platform] = []
    if args.target == "kimi":
        platforms = [Platform.KIMI]
    elif args.target == "hermes":
        platforms = [Platform.HERMES]
    else:
        platforms = [Platform.KIMI, Platform.HERMES]

    if args.check:
        for plat in platforms:
            _check_platform(skills, plat)
        return 0

    exit_code = 0
    for plat in platforms:
        code = _install_to_platform(skills, plat, mode, args.force)
        exit_code = max(exit_code, code)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
