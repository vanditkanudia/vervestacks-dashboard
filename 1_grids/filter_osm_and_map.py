#!/usr/bin/env python3
"""
Filter OSM-Eur-prebuilt buses and lines, then visualize them on an interactive map.

Usage examples:
  - Filter by ISO3 country code (auto-creates output/{ISO3} folder):
      python 1_grids/filter_osm_and_map.py --iso3 DEU

  - Filter by countries (ISO2 or ISO3 codes, auto-converted):
      python 1_grids/filter_osm_and_map.py --countries DE,AT
      python 1_grids/filter_osm_and_map.py --countries DEU,ITA

  - Filter by voltage and bounding box (minx miny maxx maxy in lon/lat):
      python 1_grids/filter_osm_and_map.py --voltage-min 220 --bbox 5 45 15 55

  - Save filtered CSVs and custom HTML output:
      python 1_grids/filter_osm_and_map.py --iso3 DEU --save-filtered
"""

import argparse
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, box
from shapely import wkt as shapely_wkt
import folium


REPO_ROOT = Path(__file__).resolve().parents[1]
GRIDS_DIR = Path(__file__).resolve().parent
OSM_DIR = REPO_ROOT / "data" / "OSM-Eur-prebuilt"
DEFAULT_BUSES_CSV = OSM_DIR / "buses.csv"
DEFAULT_LINES_CSV = OSM_DIR / "lines.csv"
DEFAULT_OUTPUT_DIR = GRIDS_DIR / "output"


def get_iso2_from_iso3(iso3_code):
    """Convert ISO3 code to ISO2 code"""
    try:
        import pycountry
        country = pycountry.countries.get(alpha_3=iso3_code)
        if country:
            return country.alpha_2
    except:
        pass
    
    # Fallback dictionary for special cases
    iso3_to_iso2 = {
        'CHE': 'CH',
        'DEU': 'DE', 
        'FRA': 'FR',
        'GBR': 'GB',
        'ITA': 'IT',
        'ESP': 'ES',
        'POL': 'PL',
        'NLD': 'NL',
        'BEL': 'BE',
        'AUT': 'AT',
        'CZE': 'CZ',
        'DNK': 'DK',
        'NOR': 'NO',
        'SWE': 'SE',
        'FIN': 'FI',
        'XKX': 'XK'   # Kosovo
    }
    
    return iso3_to_iso2.get(iso3_code, iso3_code[:2])


def parse_countries_arg(arg: Optional[str]) -> Optional[Set[str]]:
    if not arg:
        return None
    
    countries = set()
    for c in arg.split(","):
        c = c.strip().upper()
        if not c:
            continue
            
        # Check if it's ISO3 and convert to ISO2
        if len(c) == 3:
            iso2 = get_iso2_from_iso3(c)
            countries.add(iso2)
        else:
            # Assume it's already ISO2
            countries.add(c)
    
    return countries or None


def safe_to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def extract_country_from_bus_id(bus_id: str) -> Optional[str]:
    if not isinstance(bus_id, str) or not bus_id:
        return None
    prefix_chars: List[str] = []
    for ch in bus_id:
        if ch.isalpha():
            prefix_chars.append(ch)
        else:
            break
    if not prefix_chars:
        return None
    return "".join(prefix_chars).upper()


def build_buses_gdf(buses_csv: Path) -> gpd.GeoDataFrame:
    buses_df = pd.read_csv(buses_csv, low_memory=False)

    has_geometry_wkt = "geometry" in buses_df.columns and buses_df["geometry"].astype(str).str.startswith("POINT").any()
    if has_geometry_wkt:
        geometry = buses_df["geometry"].astype(str).apply(shapely_wkt.loads)
        buses_gdf = gpd.GeoDataFrame(buses_df, geometry=geometry, crs="EPSG:4326")
    else:
        if not {"x", "y"}.issubset(buses_df.columns):
            raise ValueError("buses.csv must contain either 'geometry' WKT or 'x' and 'y' columns")
        geometry = gpd.points_from_xy(buses_df["x"], buses_df["y"], crs="EPSG:4326")
        buses_gdf = gpd.GeoDataFrame(buses_df, geometry=geometry, crs="EPSG:4326")

    if "country" not in buses_gdf.columns:
        buses_gdf["country"] = buses_gdf.get("bus_id", "").astype(str).apply(extract_country_from_bus_id)

    if "voltage" in buses_gdf.columns:
        buses_gdf["voltage_num"] = safe_to_numeric(buses_gdf["voltage"])
    else:
        buses_gdf["voltage_num"] = pd.NA

    return buses_gdf


def detect_line_bus_columns(lines_df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    candidates = [
        ("bus0", "bus1"),
        ("bus_0", "bus_1"),
        ("bus0_id", "bus1_id"),
        ("from_bus", "to_bus"),
        ("bus_from", "bus_to"),
    ]
    for c0, c1 in candidates:
        if c0 in lines_df.columns and c1 in lines_df.columns:
            return c0, c1
    return None, None


def detect_line_coord_columns(lines_df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    candidates = [
        ("x0", "y0", "x1", "y1"),
        ("lon0", "lat0", "lon1", "lat1"),
        ("longitude0", "latitude0", "longitude1", "latitude1"),
    ]
    for c0x, c0y, c1x, c1y in candidates:
        if all(col in lines_df.columns for col in [c0x, c0y, c1x, c1y]):
            return c0x, c0y, c1x, c1y
    return None, None, None, None


def build_lines_gdf(lines_csv: Path, buses_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    lines_df = pd.read_csv(lines_csv, low_memory=False)

    # Case 1: WKT geometry present
    geom_col = None
    for candidate in ["geometry", "wkt", "geometry_wkt", "geom_wkt"]:
        if candidate in lines_df.columns:
            geom_col = candidate
            break
    if geom_col is not None:
        geometry = lines_df[geom_col].astype(str).apply(shapely_wkt.loads)
        lines_gdf = gpd.GeoDataFrame(lines_df, geometry=geometry, crs="EPSG:4326")
    else:
        # Case 2: Coordinate columns
        x0_col, y0_col, x1_col, y1_col = detect_line_coord_columns(lines_df)
        if all([x0_col, y0_col, x1_col, y1_col]):
            def make_ls_from_coords(row):
                try:
                    x0, y0, x1, y1 = float(row[x0_col]), float(row[y0_col]), float(row[x1_col]), float(row[y1_col])
                    return LineString([(x0, y0), (x1, y1)])
                except Exception:
                    return None
            geometry = lines_df.apply(make_ls_from_coords, axis=1)
            lines_gdf = gpd.GeoDataFrame(lines_df, geometry=geometry, crs="EPSG:4326")
            lines_gdf = lines_gdf[lines_gdf.geometry.notnull()]
        else:
            # Case 3: Build geometry by joining to buses
            bus0_col, bus1_col = detect_line_bus_columns(lines_df)
            if not (bus0_col and bus1_col):
                raise ValueError("lines.csv must provide either geometry WKT, endpoint coordinate columns, or bus endpoint IDs (e.g., 'bus0' and 'bus1')")

            # Prepare bus coordinate lookup
            if "bus_id" not in buses_gdf.columns:
                raise ValueError("buses.csv must include 'bus_id' to construct line geometries from endpoints")

            bus_points = buses_gdf[["bus_id", "geometry"]].dropna().copy()
            # Ensure Point geometries
            bus_points = bus_points[bus_points.geometry.type == "Point"]
            id_to_xy = {str(bid): (pt.x, pt.y) for bid, pt in zip(bus_points["bus_id"].astype(str), bus_points.geometry)}

            def make_ls_from_bus_ids(row):
                b0 = str(row[bus0_col]) if pd.notna(row[bus0_col]) else None
                b1 = str(row[bus1_col]) if pd.notna(row[bus1_col]) else None
                if not b0 or not b1:
                    return None
                p0 = id_to_xy.get(b0)
                p1 = id_to_xy.get(b1)
                if not p0 or not p1:
                    return None
                return LineString([p0, p1])

            geometry = lines_df.apply(make_ls_from_bus_ids, axis=1)
            lines_gdf = gpd.GeoDataFrame(lines_df, geometry=geometry, crs="EPSG:4326")
            lines_gdf = lines_gdf[lines_gdf.geometry.notnull()]

    # Enrich country and voltage
    if "country" not in lines_gdf.columns or lines_gdf["country"].isna().all():
        bus0_col, bus1_col = detect_line_bus_columns(lines_df)
        if bus0_col and bus1_col and bus0_col in lines_gdf.columns:
            inferred_countries = lines_gdf[bus0_col].astype(str).apply(extract_country_from_bus_id)
            lines_gdf["country"] = inferred_countries
        else:
            lines_gdf["country"] = pd.NA

    if "voltage" in lines_gdf.columns:
        lines_gdf["voltage_num"] = safe_to_numeric(lines_gdf["voltage"])
    else:
        lines_gdf["voltage_num"] = pd.NA

    return lines_gdf


def filter_buses(
    buses_gdf: gpd.GeoDataFrame,
    countries: Optional[Set[str]] = None,
    voltage_min: Optional[float] = None,
    voltage_max: Optional[float] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,
) -> gpd.GeoDataFrame:
    filtered = buses_gdf.copy()

    # Filter by countries FIRST - this is the primary filter
    if countries:
        if "country" in filtered.columns:
            # Direct country column filtering
            filtered = filtered[filtered["country"].isin(countries)]
        else:
            # Fallback: extract from bus_id prefix
            if "bus_id" in filtered.columns:
                country_mask = filtered["bus_id"].astype(str).apply(
                    lambda bid: extract_country_from_bus_id(bid) in countries if extract_country_from_bus_id(bid) else False
                )
                filtered = filtered[country_mask]

    # Apply other filters after country filtering
    if voltage_min is not None:
        if "voltage_num" in filtered.columns:
            filtered = filtered[(filtered["voltage_num"].isna()) | (filtered["voltage_num"] >= voltage_min)]

    if voltage_max is not None:
        if "voltage_num" in filtered.columns:
            filtered = filtered[(filtered["voltage_num"].isna()) | (filtered["voltage_num"] <= voltage_max)]

    if bbox is not None:
        minx, miny, maxx, maxy = bbox
        bbox_geom = box(minx, miny, maxx, maxy)
        filtered = filtered[filtered.intersects(bbox_geom)]

    return filtered


def filter_lines(
    lines_gdf: gpd.GeoDataFrame,
    buses_filtered: gpd.GeoDataFrame,
    countries: Optional[Set[str]] = None,
    voltage_min: Optional[float] = None,
    voltage_max: Optional[float] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,
) -> gpd.GeoDataFrame:
    """
    Filter lines based on already-filtered buses (both endpoints must be in filtered bus set).
    This ensures proper country filtering: buses_filtered should already be country-filtered.
    """
    filtered = lines_gdf.copy()

    # PRIMARY FILTER: Both line endpoints must be in the filtered bus set
    # This automatically handles country filtering if buses_filtered was country-filtered
    if not buses_filtered.empty and "bus_id" in buses_filtered.columns:
        allowed_bus_ids: Set[str] = set(buses_filtered["bus_id"].astype(str))
        
        bus0_col, bus1_col = detect_line_bus_columns(filtered)
        if bus0_col and bus1_col:
            # Both endpoints must be in the allowed bus set
            mask = (
                filtered[bus0_col].astype(str).isin(allowed_bus_ids) & 
                filtered[bus1_col].astype(str).isin(allowed_bus_ids)
            )
            filtered = filtered[mask]
        else:
            # If we can't find bus columns, fall back to country-based filtering
            if countries and "country" in filtered.columns:
                filtered = filtered[filtered["country"].isin(countries)]

    # Apply voltage filters
    if voltage_min is not None and "voltage_num" in filtered.columns:
        filtered = filtered[(filtered["voltage_num"].isna()) | (filtered["voltage_num"] >= voltage_min)]

    if voltage_max is not None and "voltage_num" in filtered.columns:
        filtered = filtered[(filtered["voltage_num"].isna()) | (filtered["voltage_num"] <= voltage_max)]

    # Apply bounding box filter
    if bbox is not None:
        minx, miny, maxx, maxy = bbox
        bbox_geom = box(minx, miny, maxx, maxy)
        filtered = filtered[filtered.intersects(bbox_geom)]

    return filtered


def determine_map_center(buses_gdf: gpd.GeoDataFrame) -> Tuple[float, float]:
    if buses_gdf.empty:
        return 54.0, 15.0
    try:
        centroid = buses_gdf.geometry.union_all().centroid
        return float(centroid.y), float(centroid.x)
    except Exception:
        lat = buses_gdf["y"].astype(float).mean() if "y" in buses_gdf.columns else 54.0
        lon = buses_gdf["x"].astype(float).mean() if "x" in buses_gdf.columns else 15.0
        return float(lat), float(lon)


def voltage_to_color(voltage_kv: Optional[float]) -> str:
    if voltage_kv is None or pd.isna(voltage_kv):
        return "#666666"
    v = float(voltage_kv)
    if v >= 380:
        return "#d62728"
    if v >= 220:
        return "#ff7f0e"
    if v >= 132:
        return "#2ca02c"
    if v >= 66:
        return "#1f77b4"
    return "#9467bd"


def add_buses_to_map(m: folium.Map, buses_gdf: gpd.GeoDataFrame) -> None:
    for _, row in buses_gdf.iterrows():
        geom: Point = row.geometry
        if geom is None or geom.is_empty:
            continue
        popup_parts: List[str] = []
        if "bus_id" in row:
            popup_parts.append(f"bus_id: {row['bus_id']}")
        if "country" in row and pd.notna(row["country"]):
            popup_parts.append(f"country: {row['country']}")
        if "voltage_num" in row and pd.notna(row["voltage_num"]):
            popup_parts.append(f"voltage: {int(row['voltage_num'])} kV")
        popup_text = " | ".join(popup_parts) if popup_parts else "bus"

        color = voltage_to_color(row.get("voltage_num", pd.NA))
        folium.CircleMarker(
            location=[geom.y, geom.x],
            radius=4,
            color=color,
            fill=True,
            fill_opacity=0.9,
            weight=1,
            popup=popup_text,
        ).add_to(m)


def add_lines_to_map(m: folium.Map, lines_gdf: gpd.GeoDataFrame) -> None:
    for _, row in lines_gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        if not isinstance(geom, (LineString,)):
            try:
                line_strings: List[LineString] = list(geom.geoms)  # type: ignore[attr-defined]
            except Exception:
                line_strings = []
        else:
            line_strings = [geom]

        color = voltage_to_color(row.get("voltage_num", pd.NA))
        popup_parts: List[str] = []
        for k in ["name", "line_id", "country"]:
            if k in row and pd.notna(row[k]):
                popup_parts.append(f"{k}: {row[k]}")
        if "voltage_num" in row and pd.notna(row["voltage_num"]):
            popup_parts.append(f"voltage: {int(row['voltage_num'])} kV")
        popup_text = " | ".join(popup_parts) if popup_parts else "line"

        for ls in line_strings:
            coords = [(lat, lon) for lon, lat in ls.coords]
            folium.PolyLine(
                locations=coords,
                color=color,
                weight=2,
                opacity=0.8,
                popup=popup_text,
            ).add_to(m)


def render_map(
    buses_gdf: gpd.GeoDataFrame,
    lines_gdf: gpd.GeoDataFrame,
    output_html: Path,
) -> None:
    lat, lon = determine_map_center(buses_gdf)
    m = folium.Map(location=[lat, lon], zoom_start=6, tiles="cartodbpositron")

    add_lines_to_map(m, lines_gdf)
    add_buses_to_map(m, buses_gdf)

    folium.LayerControl(collapsed=True).add_to(m)
    output_html.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_html))


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter OSM-Eur-prebuilt buses and lines, then visualize on a map.")
    parser.add_argument("--buses-csv", type=Path, default=DEFAULT_BUSES_CSV, help="Path to buses.csv")
    parser.add_argument("--lines-csv", type=Path, default=DEFAULT_LINES_CSV, help="Path to lines.csv")
    parser.add_argument("--countries", type=str, default=None, help="Comma-separated ISO2 or ISO3 country codes (e.g., DE,AT or DEU,ITA)")
    parser.add_argument("--iso3", type=str, default=None, help="ISO3 country code (e.g., DEU,ITA) - will be converted to ISO2 and used for output folder")
    parser.add_argument("--voltage-min", type=float, default=None, help="Minimum voltage in kV")
    parser.add_argument("--voltage-max", type=float, default=None, help="Maximum voltage in kV")
    parser.add_argument("--bbox", nargs=4, type=float, default=None, metavar=("MINX", "MINY", "MAXX", "MAXY"), help="Bounding box in lon/lat")
    parser.add_argument("--output-html", type=Path, default=None, help="Output HTML map path (auto-generated if not specified)")
    parser.add_argument("--save-filtered", action="store_true", help="Save filtered CSVs next to the HTML output")

    args = parser.parse_args()

    if not args.buses_csv.exists():
        raise FileNotFoundError(f"buses.csv not found: {args.buses_csv}")
    if not args.lines_csv.exists():
        raise FileNotFoundError(f"lines.csv not found: {args.lines_csv}")

    # Handle ISO3 input and convert to ISO2 for filtering
    selected_countries = None
    iso3_code = None
    iso2_code = None
    
    if args.iso3:
        iso3_code = args.iso3.upper()
        iso2_code = get_iso2_from_iso3(iso3_code)
        selected_countries = {iso2_code}
        print(f"ISO3 '{iso3_code}' converted to ISO2 '{iso2_code}'")
    elif args.countries:
        selected_countries = parse_countries_arg(args.countries)
        # Try to infer ISO3 from first country for output naming
        if selected_countries:
            first_country = list(selected_countries)[0]
            # Simple reverse lookup for common cases
            iso2_to_iso3 = {v: k for k, v in {
                'CHE': 'CH', 'DEU': 'DE', 'FRA': 'FR', 'GBR': 'GB', 'ITA': 'IT',
                'ESP': 'ES', 'POL': 'PL', 'NLD': 'NL', 'BEL': 'BE', 'AUT': 'AT',
                'CZE': 'CZ', 'DNK': 'DK', 'NOR': 'NO', 'SWE': 'SE', 'FIN': 'FI'
            }.items()}
            iso3_code = iso2_to_iso3.get(first_country, first_country)
    
    bbox_tuple: Optional[Tuple[float, float, float, float]] = tuple(args.bbox) if args.bbox else None

    # Auto-generate output path if not specified
    if args.output_html is None:
        if iso3_code:
            output_dir = DEFAULT_OUTPUT_DIR / iso3_code
            output_html = output_dir / f"{iso3_code}_osm_network_map.html"
        else:
            output_html = DEFAULT_OUTPUT_DIR / "osm_subset_map.html"
    else:
        output_html = args.output_html

    buses_gdf = build_buses_gdf(args.buses_csv)
    buses_filtered = filter_buses(
        buses_gdf,
        countries=selected_countries,
        voltage_min=args.voltage_min,
        voltage_max=args.voltage_max,
        bbox=bbox_tuple,
    )

    lines_gdf = build_lines_gdf(args.lines_csv, buses_gdf)
    lines_filtered = filter_lines(
        lines_gdf,
        buses_filtered,
        countries=selected_countries,
        voltage_min=args.voltage_min,
        voltage_max=args.voltage_max,
        bbox=bbox_tuple,
    )

    if args.save_filtered:
        out_dir = output_html.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        prefix = f"{iso3_code}_" if iso3_code else ""
        buses_filtered.to_csv(out_dir / f"{prefix}buses_filtered.csv", index=False)
        lines_filtered.to_csv(out_dir / f"{prefix}lines_filtered.csv", index=False)

    render_map(buses_filtered, lines_filtered, output_html)
    print(f"Saved map to: {output_html}")
    print(f"Buses shown: {len(buses_filtered)} | Lines shown: {len(lines_filtered)}")


if __name__ == "__main__":
    main()

