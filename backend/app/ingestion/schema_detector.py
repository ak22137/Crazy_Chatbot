"""
Schema detector.
Analyzes DataFrames to infer types, detect primary keys,
categoricals, and generate column-level metadata.
"""

import pandas as pd
import json
import logging
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class ColumnSchema:
    name: str
    data_type: str  # string, integer, float, date, boolean, datetime
    nullable: bool
    is_primary_key: bool = False
    is_categorical: bool = False
    distinct_count: int = 0
    null_count: int = 0
    sample_values: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TableSchema:
    table_name: str
    row_count: int
    column_count: int
    columns: list[ColumnSchema]
    primary_key_candidates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _infer_dtype(series: pd.Series) -> str:
    """Infer a human-readable data type from a pandas Series."""
    dtype_str = str(series.dtype).lower()

    if 'bool' in dtype_str:
        return 'boolean'
    if 'int' in dtype_str:
        return 'integer'
    if 'float' in dtype_str:
        return 'float'
    if 'datetime' in dtype_str:
        return 'datetime'
    if 'date' in dtype_str:
        return 'date'

    # Try to detect date columns stored as strings
    if dtype_str in ('object', 'string'):
        sample = series.dropna().head(20)
        if len(sample) > 0:
            try:
                pd.to_datetime(sample, infer_datetime_format=True)
                return 'datetime'
            except (ValueError, TypeError):
                pass
            # Check if numeric stored as string
            try:
                numeric = pd.to_numeric(sample)
                if all(numeric == numeric.astype(int)):
                    return 'integer'
                return 'float'
            except (ValueError, TypeError):
                pass
    return 'string'


def _get_sample_values(series: pd.Series, n: int = 5) -> list[str]:
    """Get up to n unique sample values from the series."""
    unique = series.dropna().unique()
    samples = unique[:n]
    return [str(v) for v in samples]


def detect_schema(table_name: str, df: pd.DataFrame) -> TableSchema:
    """
    Analyze a DataFrame and produce a full TableSchema with column metadata.

    Args:
        table_name: The name this table will be stored as.
        df: The DataFrame to analyze.

    Returns:
        TableSchema with all column metadata.
    """
    columns: list[ColumnSchema] = []
    pk_candidates: list[str] = []

    for col_name in df.columns:
        series = df[col_name]
        distinct = series.nunique()
        nulls = int(series.isna().sum())
        dtype = _infer_dtype(series)
        nullable = nulls > 0
        is_categorical = (
            dtype == 'string'
            and distinct <= 50
            and distinct < len(df) * 0.5
            and len(df) > 10
        )

        # Primary key: unique, non-null, not float
        if distinct == len(df) and nulls == 0 and dtype != 'float':
            pk_candidates.append(col_name)

        col_schema = ColumnSchema(
            name=col_name,
            data_type=dtype,
            nullable=nullable,
            is_primary_key=False,
            is_categorical=is_categorical,
            distinct_count=distinct,
            null_count=nulls,
            sample_values=_get_sample_values(series),
        )
        columns.append(col_schema)

    # Mark the first PK candidate as primary key
    if pk_candidates:
        for col in columns:
            if col.name == pk_candidates[0]:
                col.is_primary_key = True
                break

    return TableSchema(
        table_name=table_name,
        row_count=len(df),
        column_count=len(df.columns),
        columns=columns,
        primary_key_candidates=pk_candidates,
    )
