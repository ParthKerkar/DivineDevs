"""Build a transparent Census-based heat mortality-risk screening factor."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from weather_api import calculate_hourly_wbgt, fetch_weather_snapshot

AGE_WEIGHTS = {"older_60_plus_share": 0.45, "child_0_4_share": 0.15,
               "worker_population_share": 0.15, "outdoor_worker_share": 0.25}
TOWN_WEIGHTS = {"state_older_60_plus_share": 0.30, "child_0_6_share": 0.20,
                "worker_population_share": 0.20, "outdoor_worker_share": 0.30}
WBGT_SCREENING_ANCHOR_C = 26.0
WBGT_TOP_ALERT_C = 32.2


def clean_state_name(value: object) -> str:
    """Normalise only known Census presentation differences for joins."""
    name = str(value).strip().upper()
    name = re.sub(r"^STATE\s*-\s*", "", name)
    name = re.sub(r"\s*\(\d+\)\s*$", "", name)
    aliases = {"NCT OF DELHI": "DELHI", "ORISSA": "ODISHA",
               "UTTARANCHAL": "UTTARAKHAND", "ANDAMAN & NICOBAR ISLANDS": "ANDAMAN AND NICOBAR ISLANDS",
               "DADRA & NAGAR HAVELI": "DADRA AND NAGAR HAVELI"}
    return aliases.get(name, name)


def clean_town_name(value: object) -> str:
    """Create a conservative match key for a user city and Census town name."""
    name = re.sub(r"\([^)]*\)", "", str(value).upper())
    return re.sub(r"[^A-Z0-9]", "", name)


def capped_percentile_scale(values: pd.Series) -> pd.Series:
    """Scale a state-comparison indicator using its 5th and 95th percentiles."""
    lower, upper = values.quantile([0.05, 0.95])
    if pd.isna(lower) or pd.isna(upper) or upper <= lower:
        return pd.Series(0.5, index=values.index)
    return ((values - lower) / (upper - lower)).clip(0, 1)


def read_pca(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="Data", dtype={"State": str, "District": str})
    states = raw[(raw["Level"] == "STATE") & (raw["TRU"] == "Total")].copy()
    states["state_key"] = states["Name"].map(clean_state_name)
    numeric = ["TOT_P", "TOT_WORK_P", "MAIN_CL_P", "MAIN_AL_P", "MARG_CL_P", "MARG_AL_P"]
    states[numeric] = states[numeric].apply(pd.to_numeric, errors="coerce")
    states["outdoor_workers"] = states[["MAIN_CL_P", "MAIN_AL_P", "MARG_CL_P", "MARG_AL_P"]].sum(axis=1)
    return states[["State", "state_key", "Name", "TOT_P", "TOT_WORK_P", "outdoor_workers"]]


def read_towns(path: Path) -> pd.DataFrame:
    """Read Census 2011 urban town records and their local worker indicators."""
    raw = pd.read_excel(path, sheet_name="Data", dtype={"State": str, "District": str, "Town/Village": str})
    towns = raw[(raw["Level"] == "TOWN") & (raw["TRU"] == "Urban")].copy()
    numeric = ["TOT_P", "P_06", "TOT_WORK_P", "MAIN_CL_P", "MAIN_AL_P", "MARG_CL_P", "MARG_AL_P"]
    towns[numeric] = towns[numeric].apply(pd.to_numeric, errors="coerce")
    towns["outdoor_workers"] = towns[["MAIN_CL_P", "MAIN_AL_P", "MARG_CL_P", "MARG_AL_P"]].sum(axis=1)
    towns = towns.rename(columns={"State": "state_code", "District": "district_code", "Town/Village": "town_code",
                                  "Name": "town", "TOT_P": "population_2011", "P_06": "children_0_6",
                                  "TOT_WORK_P": "workers_total"})
    towns["state_code"] = towns["state_code"].astype(str).str.zfill(2)
    towns["town_key"] = towns["town"].map(clean_town_name)
    return towns[["state_code", "district_code", "town_code", "town", "town_key", "population_2011", "children_0_6", "workers_total", "outdoor_workers"]]


def read_age(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="Sheet1", header=None, skiprows=7)
    raw = raw.iloc[:, :14]
    raw.columns = ["table", "state_code", "district_code", "state_name", "age_group", "total", "male", "female",
                   "rural_total", "rural_male", "rural_female", "urban_total", "urban_male", "urban_female"]
    rows = raw[(raw["district_code"] == 0) & raw["age_group"].isin(["All ages", "0-4", "60-64", "65-69", "70-74", "75-79", "80+"])].copy()
    rows["total"] = pd.to_numeric(rows["total"], errors="coerce")
    pivot = rows.pivot_table(index=["state_code", "state_name"], columns="age_group", values="total", aggfunc="first").reset_index()
    required = ["All ages", "0-4", "60-64", "65-69", "70-74", "75-79", "80+"]
    missing = set(required).difference(pivot.columns)
    if missing:
        raise ValueError(f"Age table is missing required age groups: {sorted(missing)}")
    pivot["state_key"] = pivot["state_name"].map(clean_state_name)
    pivot["older_60_plus"] = pivot[["60-64", "65-69", "70-74", "75-79", "80+"]].sum(axis=1)
    return pivot[["state_key", "All ages", "0-4", "older_60_plus"]]


def read_occupation_total(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="Sheet1", header=None, skiprows=6)
    raw = raw.iloc[:, :18]
    raw.columns = ["table", "state_name", "state_code", "area", "division", "subgroup", "family", "nco", "nco_name",
                   "total", "male", "female", "rural_total", "rural_male", "rural_female", "urban_total", "urban_male", "urban_female"]
    # One TOTAL row is present for each state.  ``area`` is a state name in
    # this table (despite its multi-row header), rather than the literal word
    # "STATE".
    rows = raw[(raw["nco_name"] == "TOTAL") & (raw["area"] != "INDIA")].copy()
    rows["total"] = pd.to_numeric(rows["total"], errors="coerce")
    rows["state_key"] = rows["area"].map(clean_state_name)
    return rows[["state_key", "total"]].rename(columns={"total": "non_ag_main_workers_b25a"})


def read_death_history(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    year_columns = [column for column in raw.columns if str(column).isdigit()]
    raw[year_columns] = raw[year_columns].apply(pd.to_numeric, errors="coerce")
    raw["state_key"] = raw["State/UT"].map(clean_state_name)
    raw["reported_heat_deaths_2018_2022"] = raw[year_columns].sum(axis=1, min_count=1)
    raw["reported_heat_deaths_annual_mean"] = raw[year_columns].mean(axis=1)
    return raw[["state_key", "reported_heat_deaths_2018_2022", "reported_heat_deaths_annual_mean"]]


def build_demographic_vulnerability(pca_path: Path, age_path: Path, occupation_path: Path, deaths_path: Path) -> pd.DataFrame:
    frame = read_pca(pca_path).merge(read_age(age_path), on="state_key", how="inner", validate="one_to_one")
    frame = frame.merge(read_occupation_total(occupation_path), on="state_key", how="left")
    frame = frame.merge(read_death_history(deaths_path), on="state_key", how="left")
    frame = frame.rename(columns={"Name": "state", "TOT_P": "population_2011", "TOT_WORK_P": "workers_total"})
    # Use the age-table total for age shares; retain PCA total as a source-consistency field.
    frame["older_60_plus_share"] = frame["older_60_plus"] / frame["All ages"]
    frame["child_0_4_share"] = frame["0-4"] / frame["All ages"]
    frame["worker_population_share"] = frame["workers_total"] / frame["population_2011"]
    frame["outdoor_worker_share"] = frame["outdoor_workers"] / frame["workers_total"]
    for indicator in AGE_WEIGHTS:
        frame[f"{indicator}_scaled"] = capped_percentile_scale(frame[indicator])
    frame["demographic_vulnerability_0_1"] = sum(
        weight * frame[f"{indicator}_scaled"] for indicator, weight in AGE_WEIGHTS.items()
    )
    frame["demographic_vulnerability_0_100"] = 100 * frame["demographic_vulnerability_0_1"]
    frame["reported_heat_death_rate_per_100k_annual"] = (
        100000 * frame["reported_heat_deaths_annual_mean"] / frame["population_2011"]
    )
    return frame.sort_values("state").reset_index(drop=True)


def build_town_demographic_vulnerability(pca_path: Path, state_demographics: pd.DataFrame) -> pd.DataFrame:
    """Build town scores while preserving the state-level limitation of C-14 age data.

    Census C-14 supplied here cannot identify each town's residents aged 60+.
    The corresponding state share is therefore retained as a labelled proxy;
    all child and worker indicators are calculated from the local town record.
    """
    towns = read_towns(pca_path)
    state_fields = state_demographics[["State", "state", "state_key", "older_60_plus_share", "older_60_plus_share_scaled",
                                       "reported_heat_deaths_2018_2022", "reported_heat_deaths_annual_mean"]].copy()
    state_fields["state_code"] = state_fields["State"].astype(str).str.zfill(2)
    towns = towns.merge(state_fields.drop(columns="State"), on="state_code", how="left", validate="many_to_one")
    if towns["state"].isna().any():
        raise ValueError("Some town records could not be matched to their state demographic record.")
    towns["child_0_6_share"] = towns["children_0_6"] / towns["population_2011"]
    towns["worker_population_share"] = towns["workers_total"] / towns["population_2011"]
    towns["outdoor_worker_share"] = towns["outdoor_workers"] / towns["workers_total"]
    towns["state_older_60_plus_share"] = towns["older_60_plus_share"]
    towns["state_older_60_plus_share_scaled"] = towns["older_60_plus_share_scaled"]
    for indicator in ["child_0_6_share", "worker_population_share", "outdoor_worker_share"]:
        towns[f"{indicator}_scaled"] = capped_percentile_scale(towns[indicator])
    towns["town_demographic_vulnerability_0_1"] = sum(
        weight * towns[f"{indicator}_scaled"] for indicator, weight in TOWN_WEIGHTS.items()
    )
    towns["town_demographic_vulnerability_0_100"] = 100 * towns["town_demographic_vulnerability_0_1"]
    return towns.sort_values(["state", "town"]).reset_index(drop=True)


def wbgt_hazard(latitude: float, longitude: float, days: int) -> dict:
    weather = fetch_weather_snapshot(latitude=latitude, longitude=longitude, forecast_days=days)
    hourly = calculate_hourly_wbgt(weather, latitude, longitude)
    valid = [record for record in hourly if record["wbgt_c"] is not None]
    if not valid:
        raise RuntimeError("No converged WBGT records were returned by the forecast pipeline.")
    peak = max(valid, key=lambda record: record["wbgt_c"])
    hazard = max(0.0, min(1.0, (peak["wbgt_c"] - WBGT_SCREENING_ANCHOR_C) / (WBGT_TOP_ALERT_C - WBGT_SCREENING_ANCHOR_C)))
    return {"forecast_peak_wbgt_c": peak["wbgt_c"], "forecast_peak_time_utc": peak["time"],
            "thermal_hazard_0_1": hazard, "thermal_hazard_0_100": 100 * hazard,
            "wbgt_converged_hours": len(valid), "wbgt_requested_hours": len(hourly)}


def risk_band(score: float) -> str:
    if score < 10:
        return "Low"
    if score < 30:
        return "Moderate"
    if score < 60:
        return "High"
    return "Very high"


def load_locations(path: Path | None, state: str | None, latitude: float | None, longitude: float | None) -> pd.DataFrame:
    """Load batch locations, or create one legacy Pune/state-style record."""
    if path:
        locations = pd.read_csv(path)
        required = {"city", "state", "latitude", "longitude"}
        missing = required.difference(locations.columns)
        if missing:
            raise ValueError(f"Location CSV is missing columns: {sorted(missing)}")
    else:
        if state is None or latitude is None or longitude is None:
            raise ValueError("Provide --locations, or all of --state, --lat, and --lon.")
        locations = pd.DataFrame([{"city": "Pune", "state": state, "latitude": latitude, "longitude": longitude}])
    locations["state_key"] = locations["state"].map(clean_state_name)
    locations["requested_census_town"] = locations.get("census_town_name", locations["city"]).astype(str).str.strip()
    locations["town_key"] = locations["requested_census_town"].map(clean_town_name)
    locations["latitude"] = pd.to_numeric(locations["latitude"], errors="raise")
    locations["longitude"] = pd.to_numeric(locations["longitude"], errors="raise")
    return locations


def build_city_risk(locations: pd.DataFrame, towns: pd.DataFrame, days: int) -> pd.DataFrame:
    records = []
    for location in locations.to_dict("records"):
        match = towns[(towns["state_key"] == location["state_key"]) & (towns["town_key"] == location["town_key"])]
        # The optional census_town_name resolves cases such as Pune (CB) and
        # Pune (M Corp.), which deliberately share the same simplified key.
        if len(match) > 1 and location.get("requested_census_town") != location["city"]:
            exact = match[match["town"].astype(str).str.strip().str.casefold() == str(location["requested_census_town"]).casefold()]
            if len(exact) == 1:
                match = exact
        if len(match) != 1:
            candidates = towns[towns["state_key"] == location["state_key"]]["town"].drop_duplicates().head(20).tolist()
            raise ValueError(f"Could not uniquely match {location['city']!r} in {location['state']!r} to a Census town. "
                             f"Set census_town_name in the location CSV. Sample candidates: {candidates}")
        hazard = wbgt_hazard(location["latitude"], location["longitude"], days)
        record = match.iloc[0].to_dict()
        record.update(hazard)
        record.update({"city": location["city"], "weather_latitude": location["latitude"], "weather_longitude": location["longitude"]})
        record["mortality_risk_factor_0_100"] = 100 * record["town_demographic_vulnerability_0_1"] * record["thermal_hazard_0_1"]
        record["mortality_risk_band"] = risk_band(record["mortality_risk_factor_0_100"])
        records.append(record)
    return pd.DataFrame(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pca", type=Path, required=True); parser.add_argument("--age", type=Path, required=True)
    parser.add_argument("--occupation", type=Path, required=True); parser.add_argument("--deaths", type=Path, required=True)
    parser.add_argument("--state", help="State/UT to pair with --lat and --lon when --locations is not used.")
    parser.add_argument("--lat", type=float); parser.add_argument("--lon", type=float)
    parser.add_argument("--locations", type=Path, help="CSV: city,state,latitude,longitude[,census_town_name].")
    parser.add_argument("--days", type=int, default=5); parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "outputs")
    args = parser.parse_args()
    if args.days < 1:
        parser.error("--days must be positive")
    for path in [args.pca, args.age, args.occupation, args.deaths]:
        if not path.is_file():
            parser.error(f"Input not found: {path}")

    demographics = build_demographic_vulnerability(args.pca, args.age, args.occupation, args.deaths)
    towns = build_town_demographic_vulnerability(args.pca, demographics)
    locations = load_locations(args.locations, args.state, args.lat, args.lon)
    result = build_city_risk(locations, towns, args.days)
    result["generated_at_utc"] = datetime.now(timezone.utc).isoformat()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    demographics.to_csv(args.output_dir / "demographic_vulnerability_state.csv", index=False)
    towns.to_csv(args.output_dir / "demographic_vulnerability_town.csv", index=False)
    result.to_csv(args.output_dir / "city_mortality_risk_screening.csv", index=False)
    metadata = {"method": "Census-based demographic vulnerability times forecast Liljegren WBGT thermal hazard",
                "age_weights": AGE_WEIGHTS, "wbgt_screening_anchor_c": WBGT_SCREENING_ANCHOR_C,
                "town_weights": TOWN_WEIGHTS, "wbgt_top_alert_c": WBGT_TOP_ALERT_C,
                "warning": "Screening index only; town age 60+ uses a state-level C-14 proxy, not a local age count."}
    (args.output_dir / "method_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(result[["city", "town", "state", "town_demographic_vulnerability_0_100", "forecast_peak_wbgt_c", "thermal_hazard_0_100", "mortality_risk_factor_0_100", "mortality_risk_band"]].to_string(index=False))


if __name__ == "__main__":
    main()
