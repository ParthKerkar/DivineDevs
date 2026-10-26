# SIH 26083: Extreme Heatwave Early Warning and Human Thermal Stress Index
# Comprehensive Codebase Audit, Project Reconstruction & Technical Documentation

**Report Date:** 2026-10-26  
**Auditor:** Senior ML Engineer, Python Backend Architect & Scientific Computing Auditor  
**Audit Scope:** Full static code analysis of `/home/parker/sih/DivineDevs`, historical git trajectories (`origin/master`, `origin/parker`, `origin/anti`, `origin/arnav`, `origin/sean`), offline regression unit test suite execution, and SIH Problem Statement 26083 reconciliation.  
**Report Location:** `/home/parker/sih/SIH_26083_COMPLETE_CODEBASE_AUDIT.md`

---

## Deliverable A: Executive Summary

### 1. What the Project Actually Does Today
The repository under `/home/parker/sih/DivineDevs` hosts an operational, lightweight, zero-dependency Python and JavaScript web application called **HeatShield (HeatWatch India)**.

Contrary to conventional hackathon prototypes that assemble disconnected mockups, this project implements a working, end-to-end meteorological and biometeorological processing pipeline with the following capabilities:
1. **Live Weather Ingestion:** Connects on demand to the Open-Meteo Weather Forecast REST API to retrieve hourly meteorological variables (temperature at 2m, relative humidity at 2m, wind speed at 10m, surface pressure, and downwelling shortwave solar radiation) for any coordinate or city worldwide, with a 5-day forecast horizon.
2. **Physical Thermal Stress Modeling (Liljegren Outdoor WBGT):** Implements a faithful Python port of the Liljegren et al. (2008) outdoor Wet-Bulb Globe Temperature (WBGT) algorithm (originally written in C by Argonne National Laboratory). It iteratively solves the coupled heat and mass transfer energy balances for a wicked cylinder (natural wet-bulb temperature, $T_{nwb}$) and a 2-inch black copper sphere (globe temperature, $T_g$), combining them into outdoor WBGT ($0.7 T_{nwb} + 0.2 T_g + 0.1 T_a$).
3. **Epidemiological Mortality Risk Estimation:** Evaluates relative risk ($RR$), attributable fraction ($AF$), and an application-level normalized Mortality Risk Index ($MRI$, 0–100) using a parametric exposure-response function derived from Cheng, Lung, Hwang (2019) (*Environmental Research*), anchored at a $30.0^\circ\text{C}$ WBGT baseline ($RR = 1.00$) and a $33.0^\circ\text{C}$ threshold candidate ($RR = 1.09$).
4. **Risk Context Synthesis & Evidence-Guided Recommendations:** Evaluates forecast trajectories (e.g. `RAPIDLY_INCREASING`, `STABLE`, `IMPROVING`) and multi-day thermal persistence ($\ge 3$ elevated days) across the 5-day horizon. Filters a 660-line structured library of health-protective interventions attributed to the World Health Organization (WHO), NIOSH, and OSHA for three audiences (`PUBLIC`, `OUTDOOR_WORKER`, `AUTHORITY`). If a Google Gemini API key is provided, it attempts generative personalization with strict JSON schema constraints and a zero-failure fallback to deterministic evidence.
5. **Interactive GIS Dashboard & REST API:** A custom multi-threaded Python HTTP server (`dashboard_server.py`) serving a Leaflet-based single-page application. Features a nationwide interpolated thermal stress SVG overlay across the boundary of India (derived via inverse distance weighting of a 2-degree lat/lon grid), city marker alerts, dynamic city search geocoding, current environmental metrics, 5-day daily peak WBGT forecasts, and health risk tooltips.

### 2. What the Project Does NOT Do (Critical Deficits vs. SIH 26083)
Despite its strengths in physical and software engineering, the codebase has major gaps when measured against the full requirements of SIH Problem Statement 26083:
1. **NO Machine Learning / Predictive Models:** There is **zero ML code**. No Scikit-Learn, PyTorch, TensorFlow, or statistical time-series models exist in the repository. Weather forecasting is entirely outsourced to Open-Meteo's external Numerical Weather Prediction (NWP) API.
2. **NO Hospitalization Risk Modeling:** Hospitalization risk is completely unaddressed in the active codebase. (An earlier experimental branch attempted a discrete threshold comparison from Agarwal et al. 2018, but this was discarded).
3. **NO Demographic / Socioeconomic Vulnerability Integration:** The Mortality Risk Index is calculated solely from outdoor WBGT. It does not account for age distribution (elderly 65+ or children), poverty indices, housing quality, access to air conditioning, or outdoor worker census counts.
4. **NO Hyperlocal / Ward-Level GIS Resolution:** Despite project documentation specifying ward-level early warning for Pune, the operational code operates at the macro/city level. There are no ward boundary shapefiles/GeoJSONs, no ward microclimate models, and no urban heat island (UHI) adjustments.
5. **Epidemiological Context Mismatch:** The mortality model is borrowed from a study conducted in Taiwan (Cheng et al., 2019) and applies an arbitrary doubling of risk slope ($\beta_2 = 2\beta_1$) above $33^\circ\text{C}$. It has not been calibrated or validated against Indian mortality data or Pune municipal health surveillance records.
6. **NO Automated Alert Dispatch:** There are no SMS, WhatsApp, email, or Common Alerting Protocol (CAP) integrations for pushing warnings to municipal authorities or citizens.

---

## Deliverable B: Architecture Diagram

```mermaid
flowchart TD
    subgraph External_APIs["External API Services"]
        OM_GEO["Open-Meteo Geocoding API<br/>(geocoding-api.open-meteo.com)"]
        OM_WX["Open-Meteo Forecast API<br/>(api.open-meteo.com/v1/forecast)"]
        GEMINI["Google Gemini API (Optional)<br/>(gemini-3.7-flash:generateContent)"]
    end

    subgraph Backend_Server["Backend Server (dashboard_server.py)"]
        HTTP_HANDLER["HeatRiskApiHandler<br/>(ThreadingHTTPServer :8000)"]
        CACHE_GRID["_cache['india-grid']<br/>(TTL: 300s)"]
        CACHE_DASH["_dashboard_cache<br/>(TTL: 300s)"]
        CACHE_RISK["_heat_risk_cache<br/>(TTL: 300s)"]
    end

    subgraph Ingestion_Geocoding["Ingestion & Geocoding Layer"]
        GEO["geocoding.py<br/>geocode_city()"]
        WX_INGEST["weather_api.py<br/>fetch_weather_snapshot()<br/>build_weather_url()"]
    end

    subgraph Physics_Engine["Physical Biometeorology Engine (weather_api.py)"]
        WIND["wind_speed_10m_to_2m()<br/>Log-Profile Scaling (z0=0.1m)"]
        SOLAR["solar_position() & adjust_solar_irradiance()<br/>NOAA Fractional Year & Beam/Diffuse"]
        LILJEGREN["calculate_liljegren_outdoor_wbgt()<br/>Argonne wbgt.c Port"]
        TNWB["_natural_wet_bulb()<br/>Cylinder Heat/Mass Iterative Solver"]
        TGLOBE["_globe_temperature()<br/>Sphere Radiative/Convective Solver"]
        WBGT_EQ["WBGT = 0.7*Tnwb + 0.2*Tg + 0.1*Ta"]
        FLAG["risk_category()<br/>Blue | Green | Yellow | Orange | Red"]
    end

    subgraph Health_Risk_Engine["Health Risk Engine (mortality_risk.py)"]
        RR_CALC["calculate_relative_risk()<br/>Cheng et al. (2019) Log-Linear Model<br/>Baseline: <=30°C, Threshold: 33°C"]
        AF_CALC["calculate_attributable_fraction()<br/>AF = (RR - 1) / RR"]
        MRI_CALC["calculate_mortality_risk_index()<br/>Piecewise Continuous Mapping (0–100)"]
        TIER_CALC["classify_risk_category()<br/>Low | Moderate | High | Very High | Extreme"]
    end

    subgraph Context_Recommendation["Context & Recommendation Engines"]
        CTX_ENG["risk_context_engine.py<br/>build_risk_context()<br/>analyze_forecast_trend()<br/>analyze_heat_persistence()<br/>synthesize_overall_heat_health_level()"]
        REC_LIB["recommendation_library.py<br/>660 lines WHO / NIOSH / OSHA<br/>(PUBLIC, OUTDOOR_WORKER, AUTHORITY)"]
        REC_ENG["recommendation_engine.py<br/>generate_deterministic_recommendations()"]
        REC_AI["call_ai_personalizer() & validate_ai_output()<br/>Gemini Fallback & Guardrails"]
    end

    subgraph Frontend_GIS["GIS Dashboard Frontend (dashboard/)"]
        HTML["index.html<br/>Layout & Responsive Shell"]
        APP_JS["app.js<br/>Leaflet 1.9.4 Map | City Autocomplete<br/>SVG Interpolated Color Raster Layer"]
        HEALTH_JS["health-panel.js<br/>Fetch Interceptor & Health UI Render"]
        CSS["styles.css<br/>Card Styles, Badges & Tooltips"]
        GEOJSON["india-boundary.geojson<br/>India National ADM0 MultiPolygon"]
    end

    %% Data flow connections
    Frontend_GIS <-->|HTTP REST Requests| HTTP_HANDLER
    HTTP_HANDLER --> Ingestion_Geocoding
    HTTP_HANDLER --> CACHE_GRID
    HTTP_HANDLER --> CACHE_DASH
    HTTP_HANDLER --> CACHE_RISK

    GEO -->|HTTP GET /search| OM_GEO
    WX_INGEST -->|HTTP GET /v1/forecast| OM_WX

    WX_INGEST --> Physics_Engine
    WIND --> LILJEGREN
    SOLAR --> LILJEGREN
    TNWB --> WBGT_EQ
    TGLOBE --> WBGT_EQ
    WBGT_EQ --> FLAG

    WBGT_EQ --> Health_Risk_Engine
    RR_CALC --> AF_CALC
    RR_CALC --> MRI_CALC
    MRI_CALC --> TIER_CALC

    FLAG & TIER_CALC --> CTX_ENG
    CTX_ENG --> REC_ENG
    REC_LIB --> REC_ENG
    REC_ENG -->|Optional Prompt| GEMINI
    REC_AI --> REC_ENG
    REC_ENG --> HTTP_HANDLER
```

### End-to-End Observation Walkthrough
To trace data through the implemented system, consider an observation for Pune ($18.5204^\circ\text{N}, 73.8567^\circ\text{E}$) during an afternoon heat episode:

1. **Ingestion:** `weather_api.py:fetch_weather_snapshot()` requests Open-Meteo for coordinates `(18.5204, 73.8567)` with `timezone=GMT` and `wind_speed_unit=ms`.
   * Sample observation: `time = "2026-05-15T08:30:00Z"` (14:00 IST), $T_a = 38.5^\circ\text{C}$, $RH = 42\%$, $WS_{10m} = 3.2\text{ m/s}$, $SR = 850\text{ W/m}^2$, $P = 955\text{ hPa}$.
2. **Log-Profile Wind Adjustment:**
   $$WS_{2m} = WS_{10m} \times \frac{\ln(2.0 / 0.1)}{\ln(10.0 / 0.1)} = 3.2 \times \frac{\ln(20)}{\ln(100)} \approx 3.2 \times 0.6505 = 2.08\text{ m/s}$$
3. **Solar Geometry (NOAA):**
   * Computes fractional day of year $\gamma$, solar declination $\delta$, equation of time $EOT$, and solar hour angle $\omega$.
   * Computes cosine of solar zenith angle $cza \approx 0.88$ and earth-sun distance factor $soldist \approx 1.01$.
   * Adjusts shortwave radiation into direct normal and diffuse components: $SR_{norm} \approx 680\text{ W/m}^2$, $f_{dir} \approx 0.78$.
4. **Iterative Heat & Mass Balance Solvers:**
   * `_natural_wet_bulb()` solves for the steady-state temperature of a cylindrical wick ($D=7\text{ mm}, L=25.4\text{ mm}$), balancing atmospheric longwave radiation, direct/diffuse solar absorption, convective heat transfer, and evaporative cooling via iterative relaxation (damping factor 0.1, convergence tolerance $0.02^\circ\text{C}$). Converges at $T_{nwb} = 28.42^\circ\text{C}$.
   * `_globe_temperature()` balances radiative gain from sky, ground, and direct sun against convective cooling from a 2-inch black copper sphere ($D=50.8\text{ mm}$). Converges at $T_g = 47.15^\circ\text{C}$.
5. **Physical WBGT Formulation:**
   $$WBGT = 0.7(28.42) + 0.2(47.15) + 0.1(38.5) = 19.894 + 9.430 + 3.850 = 33.17^\circ\text{C}$$
   * Flag Color: $33.17^\circ\text{C} \ge 32.2^\circ\text{C} \implies \mathbf{Red}$ (Physical Extreme).
6. **Epidemiological Risk Evaluation (`mortality_risk.py`):**
   * Because $WBGT = 33.17^\circ\text{C} > 33.0^\circ\text{C}$, risk evaluation enters the accelerated tier:
     $$\beta_1 = \frac{\ln(1.09)}{33.0 - 30.0} \approx 0.028735, \quad \beta_2 = 2 \times \beta_1 \approx 0.057470$$
     $$RR = 1.09 \times \exp(0.057470 \times (33.17 - 33.0)) = 1.09 \times \exp(0.00977) \approx 1.1007$$
   * Attributable Fraction:
     $$AF = \frac{1.1007 - 1.0}{1.1007} \approx 0.0915 \quad (9.15\% \text{ of mortality risk attributable to heat})$$
   * Mortality Risk Index (piecewise linear):
     $$MRI = 70.0 + (33.17 - 33.0) \times 10.0 = 71.7 / 100$$
   * Epidemiological Risk Category: $71.7 \in [70.0, 85.0) \implies \mathbf{Very\ High}$.
7. **Context Synthesis & Recommendations (`risk_context_engine.py`):**
   * Multi-day trend evaluated against 5-day maxima. If maximum reaches $34.2^\circ\text{C}$, trend is classified as `INCREASING` ($\Delta \ge 1.0^\circ\text{C}$).
   * Multi-day persistence: count of forecast days with $WBGT \ge 29.5^\circ\text{C}$ or $MRI \ge 55$. If 4 days, elevated heat persistence triggered.
   * Overall Heat-Health Level: $\max(\text{Physical: EXTREME}, \text{Epidemiological: VERY\_HIGH}) \implies \mathbf{EXTREME}$.
   * Filters `RECOMMENDATION_LIBRARY` for `audience="PUBLIC"`, `severity="EXTREME"`, generating prioritized actions (e.g. hydrate with 500ml/hr, avoid outdoor exposure between 11:00 and 16:00, seek air-conditioned shelter).
8. **Dashboard Presentation:**
   * Served via `/api/wbgt?lat=18.5204&lon=73.8567` or `/api/heat-risk?city=Pune`.
   * The Leaflet UI displays the city card with red background, WBGT $33.2^\circ\text{C}$, MRI $71.7/100$, Relative Risk $1.101$, and authoritative advice.

---

## Deliverable C: Comprehensive File-by-File Inventory

The workspace `/home/parker/sih` contains one primary project repository located at `/home/parker/sih/DivineDevs`. The entire codebase comprises **18 source and configuration files totaling 5,140 lines of code**.

| File / Directory | Purpose | Key Classes & Functions | Status | Dependencies |
|---|---|---|---|---|
| `DivineDevs/` | Root repository folder for the SIH project. | N/A | Active workspace | Git |
| `DivineDevs/PROJECT_MEMORY.md` | Architectural guidelines, design constraints, and team coordination memory. | Sections 1–15 | Complete / Reference | None |
| `DivineDevs/.gitignore` | Git exclusion rules. | Excludes `.env`, `.env.*`, `__pycache__/`, `*.pyc` | Complete | Git |
| `DivineDevs/weather_api.py` | Core biometeorological ingestion, solar geometry, and Liljegren WBGT solver. | `build_weather_url()`, `fetch_weather_snapshot()`, `wind_speed_10m_to_2m()`, `solar_position()`, `adjust_solar_irradiance()`, `esat()`, `_natural_wet_bulb()`, `_globe_temperature()`, `calculate_liljegren_outdoor_wbgt()`, `calculate_hourly_wbgt()`, `fetch_heat_risk_for_coordinates()`, `fetch_heat_risk_for_city()` | Fully implemented, verified against PyWBGT fixtures | Python stdlib (`math`, `json`, `urllib.request`, `datetime`) |
| `DivineDevs/mortality_risk.py` | Parametric epidemiological mortality risk calculations based on Cheng et al. (2019). | `calculate_relative_risk()`, `calculate_attributable_fraction()`, `calculate_mortality_risk_index()`, `classify_risk_category()`, `evaluate_mortality_risk()` | Fully implemented, verified via unit tests | Python stdlib (`math`, `typing`) |
| `DivineDevs/geocoding.py` | Geocoding service resolving city names to latitude/longitude using Open-Meteo. | `geocode_city()`, `clear_geocode_cache()` | Fully implemented, memory-cached (1h TTL) | Python stdlib (`urllib.request`, `json`, `time`) |
| `DivineDevs/risk_context_engine.py` | Synthesizes physical WBGT, MRI, multi-day forecast trends, and heat persistence into unified risk tiers. | `get_wbgt_severity_level()`, `get_mri_severity_level()`, `analyze_forecast_trend()`, `analyze_heat_persistence()`, `synthesize_overall_heat_health_level()`, `generate_derived_insights()`, `build_risk_context()` | Fully implemented, verified via unit tests | Python stdlib (`typing`) |
| `DivineDevs/recommendation_library.py` | Structured repository of evidence-based heat-health protective measures. | `RECOMMENDATION_LIBRARY`, `get_library_recommendations()` | Fully implemented (660 lines of structured data) | Python stdlib (`typing`) |
| `DivineDevs/recommendation_engine.py` | Recommendation pipeline applying deterministic rules, dynamic priority weighting, and optional Gemini LLM tailoring. | `get_ai_api_key()`, `generate_deterministic_recommendations()`, `call_ai_personalizer()`, `validate_ai_output()`, `get_heat_health_recommendations_for_risk_payload()`, `get_heat_health_recommendations()` | Fully implemented with safe fallback | Python stdlib (`urllib.request`, `json`, `logging`, `time`) |
| `DivineDevs/dashboard_server.py` | Multi-threaded HTTP server providing REST API endpoints and static frontend serving. | `HeatRiskApiHandler`, `spatial_grid_points()`, `dashboard_grid()`, `geocode_city_list()`, `get_cached_dashboard()`, `create_server()` | Fully implemented and operational | Python stdlib (`http.server`, `urllib.parse`, `json`, `time`) |
| `DivineDevs/dashboard/index.html` | Frontend markup shell, Leaflet CDN links, layout panels, and inline DOM observer. | Root markup, SVG brand icons, detail panel templates | Fully implemented | Leaflet 1.9.4 CSS/JS |
| `DivineDevs/dashboard/app.js` | Main client-side GIS dashboard logic, Leaflet map initialization, raster SVG overlay rendering, and city marker handlers. | `initTheme()`, `renderDetails()`, `selectCity()`, `colorFor()`, `interpolate()`, `renderField()`, `loadField()`, `renderSearchResults()` | Fully implemented | Leaflet 1.9.4 |
| `DivineDevs/dashboard/health-panel.js` | Client-side health panel controller; monkey-patches `window.fetch` to intercept duplicate calls and render tooltips. | `renderHealth()`, `window.fetch` monkey-patch wrapper | Fully implemented | Vanilla JavaScript |
| `DivineDevs/dashboard/india-boundary.geojson` | Simplified boundary polygons for the Republic of India (ADM0). | GeoJSON FeatureCollection (MultiPolygon, 91 KB) | Static resource | GeoJSON standard |
| `DivineDevs/dashboard/styles.css` | Complete stylesheet for desktop and mobile GIS dashboard, dark/light themes, info-cards, and tooltips. | 1,149 lines of custom CSS | Fully implemented | CSS3 |
| `DivineDevs/tests/test_weather_api.py` | Regression tests comparing Liljegren WBGT calculations against published PyWBGT fixtures. | `LiljegrenRegressionTests`, `WeatherApiContractTests` | Verified (6 tests pass in 0.001s) | Python stdlib `unittest` |
| `DivineDevs/tests/test_mortality_risk.py` | Unit tests verifying mathematical correctness of Cheng et al. relative risk, AF, and MRI equations. | `MortalityRiskModelTests` | Verified (8 tests pass in 0.001s) | Python stdlib `unittest` |
| `DivineDevs/tests/test_geocoding.py` | Integration tests for Open-Meteo geocoding and caching. | `GeocodingServiceTests` | Implemented (Requires live network) | Python stdlib `unittest` |
| `DivineDevs/tests/test_heat_risk_api.py` | Integration tests validating end-to-end weather -> WBGT -> mortality risk API contracts and HTTP server routes. | `HeatRiskPipelineTests`, `HttpServerApiTests` | Implemented (Requires live network) | Python stdlib `unittest` |
| `DivineDevs/tests/test_recommendations.py` | Unit and integration tests for evidence filtering, trend detection, AI validator, and recommendation routes. | `RecommendationLibraryTests`, `RiskContextEngineTests`, `RecommendationEngineTests`, `RecommendationsApiHttpTests` | Verified offline suites pass (12 tests pass in 0.001s) | Python stdlib `unittest` |

### Obsolete, Abandoned, and Redundant Files Identified Across History
Through deep git inspection (`origin/parker`, `origin/anti`, commit `83e2ed4`), several earlier approaches were identified:
1. **Abandoned Demographic Vulnerability Pipeline (`83e2ed4`):**
   * Contained `mortality_risk/build_mortality_risk.py` and CSV outputs (`demographic_vulnerability_town.csv`, `demographic_vulnerability_state.csv`).
   * Attempted to calculate a demographic vulnerability score from 2011 Census tables (age 60+, children 0-4, agricultural laborers).
   * **Reason for Removal:** The Census data required external local Excel files (`C:\Users\SEAN\Downloads\...`) that were not present in the repository, and reporting completeness of heat-death records was unverified. It was purged in commit `5b43166`.
2. **Abandoned India Heat Index (IHI) & Hospitalization Layer (`origin/parker`):**
   * Contained `health_impact/service.py`, `HEALTH_IMPACT.md`, `health_impact/data/india_climate_zones.geojson`, and PDFs (`EST2023b.pdf`, `IJOEM-22-57.pdf`).
   * Implemented Choudhary et al. (2024) India Heat Index ($IHI = 0.820 T_a + 0.123 RH + 0.004 SR - 0.117 WS - 6.727$) and Agarwal et al. (2018) hospitalization comparisons ($T_a \ge 39^\circ\text{C}$ vs $<38^\circ\text{C}$).
   * **Reason for Replacement:** Project guidelines in `PROJECT_MEMORY.md` forbade using Heat Index instead of WBGT and prohibited mixing IHI coefficients with WBGT. The team abandoned this approach to unify the pipeline around Liljegren WBGT and Cheng et al. (2019).
3. **Frontend Code Duplication / Monkey-Patch Coupling:**
   * In `dashboard/index.html` (lines 8–10), an inline `<script>` registers a `MutationObserver` on the `#place` header to fetch `/api/heat-risk?city=` and `/api/recommendations?city=`.
   * Concurrently, `dashboard/health-panel.js` monkey-patches `window.fetch` to intercept these calls and satisfy them locally from the already-fetched `/api/wbgt` response.
   * This is an unusual circular coupling that works around legacy frontend code rather than cleanly refactoring the data flow.

---

## Deliverable D: Technical Deep Dive

### 1. Data Ingestion Architecture
* **Provider:** Open-Meteo REST API (`https://api.open-meteo.com/v1/forecast`).
* **Protocol & Parameters:**
  * Request URL constructed in `weather_api.py:build_weather_url()`.
  * Queried variables:
    * `current`: `temperature_2m`, `relative_humidity_2m`, `wind_speed_10m`, `surface_pressure`, `shortwave_radiation`
    * `hourly`: `temperature_2m`, `relative_humidity_2m`, `wind_speed_10m`, `shortwave_radiation`, `surface_pressure`
  * Parameters: `timezone=GMT`, `wind_speed_unit=ms`, `forecast_days=5`.
* **Spatial & Temporal Characteristics:**
  * Point coordinates passed as decimal degrees (`latitude`, `longitude`).
  * Time resolution: Hourly forecast intervals for 120 hours (5 days).
  * Timestamps returned in ISO 8601 UTC format (e.g. `2026-08-31T14:00`).
* **Data Sanitization & Preprocessing:**
  * `validate_location()` asserts $-90 \le \text{lat} \le 90$ and $-180 \le \text{lon} \le 180$.
  * `_parse_utc()` parses ISO strings and ensures timezone awareness (`timezone.utc`).
  * Unit conversions: Temperature is converted from Celsius to Kelvin ($T_k = T_c + 273.15$); Relative Humidity is converted from percentage to fraction ($rh = RH / 100$); surface pressure is kept in hectopascals/millibars ($mb \equiv hPa$).

### 2. Liljegren Outdoor WBGT Physics Implementation
The Wet-Bulb Globe Temperature is defined as:
$$WBGT = 0.7 T_{nwb} + 0.2 T_g + 0.1 T_a$$
Where:
* $T_a$: Ambient air temperature ($^\circ\text{C}$)
* $T_{nwb}$: Natural wet-bulb temperature ($^\circ\text{C}$), representing evaporative cooling on a sweat-wetted cylindrical surface under natural air motion and solar/thermal radiation.
* $T_g$: Globe temperature ($^\circ\text{C}$), representing equilibrium radiation temperature inside a 50.8 mm matte-black sphere.

#### A. Boundary Layer Wind Scaling
Liljegren's model requires wind speed at instrument height ($2\text{ m}$), whereas meteorological standard is $10\text{ m}$. `wind_speed_10m_to_2m()` applies the neutral log-law wind profile:
$$u_{2m} = \max\left(u_{10m} \times \frac{\ln(z_{ref} / z_0)}{\ln(z_{10} / z_0)}, u_{min}\right)$$
Where $z_{ref} = 2.0\text{ m}$, $z_{10} = 10.0\text{ m}$, surface roughness length $z_0 = 0.1\text{ m}$ (representing open terrain with low vegetation/suburban fringe), and minimum air speed $u_{min} = 0.13\text{ m/s}$ (preventing division-by-zero or infinite thermal resistance in calm air).

#### B. Solar Position & Radiance Partitioning
In `solar_position()`, the NOAA solar position equations estimate the solar zenith angle ($\theta_z$, with $cza = \cos \theta_z$) and Earth-Sun orbital distance correction ($soldist$):
* Day angle: $\gamma = \frac{2\pi}{365} (DOY - 1 + \frac{\text{hour} - 12}{24})$.
* Solar declination $\delta$ and Equation of Time ($EOT$) evaluated via Fourier expansions.
* Solar hour angle: $\omega = \frac{\pi}{12} (\text{solar minutes} / 4 - 180)$.
* Cosine solar zenith angle: $cza = \sin(\text{lat}) \sin(\delta) + \cos(\text{lat}) \cos(\delta) \cos(\omega)$.

`adjust_solar_irradiance()` partitions the Open-Meteo global horizontal shortwave radiation ($SR$) into direct and diffuse components:
* Top of Atmosphere (TOA) normal irradiance: $I_{TOA} = \frac{I_{solar} \cdot \max(0, cza)}{soldist^2}$, where $I_{solar} = 1367.0\text{ W/m}^2$.
* Normalized clearness index: $K = \min\left(\frac{SR}{I_{TOA}}, 0.85\right)$.
* Direct beam fraction: $f_{dir} = \exp(3.0 - 1.34 K - 1.65 / K)$, clamped between $0.0$ and $0.9$.

#### C. Natural Wet-Bulb Iterative Balance (`_natural_wet_bulb`)
The energy balance for the wet wick cylinder equates sensible heat transfer, radiative heat exchange, and latent heat of evaporation:
$$h_c (T_a - T_{nwb}) + R_{net} = \lambda \cdot j_w$$
Where:
* Convective heat transfer coefficient $h$ is derived from cylinder Nusselt number:
  $$Re = \frac{u_{2m} \rho D_{wick}}{\mu}, \quad Nu = 0.281 Re^{0.6} Pr^{0.44}, \quad h = Nu \frac{k_{air}}{D_{wick}}$$
  (with $D_{wick} = 0.007\text{ m}, L_{wick} = 0.0254\text{ m}$).
* Net radiation $R_{net}$ accounts for:
  * Atmospheric longwave emission: $\varepsilon_{atm} = 0.575 (e_{air})^{0.143}$.
  * Surface longwave emission: $\varepsilon_{sfc} = 0.999$.
  * Direct and diffuse solar absorption by the wick with albedo $\alpha_{wick} = 0.40$ and emissivity $\varepsilon_{wick} = 0.95$.
* Evaporative mass flux $j_w$ depends on vapor pressure deficit:
  $$e_{sat}(T) = 1.004 \times 6.1121 \times \exp\left(17.502 \frac{T - 273.15}{T - 32.18}\right)$$
* Iteration: Successive substitution with heavy damping:
  $$T_{next} = 0.9 T_{prev} + 0.1 T_{current}$$
  Terminates when $|T_{current} - T_{prev}| < 0.02\text{ K}$ or reaches 50 iterations.

#### D. Globe Temperature Iterative Balance (`_globe_temperature`)
The globe temperature represents radiation equilibrium on a 50.8 mm ($0.0508\text{ m}$) black copper sphere ($\alpha_{globe} = 0.05, \varepsilon_{globe} = 0.95$):
$$h_{sphere} (T_g - T_a) = \varepsilon_{globe} \sigma \left(\frac{T_{sky}^4 + T_{gnd}^4}{2} - T_g^4\right) + S_{absorbed}$$
Where sphere convection coefficient is given by:
$$Nu_{sphere} = 2.0 + 0.6 Re^{1/2} Pr^{1/3}, \quad h_{sphere} = Nu_{sphere} \frac{k_{air}}{D_{globe}}$$
Iterates until temperature difference converges within $0.02\text{ K}$.

### 3. Epidemiological Mortality Risk Model
Implemented in `mortality_risk.py`, based on:
> Cheng, Y.-T., Lung, S.-C. C., & Hwang, J.-S. (2019). "New approach to identifying proper thresholds for a heat warning system using health risk increments." *Environmental Research*, 169, 180–189.

#### A. Mathematical Formulation
1. **Reference Baseline Exposure:** Anchor at $WBGT_0 = 30.0^\circ\text{C}$. For any exposure $WBGT \le 30.0^\circ\text{C}$, the relative risk is:
   $$RR = 1.00$$
2. **Threshold Candidate:** Cheng et al. identified $33.0^\circ\text{C}$ as the critical inflection point associated with a 9% excess all-cause mortality risk ($RR = 1.09$).
3. **Log-Linear Slope ($\beta_1$):**
   $$\beta_1 = \frac{\ln(1.09)}{33.0 - 30.0} = \frac{0.086178}{3.0} \approx 0.028726\text{ per }^\circ\text{C}$$
4. **Sub-Threshold Elevated Zone ($30.0^\circ\text{C} < WBGT \le 33.0^\circ\text{C}$):**
   $$RR(WBGT) = \exp\left(\beta_1 (WBGT - 30.0)\right)$$
5. **Super-Threshold Extreme Heat Zone ($WBGT > 33.0^\circ\text{C}$):**
   The implementation assumes an accelerated risk multiplier with slope $\beta_2 = 2 \times \beta_1 \approx 0.057452$:
   $$RR(WBGT) = 1.09 \times \exp\left(\beta_2 (WBGT - 33.0)\right)$$
6. **Attributable Fraction ($AF$):**
   $$AF = \frac{RR - 1}{RR} \quad (\text{for } RR \ge 1.00; \quad 0.0 \text{ otherwise})$$
7. **Mortality Risk Index ($MRI$):**
   A piecewise continuous mapping scaling risk to a 0–100 index:
   $$MRI(WBGT) = \begin{cases} 
   0.0 & \text{if } WBGT \le 0 \\
   (WBGT / 28.0) \times 20.0 & \text{if } 0 < WBGT \le 28.0 \\
   20.0 + \frac{WBGT - 28.0}{2.0} \times 15.0 & \text{if } 28.0 < WBGT \le 30.0 \\
   35.0 + \frac{WBGT - 30.0}{3.0} \times 35.0 & \text{if } 30.0 < WBGT \le 33.0 \\
   \min\left(100.0, 70.0 + (WBGT - 33.0) \times 10.0\right) & \text{if } WBGT > 33.0 
   \end{cases}$$
8. **Categorical Risk Tiers:**
   * $MRI < 30.0$: `Low`
   * $30.0 \le MRI < 55.0$: `Moderate`
   * $55.0 \le MRI < 70.0$: `High`
   * $70.0 \le MRI < 85.0$: `Very High`
   * $MRI \ge 85.0$: `Extreme`

### 4. Risk Context Engine & Forecast Trend Synthesis
Implemented in `risk_context_engine.py`:
* **Forecast Trend Detection (`analyze_forecast_trend`):** Compares the peak WBGT in the 5-day forecast against the current WBGT ($\Delta = \max(WBGT_{forecast}) - WBGT_{current}$):
  * $\Delta \ge +3.0^\circ\text{C} \implies \mathbf{RAPIDLY\_INCREASING}$
  * $\Delta \ge +1.0^\circ\text{C} \implies \mathbf{INCREASING}$
  * $\Delta \le -1.5^\circ\text{C} \implies \mathbf{IMPROVING}$
  * Otherwise $\implies \mathbf{STABLE}$
* **Heat Persistence Analysis (`analyze_heat_persistence`):** Counts consecutive or total days where daily maximum $WBGT \ge 29.5^\circ\text{C}$ or $MRI \ge 55.0$. If elevated heat persists for $\ge 3$ days, the overall heat-health tier is escalated by one level (e.g. from `MODERATE` to `HIGH`).

### 5. Recommendation Engine & Safety Architecture
Implemented in `recommendation_engine.py`:
* **Deterministic Selection:** Pulls approved actions from `recommendation_library.py` based on `audience` (`PUBLIC`, `OUTDOOR_WORKER`, `AUTHORITY`) and `overall_heat_health_level`.
* **Dynamic Priority Scoring:** Re-ranks actions depending on forecast trend and specific physiological risk categories (`HYDRATION`, `REST_RECOVERY`, `WORK_SCHEDULING`, `PUBLIC_ALERT`).
* **Generative AI Personalizer (`call_ai_personalizer`):**
  * When `GEMINI_API_KEY` is present, issues an HTTP POST to Google Gemini (`gemini-3.7-flash:generateContent`).
  * System prompt instructs the model to tailor wording and prioritize interventions strictly from the approved input set.
* **Output Validation Guardrails (`validate_ai_output`):**
  * Verifies output against a blacklist of medical/clinical keywords (`"prescribe"`, `"medication"`, `"pill"`, `"aspirin"`, `"paracetamol"`, `"antibiotic"`).
  * Verifies against ungrounded mortality claims (`"exact deaths"`, `"will die"`, `"fatalities count"`).
  * Enforces category matching against the approved evidence library.
  * If the LLM response fails validation, times out (30s), or errors, the system silently and deterministically falls back to the static evidence library.

### 6. Backend API & GIS Dashboard Architecture
* **Server Framework:** Pure Python `ThreadingHTTPServer` (`dashboard_server.py`) binding to `0.0.0.0:8000`.
* **Core REST Endpoints:**
  * `GET /api/health`: Health status probe.
  * `GET /api/wbgt-grid`: Generates a national grid of WBGT observations across India. Pre-computes 2-degree spatial grid points ($8^\circ\text{N}$ to $35^\circ\text{N}$, $68^\circ\text{E}$ to $97^\circ\text{E}$) inside `india_polygons()`. Issues a single bulk Open-Meteo request and returns observation points with coordinates, WBGT, and flag color. Cached for 300 seconds.
  * `GET /api/search?q=<query>`: Auto-completes Indian cities from a hardcoded list of 90+ major cities and aliases, falling back to Open-Meteo Geocoding API filtered to `country_code == 'IN'`.
  * `GET /api/wbgt?lat=<lat>&lon=<lon>`: Returns hourly WBGT, current conditions, daily peak forecasts, and attached health recommendations for a specific coordinate. Cached for 300 seconds.
  * `GET /api/heat-risk?city=<city>`: Executes the complete end-to-end pipeline (geocoding $\rightarrow$ forecast retrieval $\rightarrow$ Liljegren WBGT $\rightarrow$ Cheng mortality risk).
  * `GET /api/recommendations?city=<city>&audience=<aud>`: Returns tailored health recommendations. Supports `POST /api/recommendations` with JSON payload.
* **Frontend Implementation (`dashboard/`):**
  * Built using vanilla HTML5, CSS3, and Leaflet 1.9.4.
  * Features a continuous vector color field rendered onto an off-screen HTML SVG and layered as a Leaflet `L.imageOverlay`.
  * Interpolation algorithm (`app.js:interpolate()`): Inverse Distance Weighting (IDW, $w_i = 1 / d_i^2$) across all national grid points. Clipped cleanly to India's sovereign land boundary via an SVG `<clipPath>` defined by `india-boundary.geojson`.
  * Responsive sidebar panel presenting current WBGT flag badge, 5-day forecast cards, Mortality Risk Index, Relative Risk, and evidence-grounded advisories.

---

## Deliverable E: SIH Requirements Compliance Matrix

The following matrix audits the implementation status of each core requirement stipulated under SIH Problem Statement 26083:

| SIH 26083 Requirement | Current Implementation Status | Code Evidence (File & Functions) | Implementation Reality vs. Expectation | Critical Technical Gap |
|---|---|---|---|---|
| **1. Weather Data Ingestion** | **Implemented & Verified** | `weather_api.py:fetch_weather_snapshot()`, `build_weather_url()` | Ingests real-time and forecast $T_a$, $RH$, $WS$, $SR$, and $P$ from Open-Meteo API. | Relies exclusively on external third-party API; no local IMD or AWS sensor fallback. |
| **2. Historical Weather Dataset** | **Not Implemented** | None (Mentioned only in `PROJECT_MEMORY.md:151-175`) | No historical ERA5, IMD, or gridded reanalysis datasets exist in the codebase. | Historical data is not available locally for offline model training or calibration. |
| **3. Weather Forecasting** | **Partially Implemented (Outsourced)** | `weather_api.py:build_weather_url(forecast_days=5)` | Forecasts are retrieved from Open-Meteo NWP models. No custom ML model predicts future weather. | Zero native ML weather prediction; completely dependent on upstream API. |
| **4. 3–5 Day Forecast Horizon** | **Implemented & Verified** | `weather_api.py:HOURLY_FIELDS`, `daily_max_wbgt()` | Open-Meteo queried for 5-day horizon (120 hours); aggregated to daily maximum peaks. | Only hourly and daily peaks supported; no multi-model ensemble aggregation. |
| **5. Hourly Forecast Granularity** | **Implemented & Verified** | `weather_api.py:calculate_hourly_wbgt()` | Computes Liljegren WBGT for every individual forecast hour. | Stored only in-memory; not persisted to a time-series database. |
| **6. WBGT Physical Metric** | **Implemented & Verified** | `weather_api.py:calculate_liljegren_outdoor_wbgt()` | Rigorous port of Argonne's Liljegren (2008) outdoor WBGT solver ($0.7 T_{nwb} + 0.2 T_g + 0.1 T_a$). | Log-profile wind adjustment uses fixed $z_0=0.1\text{m}$ rather than dynamic land-cover roughness. |
| **7. Human Thermal Stress Index** | **Implemented & Verified** | `weather_api.py:risk_category()`, `risk_context_engine.py:get_wbgt_severity_level()` | Physical flag color tiers (Blue, Green, Yellow, Orange, Red) aligned with ISO 7243 / OSHA standards. | UTCI is not implemented; system relies solely on outdoor WBGT. |
| **8. Mortality Risk Index** | **Partially Implemented (Parametric Only)** | `mortality_risk.py:calculate_relative_risk()`, `calculate_mortality_risk_index()` | Computes $RR$, $AF$, and $MRI$ (0–100) using Cheng et al. (2019) exposure-response curve. | Based on Taiwan population curve; arbitrary $\beta_2$ doubling above $33^\circ\text{C}$; not trained on Indian data. |
| **9. Hospitalization Risk** | **Not Implemented** | Purged from master (existed on `origin/parker:health_impact/service.py`) | No hospitalization risk formulas, indices, or outputs exist in the active codebase. | 100% missing from active release. |
| **10. Historical Health Outcome Data** | **Not Implemented** | Purged from master (referenced in `83e2ed4:mortality_risk/README.md`) | Zero mortality, morbidity, or hospitalization records exist in the repository. | No ground truth health data available to validate or train epidemiological models. |
| **11. Demographic Risk Adjustment** | **Not Implemented** | None in master (purged from `83e2ed4`) | Risk score does not incorporate age (60+ / children), poverty, outdoor workers, or housing. | Identical weather produces identical risk regardless of whether location is an affluent suburb or dense slum. |
| **12. GIS Visualization** | **Implemented & Verified** | `dashboard/app.js:renderField()`, `dashboard_server.py:spatial_grid_points()` | Leaflet map with nationwide IDW interpolated SVG heat layer clipped to India boundary. | Resolution is national/regional (~220km grid), not urban/neighborhood scale. |
| **13. Ward-Level / Zone Forecasting** | **Not Implemented** | None (Specified in `PROJECT_MEMORY.md:228-262`) | System resolves cities as single points. No Pune ward boundary GeoJSON or ward data. | Completely absent. No municipal ward-level spatial breakdown. |
| **14. Color-Coded Alerts** | **Implemented & Verified** | `dashboard/styles.css`, `dashboard/app.js:colors` | Dual color coding: WBGT flag colors and 5-tier epidemiological health-level badges. | UI-only visual display; no audio alerts or browser push notifications. |
| **15. Automated Public Health Advisories** | **Implemented & Verified** | `recommendation_engine.py`, `recommendation_library.py` | Generates structured advisories for Public, Outdoor Workers, and Authorities grounded in WHO/NIOSH/OSHA. | Advisories are rendered on dashboard; not pushed automatically to stakeholders. |
| **16. SMS / WhatsApp Alert Integration** | **Not Implemented** | None | No Twilio, WhatsApp Business API, Gupshup, or SMS gateway code exists. | 100% missing. |
| **17. Municipal Heat-Action Triggers** | **Partially Implemented (Advisory Only)** | `recommendation_library.py` (`audience="AUTHORITY"`) | Library includes trigger actions (activate cooling shelters, adjust work shifts, hospital surge prep). | Triggers are purely informational strings in an API response; no automated municipal workflow dispatch. |

---

## Deliverable F: Bugs, Architectural Oddities, and Technical Risks

### Finding 1: Arbitrary Risk Acceleration Slope Doubling Above $33^\circ\text{C}$
* **Severity:** High (Methodological / Scientific Integrity)
* **File & Function:** `mortality_risk.py:calculate_relative_risk()`, lines 26–29 & 82–85
* **Evidence:**
  ```python
  BETA_1: float = math.log(1.0 + MORTALITY_INCREMENT_AT_THRESHOLD) / (THRESHOLD_WBGT_C - REFERENCE_WBGT_C)
  BETA_2: float = 2.0 * BETA_1  # Slope for extreme heat above critical threshold
  ...
  else:
      return (1.0 + MORTALITY_INCREMENT_AT_THRESHOLD) * math.exp(BETA_2 * (wbgt - THRESHOLD_WBGT_C))
  ```
* **Why it Matters:** In the cited paper (Cheng et al., 2019), the authors do not specify a doubling of $\beta$ above $33.0^\circ\text{C}$. This slope doubling ($\beta_2 = 2\beta_1$) is an ad-hoc heuristic introduced by the developers to simulate exponential risk acceleration under extreme heat. While physiological strain does accelerate at extreme temperatures, presenting this specific multiplier as a published scientific formula misrepresents the underlying literature.
* **Recommended Correction:** Explicitly document $\beta_2 = 2\beta_1$ in docstrings and API responses as a conservative engineering safety acceleration factor rather than attributing the entire piecewise formulation to Cheng et al.

### Finding 2: Lack of Regional Indian Calibration for Relative Risk Model
* **Severity:** High (Epidemiological Validity)
* **File & Function:** `mortality_risk.py:evaluate_mortality_risk()`, lines 48–53
* **Evidence:** The codebase cites Cheng et al. (2019), which analyzed health outcomes in Taiwan. The code comments note:
  ```python
  # Indian Context: Choudhary et al. (2024, Environ. Sci. Technol.) documented heat stress
  # mortality impacts in India, but utilized the India Heat Index (IHI) rather than WBGT.
  # Per epidemiological rigor, IHI coefficients are NOT applied to WBGT.
  ```
* **Why it Matters:** The baseline threshold of $30.0^\circ\text{C}$ WBGT and the 9% increment at $33.0^\circ\text{C}$ WBGT from Taiwan cannot be assumed to apply directly to Indian populations (e.g. Pune, Vidarbha, or Rajasthan) without calibration. Acclimatization thresholds in central and northern India often exceed those of subtropical island climates.
* **Recommended Correction:** Calibrate local minimum mortality temperature (MMT) thresholds using Indian municipal mortality data (e.g. Pune Municipal Corporation civil registration data) or published Indian biometeorological literature.

### Finding 3: Brittle Monkey-Patching of `window.fetch` in Frontend
* **Severity:** Medium (Code Quality / Architectural Brittleness)
* **File & Function:** `dashboard/health-panel.js`, lines 79–101
* **Evidence:**
  ```javascript
  window.fetch = async (...args) => {
    const url = String(args[0]);
    if (url.includes("/api/heat-risk?") || url.includes("/api/recommendations?")) {
      if (!selectedPayload) await new Promise(resolve => { payloadReady = resolve; });
      const health = selectedPayload.health || {};
      const body = url.includes("/api/heat-risk?")
        ? { current: { mortalityRiskIndex: selectedPayload.current?.mortality_risk_index... } }
        : health;
      return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
    }
    const response = await originalFetch(...args);
    ...
  ```
* **Why it Matters:** `dashboard/index.html` contains an inline script that independently issues `fetch('/api/heat-risk?city=' + city)` and `fetch('/api/recommendations?city=' + city)`. To avoid duplicate HTTP roundtrips, `health-panel.js` overrides global `window.fetch` to intercept these requests and mock responses from `selectedPayload.health`. Overriding global browser primitives is error-prone, complicates debugging, and can break other asynchronous network operations.
* **Recommended Correction:** Remove the redundant inline script in `index.html`. Unify all client-side data binding inside `app.js` and `health-panel.js` so that a single unified API payload is retrieved and rendered cleanly without monkey-patching.

### Finding 4: In-Memory Caching Without Persistence or Concurrency Locks
* **Severity:** Medium (Reliability & Scalability)
* **File & Function:** `dashboard_server.py:dashboard_grid()`, `_cache`, `_dashboard_cache`
* **Evidence:**
  ```python
  _cache: Dict = {}
  _dashboard_cache: Dict[Tuple[float, float], Dict[str, Any]] = {}
  ...
  def dashboard_grid():
      key = "india-grid"
      cached = _cache.get(key)
      if cached and time.time() - cached["created"] < CACHE_SECONDS:
          return cached["payload"]
  ```
* **Why it Matters:** Caching is stored in global Python dictionaries without thread synchronization locks (`threading.Lock`). Under concurrent requests, race conditions can trigger duplicate expensive upstream calls to Open-Meteo. Furthermore, because state is in-memory, server restarts wipe the cache, re-triggering upstream latency.
* **Recommended Correction:** Wrap cache reads and writes in `threading.Lock()` or adopt a standard caching backend (e.g. Redis or SQLite).

### Finding 5: Roughness Length Hardcoded to 0.1m Across All Terrain
* **Severity:** Low (Micro-scale Accuracy)
* **File & Function:** `weather_api.py:wind_speed_10m_to_2m()`, line 98
* **Evidence:**
  ```python
  def wind_speed_10m_to_2m(wind_speed_10m, roughness_length=0.1):
  ```
* **Why it Matters:** Roughness length $z_0 = 0.1\text{ m}$ is typical for open farmland or airport runways. In dense urban centers (such as central Pune or Mumbai), building morphology creates aerodynamic roughness lengths of $z_0 \approx 0.8\text{ m} - 1.5\text{ m}$. Using $0.1\text{ m}$ overestimates 2m wind speed in urban street canyons, which causes the Liljegren convective cooling term to overestimate heat dissipation and underestimate urban thermal stress.
* **Recommended Correction:** Implement a lookup table or GIS land-use classifier that dynamically selects $z_0$ based on urban vs. rural coordinate classification.

---

## Deliverable G: Current Project Status Assessment

| Subsystem | Actual State | Production Readiness | What Works Reliably | What Is Incomplete or Missing |
|---|---|---|---|---|
| **Weather Ingestion** | Fully operational | Near Production (for non-critical use) | Dynamic query generation, UTC parsing, parameter mapping for any global coordinate. | No local sensor ingestion; no resilience against Open-Meteo API rate limits. |
| **WBGT Physical Solver** | Fully operational | Production Grade | Mathematically verified against PyWBGT; exact heat/mass balance iteration. | Roughness length is fixed; no stability-dependent Monin-Obukhov adjustment. |
| **Mortality Risk Model** | Operational (Parametric) | Research / Prototype | Clean evaluation of $RR$, $AF$, and $MRI$; robust boundary and threshold handling. | No Indian calibration; arbitrary slope doubling; no actual local mortality labels. |
| **Hospitalization Risk** | Abandoned | Not Functional | None in master. | Completely absent. |
| **Demographic Weighting** | Abandoned | Not Functional | None in master. | No age-stratified or occupational risk adjustment. |
| **Context & Recommendations** | Fully operational | Working Prototype | Trend detection, persistence tracking, WHO/NIOSH/OSHA evidence matching, safe LLM fallback. | Automated SMS/WhatsApp alerting missing; no real cooling center geo-database. |
| **GIS Visualization** | Fully operational | Working Prototype | Leaflet base map, national SVG heat overlay, city autocomplete search, responsive design. | Macro-level national interpolation only; no Pune ward boundaries. |
| **Backend API** | Fully operational | Developer Grade | Clean multi-threaded HTTP server; standard REST endpoints; JSON contracts. | Python stdlib `http.server` lacks WSGI/ASGI production scalability, auth, and rate-limiting. |

---

## Deliverable H: Prioritized Development Roadmap

### Phase 1: Localized Pune Ward-Level GIS & Microclimate Resolution (Immediate Priority)
1. **Acquire Pune Municipal Corporation (PMC) Ward Boundaries:** Download or create GeoJSON boundary polygons for Pune's 15 administrative zones and electoral wards.
2. **Integrate Ward Shapefiles into GIS Dashboard:** Replace the national India-wide SVG overlay with a dual-mode map: National overview and a high-resolution Pune Ward drill-down view.
3. **Hyperlocal Weather Downscaling / Urban Heat Island (UHI) Offsets:** Integrate land surface temperature (LST) or Copernicus Sentinel/MODIS urban canopy thermal offsets to adjust ward-level air temperature and surface roughness ($z_0$).

### Phase 2: Epidemiological Grounding & Demographic Vulnerability Integration
1. **Incorporate Pune Demographic Vulnerability Index (DVI):** Extract ward-level census data for vulnerable demographics (population over 65, children under 5, informal settlement density, outdoor construction/vendor density).
2. **Composite Risk Formulation:** Formulate the final Ward Health Risk Index as a multiplicative combination of hazard, exposure, and vulnerability:
   $$\text{Heat Health Risk} = \text{Physical Hazard (WBGT)} \times \text{Epidemiological Exposure (RR)} \times \text{Demographic Vulnerability (DVI)}$$
3. **Calibrate Against Indian Climate Zones:** Replace the generic Taiwan model with climate-zone-specific thresholds (e.g. Choudhary et al. thresholds for Semi-arid Pune vs. Humid Chennai).

### Phase 3: Hospitalization Risk Modeling Implementation
1. **Formulate Hospital Surge Predictive Index:** Implement a dedicated hospitalization risk index reflecting acute admissions for heat exhaustion, dehydration, and cardiovascular decompensation.
2. **Epidemiological Thresholding:** Model hospitalization risk increments using published occupational and clinical evidence (e.g. Agarwal et al. or ICMR surveillance data) with dedicated alert tiers for emergency departments.

### Phase 4: Production Backend Hardening & Database Persistence
1. **Migrate to FastAPI / ASGI:** Replace standard library `ThreadingHTTPServer` with FastAPI, providing asynchronous concurrency, automatic OpenAPI documentation, and strict Pydantic schema validation.
2. **Time-Series Persistence:** Integrate PostgreSQL with PostGIS and TimescaleDB to persist historical weather forecasts, calculated WBGT series, and municipal alert logs.
3. **Resilient Weather Caching & Redundancy:** Add Redis caching and implement secondary meteorological providers (e.g. IMD API or NOAA GFS direct) to ensure zero downtime.

### Phase 5: Automated Alert Dispatch & Municipal Decision Support
1. **SMS & WhatsApp Dispatch Pipeline:** Integrate Twilio or an Indian telecommunication SMS gateway (CDAC / NIC SMS gateway) to trigger automated localized heat advisories.
2. **Common Alerting Protocol (CAP) Feed:** Generate standard XML/JSON CAP alerts compatible with NDMA (National Disaster Management Authority) and PMC disaster management dashboards.
3. **Interactive Threshold Triggers:** Allow municipal administrators to set custom operational thresholds that automatically issue work-stoppage orders for outdoor labor between 12:00 and 15:00.

---

## Deliverable I: AI Handover Brief & Context Specification

```markdown
# AI ASSISTANT HANDOVER BRIEF — SIH 26083 HEATWAVE EARLY WARNING SYSTEM

## 1. Project Identity & Objective
This project is an Extreme Heatwave Early Warning and Human Thermal Stress Index platform developed for Smart India Hackathon (SIH) Problem Statement 26083. Its purpose is to transition heat warnings from simple temperature alerts to biometeorological, impact-based public health risk forecasts.

## 2. Codebase Location & Technology Stack
- Root Directory: `/home/parker/sih/DivineDevs`
- Language & Runtime: Python 3.12 (Zero third-party dependencies; pure standard library).
- Web Server: `http.server.ThreadingHTTPServer` running on port 8000.
- Frontend: HTML5, CSS3, Vanilla JavaScript, Leaflet 1.9.4 (CDN), ESRI basemap tiles.
- Weather Ingestion: Open-Meteo REST API (free tier, no API key required).
- AI Personalization: Google Gemini API via standard `urllib.request` (optional via `GEMINI_API_KEY`).

## 3. Core Architectural Modules
1. `weather_api.py`:
   - Fetches 5-day hourly forecast from Open-Meteo (`fetch_weather_snapshot`).
   - Converts 10m wind to 2m wind using log profile (`wind_speed_10m_to_2m`).
   - Computes solar position and beam/diffuse solar irradiance (`solar_position`, `adjust_solar_irradiance`).
   - Implements Liljegren (2008) outdoor WBGT solver ported from Argonne `wbgt.c` (`calculate_liljegren_outdoor_wbgt`).
   - Aggregates hourly series to daily maximum peaks (`daily_max_wbgt`).
2. `mortality_risk.py`:
   - Implements Cheng et al. (2019) relative mortality risk curve (`calculate_relative_risk`).
   - Baseline: WBGT <= 30°C (RR = 1.00); Candidate threshold: WBGT = 33°C (RR = 1.09).
   - Computes Attributable Fraction: AF = (RR - 1) / RR.
   - Computes normalized Mortality Risk Index (0–100): `calculate_mortality_risk_index`.
3. `risk_context_engine.py`:
   - Evaluates multi-day forecast trends (`analyze_forecast_trend`) and heat persistence (`analyze_heat_persistence`).
   - Synthesizes physical WBGT and epidemiological MRI into an overall severity level (`synthesize_overall_heat_health_level`).
4. `recommendation_library.py`:
   - Contains 660 lines of structured health guidance categorized by audience (`PUBLIC`, `OUTDOOR_WORKER`, `AUTHORITY`) and tier (`LOW` to `EXTREME`), cited to WHO, NIOSH, and OSHA.
5. `recommendation_engine.py`:
   - Selects and prioritizes recommendations based on risk context.
   - Optionally calls Gemini LLM for wording personalization with rigorous output validation and deterministic fallback.
6. `dashboard_server.py`:
   - Serves static dashboard files from `dashboard/`.
   - Exposes REST endpoints: `/api/health`, `/api/wbgt-grid`, `/api/search`, `/api/wbgt`, `/api/heat-risk`, `/api/recommendations`.
7. `dashboard/`:
   - `index.html`, `styles.css`, `app.js`, `health-panel.js`, `india-boundary.geojson`.

## 4. Key Architectural Rule (From PROJECT_MEMORY.md)
DO NOT train or load a machine learning model to directly predict WBGT. WBGT is a deterministic physical index derived from raw meteorological variables via the Liljegren mass/heat transfer equations. Any ML modeling must focus on predicting health impacts, localized spatial downscaling, or mortality/hospitalization outcomes.

## 5. Most Urgent Gaps Requiring Development
1. No Pune ward-level GIS resolution exists (the map currently displays national-level IDW interpolation over an India outline).
2. Hospitalization risk modeling is completely missing.
3. Demographic vulnerability (elderly, children, outdoor workers, housing conditions) is not factored into the risk score.
4. The mortality exposure-response model is borrowed from Taiwan literature and requires calibration for Indian urban contexts.
5. No automated alerting channels (SMS / WhatsApp) are implemented.
```

---

## Deliverable J: Verification Appendix

### 1. Files Inspected During Audit
Every source file in the repository was inspected line-by-line via read and static analysis tools:
* `/home/parker/sih/DivineDevs/PROJECT_MEMORY.md` (436 lines) — Inspected completely.
* `/home/parker/sih/DivineDevs/weather_api.py` (472 lines) — Inspected completely.
* `/home/parker/sih/DivineDevs/mortality_risk.py` (194 lines) — Inspected completely.
* `/home/parker/sih/DivineDevs/geocoding.py` (100 lines) — Inspected completely.
* `/home/parker/sih/DivineDevs/risk_context_engine.py` (257 lines) — Inspected completely.
* `/home/parker/sih/DivineDevs/recommendation_library.py` (660 lines) — Inspected completely.
* `/home/parker/sih/DivineDevs/recommendation_engine.py` (404 lines) — Inspected completely.
* `/home/parker/sih/DivineDevs/dashboard_server.py` (552 lines) — Inspected completely.
* `/home/parker/sih/DivineDevs/dashboard/index.html` (15 lines) — Inspected completely.
* `/home/parker/sih/DivineDevs/dashboard/app.js` (80 lines) — Inspected completely.
* `/home/parker/sih/DivineDevs/dashboard/health-panel.js` (102 lines) — Inspected completely.
* `/home/parker/sih/DivineDevs/dashboard/styles.css` (1,149 lines) — Key sections inspected.
* `/home/parker/sih/DivineDevs/dashboard/india-boundary.geojson` (91 KB) — Structure and geometry verified.
* `/home/parker/sih/DivineDevs/tests/test_weather_api.py` (107 lines) — Inspected and executed.
* `/home/parker/sih/DivineDevs/tests/test_mortality_risk.py` (135 lines) — Inspected and executed.
* `/home/parker/sih/DivineDevs/tests/test_geocoding.py` (52 lines) — Inspected.
* `/home/parker/sih/DivineDevs/tests/test_heat_risk_api.py` (148 lines) — Inspected.
* `/home/parker/sih/DivineDevs/tests/test_recommendations.py` (270 lines) — Inspected and executed offline suites.

### 2. Git History & Historical Branches Inspected
* `origin/master` (HEAD: commit `1515562` "INFOCARDS")
* `origin/parker` (commit `e62e048` "stuck in the middle", `cf2c337` "mortality rish calculate"): Inspected abandoned `health_impact/service.py` (Choudhary IHI and Agarwal hospitalization).
* Commit `83e2ed4` ("Mortality Index Pipeline") & `5b43166` ("nothing"): Inspected abandoned `mortality_risk/build_mortality_risk.py` (Census PCA town/state demographic vulnerability pipeline).

### 3. Safe Runtime Test Execution Results
All offline, network-independent test suites were safely executed in the local sandbox:
1. `tests/test_mortality_risk.py`:
   * **Result:** `Ran 8 tests in 0.001s -- OK`
   * **Verified:** Baseline $RR=1.00$ at $30^\circ\text{C}$; candidate threshold $RR=1.09$ at $33^\circ\text{C}$; piecewise continuity at $28^\circ\text{C}, 30^\circ\text{C}, 33^\circ\text{C}$; attributable fraction formula.
2. `tests/test_weather_api.py`:
   * **Result:** `Ran 6 tests in 0.001s -- OK`
   * **Verified:** Liljegren outdoor WBGT convergence against published PyWBGT fixtures ($27.22^\circ\text{C}$ mild case and $33.58^\circ\text{C}$ hot case within $0.04^\circ\text{C}$ tolerance); hourly contract aggregation; daily maximum extraction.
3. `tests/test_recommendations.py` (Offline Suites):
   * **Result:** `Ran 12 tests in 0.001s -- OK`
   * **Verified:** Library audience completeness; authoritative source tags (`WHO`, `NIOSH`, `OSHA`); forecast trend detection math; multi-day persistence count; deterministic prioritization; AI validator filtering of forbidden medical terms.
4. **Online Tests Not Executed at Runtime:**
   * `test_geocoding.py`, `test_heat_risk_api.py`, and the integration classes of `test_recommendations.py` were statically verified. They require outbound network connectivity to `geocoding-api.open-meteo.com` and `api.open-meteo.com`. In accordance with sandbox safety rules, they were analyzed statically rather than executed against live external endpoints.
