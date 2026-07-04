"""CSV and PDF file ingestion with graceful degradation."""
import io
from typing import Any
import pandas as pd
import pdfplumber


REQUIRED_COLUMN_HINTS = {
    "amount": ["amount", "total", "value", "price", "cost"],
    "vendor": ["vendor", "supplier", "payee", "merchant", "company"],
    "date": ["date", "transaction_date", "invoice_date", "timestamp"],
    "invoice_id": ["invoice_id", "invoice", "invoice_no", "id", "ref"],
    "category": ["category", "type", "expense_type", "department"],
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase column names, strip whitespace."""
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


def detect_canonical_columns(df: pd.DataFrame) -> dict[str, str | None]:
    """Map dataset columns to canonical financial columns."""
    mapping: dict[str, str | None] = {}
    cols = list(df.columns)
    for canonical, hints in REQUIRED_COLUMN_HINTS.items():
        found = None
        for col in cols:
            col_low = col.lower()
            if any(h in col_low for h in hints):
                found = col
                break
        mapping[canonical] = found
    return mapping


def coerce_numeric(series: pd.Series) -> pd.Series:
    """Strip currency symbols and convert to float."""
    if series.dtype.kind in "if":
        return series
    cleaned = (
        series.astype(str)
        .str.replace(r"[$,€£¥\s]", "", regex=True)
        .str.replace(r"[()]", "-", regex=True)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def parse_csv(content: bytes, chunk_size: int = 50000) -> dict[str, Any]:
    """Parse CSV with chunked processing for large files."""
    try:
        df_full = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        return {"ok": False, "error": f"Failed to read full CSV: {e}"}

    df_full = normalize_columns(df_full)
    canonical = detect_canonical_columns(df_full)

    # Numeric coercion of amount column
    if canonical.get("amount") and canonical["amount"] in df_full.columns:
        df_full[canonical["amount"]] = coerce_numeric(df_full[canonical["amount"]])

    preview = df_full.head(20).fillna("").to_dict(orient="records")
    # Coerce non-serializable types
    preview_clean = []
    for row in preview:
        preview_clean.append({k: (str(v) if not isinstance(v, (int, float, str, bool)) else v) for k, v in row.items()})

    return {
        "ok": True,
        "row_count": int(len(df_full)),
        "column_count": int(len(df_full.columns)),
        "columns": list(df_full.columns),
        "canonical_mapping": canonical,
        "preview": preview_clean,
        "dataframe": df_full,
    }


def parse_pdf(content: bytes) -> dict[str, Any]:
    """Extract text and tables from PDF."""
    try:
        rows: list[dict[str, Any]] = []
        all_text: list[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_text.append(text)
                tables = page.extract_tables() or []
                for tbl in tables:
                    if not tbl or len(tbl) < 2:
                        continue
                    header = [str(c).strip().lower().replace(" ", "_") if c else f"col_{i}" for i, c in enumerate(tbl[0])]
                    for r in tbl[1:]:
                        row_dict = {header[i]: (str(c).strip() if c else "") for i, c in enumerate(r) if i < len(header)}
                        rows.append(row_dict)

        if rows:
            df = pd.DataFrame(rows)
            df = normalize_columns(df)
            canonical = detect_canonical_columns(df)
            if canonical.get("amount") and canonical["amount"] in df.columns:
                df[canonical["amount"]] = coerce_numeric(df[canonical["amount"]])
            preview = df.head(20).fillna("").to_dict(orient="records")
            preview_clean = [{k: (str(v) if not isinstance(v, (int, float, str, bool)) else v) for k, v in row.items()} for row in preview]
            return {
                "ok": True,
                "row_count": int(len(df)),
                "column_count": int(len(df.columns)),
                "columns": list(df.columns),
                "canonical_mapping": canonical,
                "preview": preview_clean,
                "dataframe": df,
                "text_excerpt": "\n".join(all_text)[:3000],
            }

        # No tables — return text only
        return {
            "ok": True,
            "row_count": 0,
            "column_count": 0,
            "columns": [],
            "canonical_mapping": {},
            "preview": [],
            "dataframe": pd.DataFrame(),
            "text_excerpt": "\n".join(all_text)[:3000],
        }
    except Exception as e:
        return {"ok": False, "error": f"Failed to parse PDF: {e}"}
