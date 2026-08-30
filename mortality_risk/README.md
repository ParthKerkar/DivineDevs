# Mortality-risk screening pipeline

This folder calculates a **screening mortality-risk factor** for heat. It is
not a calibrated prediction of deaths or a causal mortality rate.

## Geographic coverage

The supplied Census C-14 and heat-death CSV are state-level. The PCA workbook
is town/village-level, so `demographic_vulnerability_town.csv` calculates
local child and worker exposure indicators for every urban Census town. Its
60+ component is explicitly a **state-level age proxy**, since a town-level
elderly count was not supplied. A future map should use matching town/ward
age data before treating that proxy as a local measurement.

## Inputs

The command below uses the four supplied files:

- `2011-IndiaStateDistSbDistTwn-0000.xlsx`: Census PCA population and worker
  counts.
- `DDW-0000C-14.xls`: Census age distribution; used to calculate population
  aged 60+ and children aged 0-4.
- `DDW-B25A-0000.xlsx`: main-worker occupational table; retained as an input
  and used to report non-agricultural main workers, but not scored because its
  occupation labels do not reliably identify heat exposure.
- `RS_Session_266_AU_359_A_i.csv`: historical, state-level annual heat deaths
  for 2018-2022. It is reported as context only, not used to train/calibrate
  the score because reporting completeness is unknown.

## Method

All demographic components are robustly min-max normalised over the available
states (5th-95th percentiles, capped at 0 and 1):

```
demographic vulnerability = 0.45 * age 60+ share
                          + 0.15 * age 0-4 share
                          + 0.15 * worker-population share
                          + 0.25 * outdoor-worker share
```

`outdoor-worker share` is the Census PCA count of cultivators plus agricultural
labourers (main and marginal workers), divided by all workers. It is a
transparent occupational-exposure proxy, not a claim that all other workers
are unexposed.

The thermal hazard uses the maximum forecast Liljegren outdoor WBGT in the
requested period:

```
thermal hazard = clip((maximum WBGT - 26.0) / (32.2 - 26.0), 0, 1)
mortality risk factor (0-100) = 100 * demographic vulnerability * thermal hazard
```

26.0 C is a conservative heat-screening anchor and 32.2 C is the existing
project's top WBGT alert threshold. Change these only after local validation
against reliable health outcomes.

## Run

For a single city, from `DivineDevs`:

```powershell
python mortality_risk/build_mortality_risk.py `
  --pca "C:\Users\SEAN\Downloads\2011-IndiaStateDistSbDistTwn-0000.xlsx" `
  --age "C:\Users\SEAN\Downloads\DDW-0000C-14.xls" `
  --occupation "C:\Users\SEAN\Downloads\DDW-B25A-0000.xlsx" `
  --deaths "C:\Users\SEAN\Downloads\RS_Session_266_AU_359_A_i.csv" `
  --state "Maharashtra" --lat 18.5204 --lon 73.8567 --days 5
```

For multiple cities, make a CSV with `city,state,latitude,longitude` and an
optional `census_town_name` for unambiguous matching. See
`locations_example.csv`, then run the same command with `--locations PATH` in
place of `--state`, `--lat`, and `--lon`. One forecast WBGT calculation is
made for each supplied coordinate.

Outputs are written to `mortality_risk/outputs/` and contain source dates,
the exact component values, forecast peak WBGT, and the final score.
