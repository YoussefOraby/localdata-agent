# Sample Datasets

This directory contains synthetic demo datasets for testing LocalData Agent.

## sample_sales.csv

A 25-row synthetic sales dataset with:
- **date** — daily from 2024-01-01 to 2024-01-25
- **product** — Widget A, Widget B, Widget C
- **category** — Gadgets, Doohickeys, Thingamajigs
- **price** — numeric values from 10.00 to 50.00
- **units_sold** — numeric values from 10 to 500
- **revenue** — numeric, contains one missing value
- **rating** — numeric from 1.0 to 5.0

Designed to exercise all analysis types:
- Summary, Missing Values & Outliers, Best/Worst Values, Basic Chart
- Web search and multi-agent queries
- Edge cases: missing values, outliers, mixed data types

Generated with `numpy` and `pandas`, not real data.
