"""Aggregate-only inventory of the OpenOximetry download.

Usage:
    python scripts/inventory.py <data_dir> [--out inventory_report.txt]

The report contains no subject-level rows: file counts, column names and
types, missingness, percentiles, and category counts with small cells
suppressed. Digits in file and folder names are masked so IDs embedded in
paths do not appear. Review the report before sharing it.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

SMALL_CELL = 5  # counts below this are reported as "<5"
MAX_CATEGORIES = 20  # columns with more distinct values get no value listing
MIN_N_FOR_PERCENTILES = 20
BIG_FILE_BYTES = 250 * 1024**2
BIG_FILE_ROWS = 500_000
TABULAR_SUFFIXES = (".csv", ".tsv", ".csv.gz", ".tsv.gz")
ID_COLUMN = re.compile(r"(subject|patient|participant)", re.IGNORECASE)
GROUP_COLUMN = re.compile(r"(subject|patient|participant|encounter|session|device)", re.IGNORECASE)


def mask(text: str) -> str:
    return re.sub(r"\d", "#", text)


def suffix_of(path: Path) -> str:
    name = path.name.lower()
    for suffix in TABULAR_SUFFIXES:
        if name.endswith(suffix):
            return suffix
    return path.suffix.lower() or "(none)"


def human(n_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024 or unit == "GB":
            return f"{n_bytes:,.1f} {unit}"
        n_bytes /= 1024
    return ""


def suppress(count: int) -> str:
    return f"<{SMALL_CELL}" if count < SMALL_CELL else f"{count:,}"


def file_tree(data_dir: Path, lines: list[str]) -> list[Path]:
    """Summarise files by masked folder and extension; return tabular files."""
    counts: Counter = Counter()
    sizes: Counter = Counter()
    examples: dict = defaultdict(set)
    tabular: list[Path] = []
    for path in sorted(data_dir.rglob("*")):
        if not path.is_file():
            continue
        suffix = suffix_of(path)
        key = (mask(str(path.parent.relative_to(data_dir))), suffix)
        counts[key] += 1
        sizes[key] += path.stat().st_size
        if len(examples[key]) < 3:
            examples[key].add(mask(path.name))
        if suffix in TABULAR_SUFFIXES:
            tabular.append(path)

    lines.append("== FILE TREE (digits masked as #) ==")
    lines.append(f"total: {sum(counts.values()):,} files, {human(sum(sizes.values()))}")
    for key in sorted(counts):
        folder, suffix = key
        lines.append(f"\n[{folder}]  {suffix}  n={counts[key]:,}  size={human(sizes[key])}")
        lines.append(f"    e.g. {', '.join(sorted(examples[key]))}")
    return tabular


def describe_column(df: pd.DataFrame, name: str, id_col: str | None) -> list[str]:
    col = df[name]
    n = len(col)
    non_null = int(col.notna().sum())
    n_unique = int(col.nunique(dropna=True))
    pct = 100 * non_null / n if n else 0.0
    out = [f"  - {name}  [{col.dtype}]  non-null {pct:.1f}%  distinct {n_unique:,}"]

    numeric = pd.api.types.is_numeric_dtype(col) and not pd.api.types.is_bool_dtype(col)
    if numeric and non_null >= MIN_N_FOR_PERCENTILES and n_unique > MAX_CATEGORIES:
        p5, p50, p95 = col.quantile([0.05, 0.5, 0.95])
        out.append(f"      p5={p5:.4g}  p50={p50:.4g}  p95={p95:.4g}")

    # List values only for genuinely categorical columns, never free text or IDs.
    categorical = 0 < n_unique <= MAX_CATEGORIES and n_unique * 5 <= max(non_null, 1)
    if categorical and name != id_col:
        if id_col:
            tally = df.groupby(name, dropna=True)[id_col].nunique()
            unit = "subjects"
        else:
            tally = col.value_counts(dropna=True)
            unit = "rows"
        cells = [f"{value!r}: {suppress(int(count))}" for value, count in tally.sort_index().items()]
        out.append(f"      {unit} per value: " + "; ".join(cells))
    return out


def describe_table(path: Path, n_files: int, data_dir: Path, lines: list[str]) -> None:
    rel = mask(str(path.relative_to(data_dir)))
    size = path.stat().st_size
    sep = "\t" if ".tsv" in path.name.lower() else ","
    sampled = size > BIG_FILE_BYTES
    lines.append(f"\n--- {rel}  ({human(size)}; {n_files:,} file(s) share this layout) ---")
    try:
        df = pd.read_csv(path, sep=sep, nrows=BIG_FILE_ROWS if sampled else None, low_memory=False)
    except Exception as exc:  # message may quote data values, so report the type only
        lines.append(f"  could not read: {type(exc).__name__}")
        return

    note = f" (first {BIG_FILE_ROWS:,} rows only)" if sampled else ""
    lines.append(f"  rows: {len(df):,}{note}   columns: {df.shape[1]}")

    id_col = next((c for c in df.columns if ID_COLUMN.search(str(c))), None)
    for name in df.columns:
        if not GROUP_COLUMN.search(str(name)):
            continue
        per_group = df.groupby(name, dropna=True).size()
        if len(per_group) >= MIN_N_FOR_PERCENTILES:
            p5, p50, p95 = per_group.quantile([0.05, 0.5, 0.95])
            lines.append(
                f"  rows per {name}: {len(per_group):,} groups, p5={p5:.0f} p50={p50:.0f} p95={p95:.0f}"
            )
    for name in df.columns:
        lines.extend(describe_column(df, name, id_col))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("--out", type=Path, default=Path("inventory_report.txt"))
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    out = args.out.resolve()
    if not data_dir.is_dir():
        print(f"not a directory: {data_dir}")
        return 1
    if data_dir == out.parent or data_dir in out.parents:
        print("refusing to write the report inside the data directory")
        return 1

    lines: list[str] = []
    tabular = file_tree(data_dir, lines)

    # Per-subject files usually share one layout; describe one file per layout.
    layouts: dict = defaultdict(list)
    for path in tabular:
        sep = "\t" if ".tsv" in path.name.lower() else ","
        try:
            header = tuple(pd.read_csv(path, sep=sep, nrows=0).columns)
        except Exception:
            header = ("(unreadable)",)
        layouts[(mask(str(path.parent.relative_to(data_dir))), header)].append(path)

    lines.append("\n\n== TABLES (one representative file per folder + column layout) ==")
    for paths in layouts.values():
        describe_table(max(paths, key=lambda p: p.stat().st_size), len(paths), data_dir, lines)

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
