"""
Excel / CSV parser.
Reads uploaded files, detects sheets, sanitizes column names,
and returns a list of (sheet_name, DataFrame) tuples.
"""

import pandas as pd
from pathlib import Path
import re
import logging

logger = logging.getLogger(__name__)


def sanitize_column_name(name: str) -> str:
    """Convert column name to safe, lowercase, underscore-separated identifier."""
    name = str(name).strip()
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', '_', name)
    name = name.lower().strip('_')
    if not name or name[0].isdigit():
        name = f"col_{name}"
    return name


def deduplicate_columns(columns: list[str]) -> list[str]:
    """Ensure all column names are unique by appending _N suffix for duplicates."""
    seen: dict[str, int] = {}
    result = []
    for col in columns:
        if col in seen:
            seen[col] += 1
            result.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            result.append(col)
    return result


def parse_file(file_path: str | Path) -> list[tuple[str, pd.DataFrame]]:
    """
    Parse an Excel or CSV file into a list of (sheet_name, DataFrame) tuples.

    Supports: .xlsx, .xls, .csv
    Returns: List of (sheet_name, dataframe) where sheet_name is the Excel
             sheet name or 'sheet1' for CSV files.
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    results: list[tuple[str, pd.DataFrame]] = []

    if suffix == '.csv':
        df = pd.read_csv(file_path, dtype_backend='numpy_nullable')
        df.columns = deduplicate_columns([sanitize_column_name(c) for c in df.columns])
        df = _clean_dataframe(df)
        results.append(("sheet1", df))

    elif suffix in ('.xlsx', '.xls'):
        engine = 'openpyxl' if suffix == '.xlsx' else 'xlrd'
        xls = pd.ExcelFile(file_path, engine=engine)
        for sheet_name in xls.sheet_names:
            try:
                df = pd.read_excel(xls, sheet_name=sheet_name, dtype_backend='numpy_nullable')
                if df.empty or len(df.columns) == 0:
                    logger.warning(f"Skipping empty sheet: {sheet_name}")
                    continue
                df.columns = deduplicate_columns([sanitize_column_name(c) for c in df.columns])
                df = _clean_dataframe(df)
                results.append((sheet_name, df))
            except Exception as e:
                logger.error(f"Error reading sheet '{sheet_name}': {e}")
                continue
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Supported: .xlsx, .xls, .csv")

    return results


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Remove fully empty rows and columns, strip whitespace from string columns."""
    # Drop rows where all values are NaN
    df = df.dropna(how='all')
    # Drop columns where all values are NaN
    df = df.dropna(axis=1, how='all')
    # Strip whitespace from string columns
    for col in df.select_dtypes(include=['object', 'string']).columns:
        df[col] = df[col].astype(str).str.strip().replace('nan', pd.NA)
    return df.reset_index(drop=True)
