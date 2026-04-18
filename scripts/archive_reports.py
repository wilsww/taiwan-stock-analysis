#!/usr/bin/env python3
"""Archive reports/ per CLAUDE.md policy.

Rules:
- 日報 (YYYY-MM-DD_日報*.md/html): keep last 7 days
- 月報 (monthly_report_YYYYMM.md): keep last 3 months
- 深度分析/估值/風險 (deep_analysis_/valuation_/risk_check_{ticker?}_YYYYMMDD.md):
  keep latest 2 per ticker (or per type for risk_check which has no ticker)

Run from repo root: python3 scripts/archive_reports.py [--dry-run]
"""
from __future__ import annotations
import argparse
import re
import shutil
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REPORTS = REPO / "reports"
ARCHIVE = REPORTS / "archive"

RE_DAILY = re.compile(r"^(\d{4})-(\d{2})-(\d{2})_日報.*\.(md|html)$")
RE_MONTHLY = re.compile(r"^monthly_report_(\d{4})(\d{2})\.md$")
RE_KEEP_LATEST = re.compile(
    r"^(deep_analysis|valuation|risk_check)_(?:([^_]+)_)?(\d{8})\.md$"
)

def classify(name: str):
    if m := RE_DAILY.match(name):
        y, mo, d, _ = m.groups()
        return "daily", date(int(y), int(mo), int(d))
    if m := RE_MONTHLY.match(name):
        y, mo = m.groups()
        return "monthly", date(int(y), int(mo), 1)
    if m := RE_KEEP_LATEST.match(name):
        kind, ticker, ymd = m.groups()
        dt = datetime.strptime(ymd, "%Y%m%d").date()
        key = f"{kind}:{ticker or '_'}"
        return "keep_latest", (key, dt)
    return None, None

def pick_to_archive(files):
    today = date.today()
    cutoff_daily = today - timedelta(days=7)
    cutoff_monthly = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    cutoff_monthly = (cutoff_monthly.replace(day=1) - timedelta(days=62)).replace(day=1)

    latest_groups = defaultdict(list)
    to_move = []

    for f in files:
        kind, meta = classify(f.name)
        if kind == "daily":
            if meta < cutoff_daily:
                to_move.append(f)
        elif kind == "monthly":
            if meta < cutoff_monthly:
                to_move.append(f)
        elif kind == "keep_latest":
            key, dt = meta
            latest_groups[key].append((dt, f))

    for key, items in latest_groups.items():
        items.sort(key=lambda x: x[0], reverse=True)
        for _, f in items[2:]:
            to_move.append(f)

    return to_move

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not REPORTS.is_dir():
        print(f"no reports dir: {REPORTS}", file=sys.stderr)
        return 1
    ARCHIVE.mkdir(exist_ok=True)

    SUBDIRS = ("daily", "deep_analysis", "valuation", "risk", "sector_flow", "monthly")
    files = []
    for sub in SUBDIRS:
        d = REPORTS / sub
        if d.is_dir():
            files.extend(p for p in d.iterdir() if p.is_file())
    to_move = pick_to_archive(files)

    if not to_move:
        print("nothing to archive")
        return 0

    for f in to_move:
        dest = ARCHIVE / f.name
        if args.dry_run:
            print(f"DRY {f.name} -> archive/")
        else:
            shutil.move(str(f), str(dest))
            print(f"MV  {f.name} -> archive/")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
