def transform(inputs, params, ctx):
    """The rows whose key appears more than once, grouped, with how many copies of the key there are."""
    rows = inputs["rows"]
    keys = [name.strip() for name in str(params.get("key_columns") or "").split(",") if name.strip()]
    keys = keys or list(rows.columns)
    unknown = [name for name in keys if name not in rows.columns]
    if unknown:
        raise ValueError(f"The table has no column {', '.join(unknown)}: the key columns are {', '.join(keys)}.")

    repeated = rows[rows.duplicated(subset=keys, keep=False)].copy()
    groups = repeated.groupby(keys, dropna=False, sort=True)
    repeated["duplicate_group"] = groups.ngroup() + 1
    repeated["copies"] = groups[keys[0]].transform("size")
    ctx.logger.info("%d rows share their key with another, in %d groups", len(repeated),
                    repeated["duplicate_group"].nunique())
    return {"duplicates": repeated.sort_values("duplicate_group").reset_index(drop=True)}
