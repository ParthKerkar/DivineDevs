# Health-impact layer

The dashboard preserves the existing Open-Meteo → Liljegren WBGT pipeline. A separate downstream path calculates hourly India Heat Index (IHI):

`IHI = 0.820 × Ta + 0.123 × RH + 0.004 × SR − 0.117 × WS − 6.727`

It aggregates hourly IHI to daily maximum and mean values, then assigns a published Choudhary et al. comfort class from daily maximum IHI. Coordinates are assigned through a locally packaged GIS polygon layer (`health_impact/data/india_climate_zones.geojson`), not a city lookup. The packaged layer is deliberately identified as a coarse prototype configuration and must be replaced with a validated machine-readable rendition of the study's climate map before operational deployment. An unmatched point is rejected; no zone is guessed.

Mortality uses published all-age, all-cause *sweltering vs comfortable* comparisons from Choudhary RK et al. (2024), “Excess Mortality Risk Due to Heat Stress in Different Climatic Zones of India”, *Environmental Science & Technology*, DOI `10.1021/acs.est.3c05218`: Delhi/Semiarid RR 1.059, Varanasi/Humid subtropical RR 1.081, and Chennai/Tropical wet and dry RR 1.080. The mortality risk index is `100 × RR`. Non-sweltering categories remain at the reference display baseline of 100 because no category-specific RR is applied. This is not zero mortality risk.

Only those three study zones have direct mortality evidence. Arid and tropical-wet assignments use an explicit proxy configuration and are returned with `coverage: "extrapolated"`, `is_extrapolated: true`, and their representative city/zone. Mountainous IHI classes are `unsupported`: no threshold is fabricated. The response includes the paper's city-specific delayed-effect window (Delhi 3 days, Varanasi 4, Chennai 6) but does not manufacture individual lag-day risks or compound daily RRs.

Hospitalization uses Agarwal AK, Dwivedi S, Ahirwar G. (2018), “Summer Heat: Making a Consistent Health Impact”, *Indian Journal of Occupational and Environmental Medicine*, DOI `10.4103/IJOEM_IJOEM_94_17`. For daily Tmax ≥40°C, it applies the published Gwalior tertiary-hospital comparison RR 1.186 and stress index 118.6; below 40°C it displays the reference baseline of 100 without inventing a 38–40°C exposure-response relationship.

We use published epidemiological relative-risk estimates rather than fitting a new mortality model. We use a published Indian hospitalization effect estimate as an evidence-based stress multiplier rather than fitting a new hospitalization model. The prototype does not predict an absolute number of deaths or hospital admissions. The indices are epidemiological decision-support indicators. Local mortality/hospitalization surveillance would be required to calibrate and validate a city/district-specific model.
