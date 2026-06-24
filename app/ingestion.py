import sys
import warnings
from pathlib import Path
from typing import Union

import pandas as pd
from pydantic import ValidationError

from app.models import Incident


def load_incidents(source: Union[str, Path]) -> list[Incident]:
    """
    Read CSV or JSONL from `source` (file path or '-' for stdin).
    Returns validated list[Incident]; skips and warns on bad rows.
    """
    source = str(source)

    if source == "-":
        df = pd.read_csv(sys.stdin)
    else:
        path = Path(source)
        suffix = path.suffix.lower()
        if suffix == ".csv":
            df = pd.read_csv(path)
        elif suffix in (".jsonl", ".json"):
            df = pd.read_json(path, lines=True)
        else:
            raise ValueError(f"Unsupported file format: {suffix!r}. Use .csv or .jsonl")

    # Strip whitespace from column names
    df.columns = [c.strip() for c in df.columns]

    incidents: list[Incident] = []
    for row in df.to_dict("records"):
        try:
            incidents.append(Incident(**row))
        except (ValidationError, TypeError) as exc:
            warnings.warn(f"Skipping invalid row {row.get('id', '?')}: {exc}")

    return incidents
