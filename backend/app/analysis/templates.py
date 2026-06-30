TEMPLATES = {
    "summary": """\
import pandas as pd
import numpy as np
import json

_cols = df.columns.tolist()
_num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
_cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
_date_cols = []
for c in _cols:
    try:
        if pd.api.types.is_datetime64_any_dtype(df[c]) or c.lower() in ("date", "datetime", "time", "timestamp"):
            _date_cols.append(c)
    except Exception:
        pass

_desc = {}
for c in _num_cols:
    _d = df[c].describe().to_dict()
    _desc[c] = {k: round(v, 4) if isinstance(v, float) else v for k, v in _d.items()}

_missing = df.isnull().sum().to_dict()
_missing = {k: int(v) for k, v in _missing.items()}
_duplicates = int(df.duplicated().sum())

result = {
    "title": "Dataset Summary",
    "summary": f"Dataset has {len(df)} rows and {len(_cols)} columns.",
    "metrics": {
        "rows": len(df),
        "columns": len(_cols),
        "numeric_columns": len(_num_cols),
        "categorical_columns": len(_cat_cols),
        "date_columns": len(_date_cols),
        "total_missing": sum(_missing.values()),
        "duplicate_rows": _duplicates,
    },
    "tables": {
        "column_names": _cols,
        "numeric_columns": _num_cols,
        "categorical_columns": _cat_cols,
        "date_columns": _date_cols,
        "describe": _desc,
        "missing_values": _missing,
    },
    "chart": None,
    "insights": []
}

if sum(_missing.values()) > 0:
    _top_missing = sorted(_missing.items(), key=lambda x: -x[1])[:3]
    for c, v in _top_missing:
        if v > 0:
            result["insights"].append(f"Column '{c}' has {v} missing values ({round(100*v/len(df), 1)}%).")
if _duplicates > 0:
    result["insights"].append(f"Dataset has {_duplicates} duplicate rows ({round(100*_duplicates/len(df), 1)}%).")
result["insights"].append(f"Dataset has {len(_num_cols)} numeric, {len(_cat_cols)} categorical, and {len(_date_cols)} date columns.")
""",
    "missing_outliers": """\
import pandas as pd
import numpy as np
import json

_num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
_missing = df.isnull().sum().to_dict()
_missing = {k: int(v) for k, v in _missing.items()}
_missing_pct = {k: round(100 * v / len(df), 2) for k, v in _missing.items()}

_outliers = {}
for c in _num_cols:
    _q1 = df[c].quantile(0.25)
    _q3 = df[c].quantile(0.75)
    _iqr = _q3 - _q1
    _lower = _q1 - 1.5 * _iqr
    _upper = _q3 + 1.5 * _iqr
    _out = df[(df[c] < _lower) | (df[c] > _upper)]
    if len(_out) > 0:
        _outliers[c] = {
            "count": len(_out),
            "percentage": round(100 * len(_out) / len(df), 2),
            "lower_bound": round(_lower, 4) if not pd.isna(_lower) else None,
            "upper_bound": round(_upper, 4) if not pd.isna(_upper) else None,
            "min_value": round(float(df[c].min()), 4),
            "max_value": round(float(df[c].max()), 4),
        }

_high_missing = sorted([(k, v) for k, v in _missing.items() if v > 0], key=lambda x: -x[1])
_high_outliers = sorted([(k, v["count"]) for k, v in _outliers.items()], key=lambda x: -x[1])

result = {
    "title": "Missing Values & Outliers",
    "summary": f"Found {sum(_missing.values())} missing values across {len(_high_missing)} columns and outliers in {len(_outliers)} numeric columns.",
    "metrics": {
        "total_missing": sum(_missing.values()),
        "columns_with_missing": len(_high_missing),
        "columns_with_outliers": len(_outliers),
    },
    "tables": {
        "missing_values": {k: {"count": _missing[k], "percentage": _missing_pct[k]} for k in _missing if _missing[k] > 0},
        "outliers": _outliers,
    },
    "chart": None,
    "insights": []
}

for c, v in _high_missing[:5]:
    result["insights"].append(f"'{c}': {v} missing ({_missing_pct[c]}%).")
for c, v in _high_outliers[:5]:
    result["insights"].append(f"'{c}': {v} outliers ({_outliers[c]['percentage']}% of data).")
if not _high_missing:
    result["insights"].append("No missing values found.")
if not _high_outliers:
    result["insights"].append("No significant outliers detected.")
""",
    "best_worst": """\
import pandas as pd
import numpy as np
import json

_num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
_date_cols = []
for c in df.columns:
    try:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            _date_cols.append(c)
    except Exception:
        try:
            _ = pd.to_datetime(df[c], errors="raise")
            _date_cols.append(c)
        except Exception:
            pass

_date_cols = list(dict.fromkeys(_date_cols))

if not _num_cols:
    result = {
        "title": "Best/Worst Values",
        "summary": "No numeric columns found to analyze.",
        "metrics": {},
        "tables": {},
        "chart": None,
        "insights": ["No numeric columns available for best/worst analysis."]
    }
else:
    _best_worst = {}
    for c in _num_cols:
        _max_val = float(df[c].max())
        _min_val = float(df[c].min())
        _max_idx = df[c].idxmax()
        _min_idx = df[c].idxmin()
        _entry = {
            "max_value": round(_max_val, 4),
            "min_value": round(_min_val, 4),
            "mean": round(float(df[c].mean()), 4),
            "median": round(float(df[c].median()), 4),
        }
        if _date_cols:
            _date_col = _date_cols[0]
            try:
                _entry["max_at"] = str(df.loc[_max_idx, _date_col])
                _entry["min_at"] = str(df.loc[_min_idx, _date_col])
            except Exception:
                pass
        _best_worst[c] = _entry

    result = {
        "title": "Best/Worst Values by Column",
        "summary": f"Analyzed {len(_num_cols)} numeric columns." + (f" Using '{_date_cols[0]}' as date column." if _date_cols else ""),
        "metrics": {
            "numeric_columns_analyzed": len(_num_cols),
            "date_column_found": _date_cols[0] if _date_cols else None,
        },
        "tables": {"columns": _best_worst},
        "chart": None,
        "insights": []
    }
    for c, v in _best_worst.items():
        result["insights"].append(f"'{c}': max={v['max_value']}, min={v['min_value']}, mean={v['mean']}.")
""",
    "basic_chart": """\
import pandas as pd
import numpy as np
import json

_num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
_cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
_date_cols = []
for c in df.columns:
    try:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            _date_cols.append(c)
    except Exception:
        pass

_date_cols = list(dict.fromkeys(_date_cols))

_chart = None
_insights = []

if _date_cols and _num_cols:
    _dc = _date_cols[0]
    _nc = _num_cols[0]
    _tmp = df.copy()
    _tmp[_dc] = pd.to_datetime(_tmp[_dc], errors="coerce")
    _tmp = _tmp.dropna(subset=[_dc, _nc])
    _grouped = _tmp.groupby(_tmp[_dc].dt.to_period("M").astype(str))[_nc].mean().reset_index()
    _grouped.columns = ["label", "value"]
    _chart = {
        "type": "line",
        "title": f"{_nc} by Month ({_dc})",
        "x": _grouped["label"].tolist(),
        "y": [round(v, 4) for v in _grouped["value"].tolist()],
        "x_label": "Month",
        "y_label": _nc,
    }
    _insights.append(f"Line chart: {_nc} trend over time ({len(_grouped)} periods).")
elif _cat_cols and _num_cols:
    _cc = _cat_cols[0]
    _nc = _num_cols[0]
    _grouped = df.groupby(_cc)[_nc].mean().sort_values(ascending=False).reset_index()
    _grouped.columns = ["label", "value"]
    _chart = {
        "type": "bar",
        "title": f"Mean {_nc} by {_cc}",
        "x": _grouped["label"].astype(str).tolist(),
        "y": [round(v, 4) for v in _grouped["value"].tolist()],
        "x_label": _cc,
        "y_label": f"Mean {_nc}",
    }
    _insights.append(f"Bar chart: mean {_nc} grouped by {_cc} ({len(_grouped)} categories).")
elif _num_cols:
    _nc = _num_cols[0]
    _bins = min(20, len(df) // 10) if len(df) >= 20 else 5
    _counts, _edges = np.histogram(df[_nc].dropna(), bins=_bins)
    _labels = [f"{round(_edges[i], 2)}-{round(_edges[i+1], 2)}" for i in range(len(_edges)-1)]
    _chart = {
        "type": "bar",
        "title": f"Distribution of {_nc}",
        "x": _labels,
        "y": [int(c) for c in _counts],
        "x_label": _nc,
        "y_label": "Count",
    }
    _insights.append(f"Histogram: distribution of {_nc} ({_bins} bins).")
else:
    _insights.append("No suitable columns found for chart generation.")

result = {
    "title": "Automatic Chart",
    "summary": "Generated chart based on data columns." if _chart else "Could not generate chart.",
    "metrics": {"chart_type": _chart["type"] if _chart else None},
    "tables": {},
    "chart": _chart,
    "insights": _insights
}
""",
}


def get_template(analysis_type: str) -> str:
    return TEMPLATES.get(analysis_type, "")
