#!/usr/bin/env python3

import os
from pathlib import Path

import geopandas as gpd
import pandas as pd
import psycopg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
BINS_SQL = "SELECT id AS bin_id, coord_x AS longitude, coord_y AS latitude FROM bin"  # LV95 (EPSG:2056)
POLYGONS_PATH = Path("data/neighbourhoods.geojson")
OUTPUT_PATH = Path("data/static/bin_neighbourhood_mapping.csv")
POLYGON_ID_COL = "id"
POLYGON_NAME_COL = "name"
BINS_CRS = "EPSG:2056"


def _load_bins() -> pd.DataFrame:
    with psycopg.connect(DATABASE_URL) as conn:
        bins_df = pd.read_sql_query(BINS_SQL, conn)

    bins_df["longitude"] = pd.to_numeric(bins_df["longitude"], errors="coerce")
    bins_df["latitude"] = pd.to_numeric(bins_df["latitude"], errors="coerce")

    print(f"Loaded {len(bins_df)} bins")
    return bins_df


def _load_polygons() -> gpd.GeoDataFrame:
    polygons = gpd.read_file(POLYGONS_PATH)

    missing_cols = [c for c in [POLYGON_ID_COL, POLYGON_NAME_COL] if c not in polygons.columns]
    if missing_cols:
        raise ValueError(f"Polygon layer missing columns: {missing_cols}")
    return polygons


def _build_bins_geodataframe(bins_df: pd.DataFrame) -> gpd.GeoDataFrame:
    bins_gdf = gpd.GeoDataFrame(
        bins_df,
        geometry=gpd.points_from_xy(bins_df["longitude"], bins_df["latitude"]),
        crs=BINS_CRS,
    )
    bins_gdf["_row_id"] = bins_gdf.index
    return bins_gdf


def _assign_within(bins_gdf: gpd.GeoDataFrame, polygons: gpd.GeoDataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    bins_in_poly_crs = bins_gdf.to_crs(polygons.crs)

    within = gpd.sjoin(
        bins_in_poly_crs,
        polygons[[POLYGON_ID_COL, POLYGON_NAME_COL, "geometry"]],
        how="left",
        predicate="within",
    )

    matched = within[within[POLYGON_ID_COL].notna()].copy()
    unmatched = within[within[POLYGON_ID_COL].isna()].copy()

    matched["assignment_method"] = "within"
    matched["distance_to_polygon_m"] = 0.0

    return matched, unmatched


def _assign_nearest(
    bins_gdf: gpd.GeoDataFrame,
    polygons: gpd.GeoDataFrame,
    unmatched: pd.DataFrame,
    matched_columns: pd.Index,
) -> pd.DataFrame:
    if unmatched.empty:
        return pd.DataFrame(columns=matched_columns)

    bins_metric = bins_gdf.loc[unmatched["_row_id"]].to_crs(BINS_CRS)
    polygons_metric = polygons.to_crs(BINS_CRS)

    nearest = gpd.sjoin_nearest(
        bins_metric,
        polygons_metric[[POLYGON_ID_COL, POLYGON_NAME_COL, "geometry"]],
        how="left",
        distance_col="distance_to_polygon_m",
    )

    nearest["assignment_method"] = "nearest"
    return nearest


def _build_output(combined: pd.DataFrame) -> pd.DataFrame:
    out = combined[
        ["bin_id", POLYGON_ID_COL, POLYGON_NAME_COL, "assignment_method", "distance_to_polygon_m"]
    ].copy()
    out["distance_to_polygon_m"] = out["distance_to_polygon_m"].astype(float).round(3)
    out = out.sort_values("bin_id")
    return out


def _save_output(out: pd.DataFrame) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved: {OUTPUT_PATH}")


def _print_summary(out: pd.DataFrame, total_bins: int) -> None:
    nearest_rows = out[out["assignment_method"] == "nearest"]
    print(f"total bins: {total_bins}")
    print(f"assigned by within: {(out['assignment_method'] == 'within').sum()}")
    print(f"assigned by nearest: {len(nearest_rows)}")
    if len(nearest_rows) > 0:
        print(f"max nearest distance (m): {nearest_rows['distance_to_polygon_m'].max():.3f}")


def main() -> None:
    bins_df = _load_bins()
    polygons = _load_polygons()

    bins_gdf = _build_bins_geodataframe(bins_df)

    matched, unmatched = _assign_within(bins_gdf, polygons)
    nearest_result = _assign_nearest(bins_gdf, polygons, unmatched, matched.columns)

    combined = pd.concat([matched, nearest_result], ignore_index=True)

    out = _build_output(combined)
    _save_output(out)
    _print_summary(out, total_bins=len(bins_df))


if __name__ == "__main__":
    main()
