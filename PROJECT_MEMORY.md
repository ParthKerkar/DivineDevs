# Project Persistent Memory --- Extreme Heatwave Early Warning System

## 1. Project Objective

Build an intelligent, localized **Extreme Heatwave Early Warning and
Human Thermal Stress Index** system for Pune.

The system should shift from:

> "What will the weather be?"

to:

> "What will the weather do to human health?"

The final platform is intended to support: - 3--5 day heat-stress
forecasting - Human thermal stress assessment - Mortality-risk
prediction - Hospitalization-risk prediction - Pune ward/zone-level
visualization - Automated heat-health alerts and recommended actions

------------------------------------------------------------------------

## 2. IMPORTANT ARCHITECTURE DECISION

### The system must NOT directly forecast WBGT.

WBGT is a deterministic physical index calculated from meteorological
variables.

The correct architecture is:

``` text
WEATHER FORECAST API
        ↓
3–5 DAY FORECAST
        ↓
Raw meteorological variables
        ↓
Liljegren outdoor WBGT calculation
        ↓
WBGT / thermal stress
        ↓
Mortality Risk Model
        ↓
Hospitalization Risk Model
        ↓
Pune Ward/Zone GIS Dashboard
        ↓
Alerts + Public Health Actions
```

Do NOT train an ML model to predict WBGT if the required meteorological
inputs are already available.

------------------------------------------------------------------------

## 3. Weather Data Source

### Primary operational weather API: Open-Meteo

Use Open-Meteo for current and forecast meteorological data.

Official documentation: https://open-meteo.com/en/docs

The API should provide the following variables:

  Required input      Open-Meteo variable
  ------------------- -------------------------------------------------
  Air temperature     `temperature_2m`
  Relative humidity   `relative_humidity_2m`
  Wind speed          `wind_speed_10m`
  Solar radiation     `shortwave_radiation`
  Surface pressure    `surface_pressure`
  Timestamp           API timestamp
  Location            Latitude/longitude for the target ward/location

Use `timezone=Asia/Kolkata` for Pune operational data.

The system requires at least a 3--5 day forecast. Open-Meteo can provide
a longer forecast horizon, so the application can request the required
period.

------------------------------------------------------------------------

## 4. WBGT Calculation

### Required method: Liljegren outdoor WBGT

The project must use the **Liljegren outdoor WBGT algorithm**.

Do NOT replace it with: - Heat Index - Stull wet-bulb approximation -
OSHA simplified WBGT - A random empirical WBGT formula - An ML-predicted
WBGT

The standard WBGT relationship is:

``` text
WBGT = 0.7 × Tw + 0.2 × Tg + 0.1 × Ta
```

where:

-   `Tw` = natural wet-bulb temperature
-   `Tg` = globe temperature
-   `Ta` = air temperature

The Liljegren algorithm derives the required intermediate physical
quantities from the meteorological inputs.

### Important

Do NOT require an external API to provide: - natural wet-bulb
temperature - globe temperature - WBGT

These should be calculated by the project's implementation of the
Liljegren algorithm from the raw meteorological inputs.

------------------------------------------------------------------------

## 5. Current Weather → WBGT Pipeline

For every forecast timestamp:

``` text
timestamp
latitude
longitude
temperature_2m
relative_humidity_2m
wind_speed_10m
shortwave_radiation
surface_pressure
        ↓
Liljegren WBGT implementation
        ↓
WBGT
```

The implementation must preserve units and perform explicit unit
conversion where required by the Liljegren equations.

Do not silently mix: - °C and K - hPa and Pa - km/h and m/s - W/m² and
other radiation units

The code should document every conversion.

------------------------------------------------------------------------

## 6. Historical Data / Model Training

Historical ERA5/ERA5-Land data already collected for the project remains
useful.

Historical data should contain the same or compatible meteorological
variables needed by the operational pipeline.

Recommended historical workflow:

``` text
Historical ERA5 / ERA5-Land
        ↓
Temperature
Relative Humidity
Wind Speed
Solar Radiation
Surface Pressure
        ↓
Liljegren WBGT calculation
        ↓
Historical WBGT
        ↓
Join with historical health outcomes
        ↓
Training dataset
```

The purpose of historical data is primarily to build and validate the
**health-impact models**, not to train a model to reproduce WBGT.

------------------------------------------------------------------------

## 7. ML Models

The ML component should focus on predicting health impacts.

### Target 1: Mortality Risk

Predict heat-associated mortality risk/spikes using historical: -
weather variables - WBGT / thermal stress - temporal features -
demographic variables - relevant historical mortality information

### Target 2: Hospitalization Risk

Predict heat-associated hospitalization risk/spikes using: - weather
variables - WBGT / thermal stress - temporal features - demographic
variables - historical hospitalization information

Do not invent health labels if reliable historical target data is
unavailable.

------------------------------------------------------------------------

## 8. Forecasting Strategy

The operational system receives weather forecasts for the next 3--5
days.

For each future timestamp:

``` text
Forecast weather
      ↓
Calculate WBGT
      ↓
Generate thermal-stress features
      ↓
Health-risk model
      ↓
Mortality risk
Hospitalization risk
```

The system therefore produces a **3--5 day health-risk forecast**,
driven by forecast meteorology.

------------------------------------------------------------------------

## 9. Ward-Level / Hyperlocal Design

The final system should support Pune ward/zone-level risk.

Each ward/location should have: - latitude - longitude - population
information - relevant demographic indicators - weather input - WBGT -
thermal stress level - mortality risk - hospitalization risk - alert
level

Possible architecture:

``` text
Pune Ward
   ↓
Ward coordinates
   ↓
Weather forecast for location
   ↓
WBGT
   ↓
Risk models
   ↓
Ward risk score
   ↓
GIS map
```

Do not claim true ward-level weather resolution unless the data
source/model actually supports it.

For an initial prototype, ward representative coordinates/grid points
may be used and clearly documented.

------------------------------------------------------------------------

## 10. Current Development Priority

The immediate development sequence is:

### Step 1 --- Weather API integration

Connect Open-Meteo and retrieve:

``` text
temperature_2m
relative_humidity_2m
wind_speed_10m
shortwave_radiation
surface_pressure
```

for Pune and a 3--5 day forecast.

### Step 2 --- Validate API data

Check: - timestamps - timezone - missing values - units - realistic
ranges

### Step 3 --- Implement Liljegren WBGT

Implement the algorithm exactly and independently.

### Step 4 --- Validate WBGT

Test against known/reference calculations or published examples where
possible.

### Step 5 --- Create the forecast pipeline

``` text
API → preprocessing → Liljegren WBGT → thermal stress
```

### Step 6 --- Integrate health-risk models

Only after the weather → WBGT pipeline is reliable.

### Step 7 --- Build GIS dashboard and alerts

Only after the underlying risk values are validated.

------------------------------------------------------------------------

## 11. Critical Rules for AI Coding Agents

When using Codex or another coding agent on this project:

1.  Read this file before modifying the project.
2.  Do not change the agreed architecture without explicitly discussing
    the change.
3.  Do not create an ML model that directly predicts WBGT.
4.  Do not use a random WBGT formula.
5.  Use the Liljegren outdoor WBGT algorithm.
6.  Do not introduce WBGT-derived features prematurely if the current
    development step only requires the raw forecast variables.
7.  Do not invent missing datasets, labels, APIs, formulas, or
    demographic values.
8.  Clearly distinguish:
    -   observed/current weather
    -   forecast weather
    -   calculated WBGT
    -   model-predicted health risk
9.  Keep data preprocessing reproducible.
10. Document units and transformations.
11. Validate every major calculation before building downstream
    components.
12. Prefer scientifically defensible methods over convenient
    approximations.

------------------------------------------------------------------------

## 12. Important Distinction: Raw vs Derived Variables

### Raw/forecast variables

These come from the weather source:

``` text
Temperature
Relative Humidity
Wind Speed
Solar Radiation
Surface Pressure
```

### Derived physical variables

These are calculated by the WBGT implementation:

``` text
Natural Wet-Bulb Temperature
Globe Temperature
WBGT
```

### Health-risk outputs

These come from ML/statistical models:

``` text
Mortality Risk
Hospitalization Risk
```

Do not mix these three categories.

------------------------------------------------------------------------

## 13. High-Level Final Architecture

``` text
                    WEATHER FORECAST API
                         (Open-Meteo)
                              ↓
                  CURRENT + 3–5 DAY DATA
                              ↓
       ┌─────────────────────────────────────────┐
       │ Temperature                             │
       │ Relative Humidity                       │
       │ Wind Speed                              │
       │ Solar Radiation                         │
       │ Surface Pressure                        │
       └─────────────────────────────────────────┘
                              ↓
                   LILJEGREN WBGT MODEL
                              ↓
       ┌─────────────────────────────────────────┐
       │ Natural Wet-Bulb Temperature            │
       │ Globe Temperature                       │
       │ WBGT                                    │
       └─────────────────────────────────────────┘
                              ↓
                    THERMAL STRESS
                              ↓
             ┌─────────────────────────────┐
             │ Mortality Risk Model        │
             │ Hospitalization Risk Model  │
             └─────────────────────────────┘
                              ↓
                    3–5 DAY RISK FORECAST
                              ↓
                     PUNE WARD GIS MAP
                              ↓
                     ALERTS + ACTIONS
```

------------------------------------------------------------------------

## 14. Non-Goals at the Current Stage

Do NOT currently: - forecast WBGT directly with ML - create unnecessary
WBGT-derived ML features - build mortality prediction before
establishing the weather/WBGT pipeline - substitute Heat Index for
WBGT - use a simplified wet-bulb approximation without explicit
approval - randomly select weather APIs or formulas - fabricate
hospitalization/mortality data - claim hyperlocal accuracy that the
underlying weather data cannot support

------------------------------------------------------------------------

## 15. Source/Method References

Primary weather source: - Open-Meteo Forecast API - Open-Meteo
Historical Weather API

WBGT method: - Liljegren et al. outdoor WBGT calculation methodology

The exact scientific implementation and equations should be documented
in the codebase when the WBGT module is implemented.
