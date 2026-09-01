"""Authoritative Heat-Health Evidence Recommendation Library.

Grounding References:
---------------------
1. WHO (World Health Organization):
   - Heat and Health Guidance: Public Heat Protection & Heat-Health Action Plans (HHAP).
   - Guidance on warning systems, cooling measures, vulnerable populations, and healthcare preparedness.
2. NIOSH / CDC (National Institute for Occupational Safety and Health):
   - Criteria for a Recommended Standard: Occupational Exposure to Heat and Hot Environments.
   - Work-rest regimens, hydration rates, acclimatization schedules, and physiological monitoring.
3. OSHA (Occupational Safety and Health Administration):
   - Heat Illness Prevention Standards: Water, Rest, Shade guidelines, work scheduling, and emergency action.

Target Audiences:
-----------------
- PUBLIC
- OUTDOOR_WORKER
- AUTHORITY
"""

from typing import Any, Dict, List

AUDIENCES = ["PUBLIC", "OUTDOOR_WORKER", "AUTHORITY"]

SEVERITY_LEVELS = ["LOW", "MODERATE", "HIGH", "VERY_HIGH", "EXTREME"]

# Structured Evidence Library
RECOMMENDATION_LIBRARY: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # PUBLIC RECOMMENDATIONS (WHO Guidance)
    # -------------------------------------------------------------------------
    # Tier 1: LOW (WBGT < 27.8°C)
    {
        "id": "who_pub_routine_low",
        "audience": "PUBLIC",
        "severity_levels": ["LOW"],
        "category": "OUTDOOR_ACTIVITY",
        "action": "Conditions are within normal comfort range. Enjoy outdoor activities with standard sun protection and lightweight clothing.",
        "source": "WHO",
        "source_reference": "WHO General Warm Weather Advisory & Physical Activity Guidance",
        "priority_base": 1,
    },
    {
        "id": "who_pub_hydration_low",
        "audience": "PUBLIC",
        "severity_levels": ["LOW"],
        "category": "HYDRATION",
        "action": "Maintain baseline daily hydration of 2.0 to 2.5 liters of water. Carry a water bottle when commuting or exercising outdoors.",
        "source": "WHO",
        "source_reference": "WHO Public Heat and Health Information Guide: Baseline Hydration",
        "priority_base": 2,
    },
    {
        "id": "who_pub_monitoring_low",
        "audience": "PUBLIC",
        "severity_levels": ["LOW"],
        "category": "FORECAST_MONITORING",
        "action": "Stay informed on upcoming 5-day heatwave forecasts for any sudden temperature or humidity rises.",
        "source": "WHO",
        "source_reference": "WHO Heat Early Warning Systems: Public Meteorological Awareness",
        "priority_base": 3,
    },
    {
        "id": "who_pub_sun_low",
        "audience": "PUBLIC",
        "severity_levels": ["LOW"],
        "category": "SUN_PROTECTION",
        "action": "Apply SPF 30+ sunscreen and wear UV-rated sunglasses during peak midday sunshine hours.",
        "source": "WHO",
        "source_reference": "WHO Public Health Advice: Solar Radiation and Skin Protection",
        "priority_base": 3,
    },

    # Tier 2: MODERATE (WBGT 27.8°C - 29.4°C)
    {
        "id": "who_pub_rest_mod",
        "audience": "PUBLIC",
        "severity_levels": ["MODERATE"],
        "category": "REST_RECOVERY",
        "action": "Take regular 10 to 15 minute rest intervals in shaded or ventilated areas during sustained outdoor physical exertion.",
        "source": "WHO",
        "source_reference": "WHO Guidance on Physical Exertion During Moderate Heat",
        "priority_base": 1,
    },
    {
        "id": "who_pub_hydration_mod",
        "audience": "PUBLIC",
        "severity_levels": ["MODERATE"],
        "category": "HYDRATION",
        "action": "Drink 350 to 500 ml of water per hour during active daytime hours; consume electrolyte fluids like lemon water or coconut water.",
        "source": "WHO",
        "source_reference": "WHO Hydration & Mineral Balance Guidance for Warm Climates",
        "priority_base": 1,
    },
    {
        "id": "who_pub_cooling_mod",
        "audience": "PUBLIC",
        "severity_levels": ["MODERATE"],
        "category": "COOLING",
        "action": "Keep living spaces ventilated; use electric fans, open cross-breezes in morning/evening, and close sunny window blinds.",
        "source": "WHO",
        "source_reference": "WHO Heat-Health Guidance: Domestic Cooling Interventions",
        "priority_base": 2,
    },
    {
        "id": "who_pub_vulnerable_mod",
        "audience": "PUBLIC",
        "severity_levels": ["MODERATE"],
        "category": "VULNERABLE_PERSON_CHECK",
        "action": "Check on elderly family members, infants, and individuals with chronic respiratory or cardiovascular conditions.",
        "source": "WHO",
        "source_reference": "WHO Heat-Health Action Plans: Protecting Vulnerable Populations",
        "priority_base": 2,
    },

    # Tier 3: HIGH (WBGT 29.5°C - 31.0°C)
    {
        "id": "who_pub_exposure_high",
        "audience": "PUBLIC",
        "severity_levels": ["HIGH"],
        "category": "EXPOSURE_REDUCTION",
        "action": "Stay indoors during peak solar hours (11:00 AM to 3:30 PM); reschedule strenuous workouts and sports to early morning or late evening.",
        "source": "WHO",
        "source_reference": "WHO Public Heat Protection Guidelines: Sun & Peak Heat Avoidance",
        "priority_base": 1,
    },
    {
        "id": "who_pub_hydration_high",
        "audience": "PUBLIC",
        "severity_levels": ["HIGH"],
        "category": "HYDRATION",
        "action": "Increase fluid intake to 500 to 750 ml/hr with oral rehydration salts (ORS) or electrolyte fluids; avoid alcohol and sugary caffeinated drinks.",
        "source": "WHO",
        "source_reference": "WHO Public Heatwave Hydration & Electrolyte Protocol",
        "priority_base": 1,
    },
    {
        "id": "who_pub_workrest_high",
        "audience": "PUBLIC",
        "severity_levels": ["HIGH"],
        "category": "REST_RECOVERY",
        "action": "Implement a 45 min activity / 15 min shaded rest schedule for all outdoor and manual chores.",
        "source": "WHO",
        "source_reference": "WHO Occupational & Physical Heat Regimens in High Thermal Stress",
        "priority_base": 2,
    },
    {
        "id": "who_pub_awareness_high",
        "audience": "PUBLIC",
        "severity_levels": ["HIGH"],
        "category": "HEAT_ILLNESS_AWARENESS",
        "action": "Watch for early symptoms of heat exhaustion (dizziness, nausea, rapid pulse, heavy sweating); rest in cool shade immediately.",
        "source": "WHO",
        "source_reference": "WHO Clinical Heat Illness Recognition Protocol",
        "priority_base": 2,
    },

    # Tier 4: VERY HIGH (WBGT 31.1°C - 32.1°C)
    {
        "id": "who_pub_exposure_very_high",
        "audience": "PUBLIC",
        "severity_levels": ["VERY_HIGH"],
        "category": "EXPOSURE_REDUCTION",
        "action": "Dangerous thermal strain: Limit continuous outdoor exposure to under 30 minutes. Stay in air-conditioned or well-cooled indoor environments.",
        "source": "WHO",
        "source_reference": "WHO Extreme Heat Advisory on Ambient Exposure Reduction",
        "priority_base": 1,
    },
    {
        "id": "who_pub_workrest_very_high",
        "audience": "PUBLIC",
        "severity_levels": ["VERY_HIGH"],
        "category": "REST_RECOVERY",
        "action": "Enforce a 30 min activity / 30 min shaded rest cycle. Curtail all non-essential heavy physical exertion.",
        "source": "WHO",
        "source_reference": "WHO Heat-Health Work-Rest Guidelines for Very High Heat Stress",
        "priority_base": 1,
    },
    {
        "id": "who_pub_hydration_very_high",
        "audience": "PUBLIC",
        "severity_levels": ["VERY_HIGH"],
        "category": "HYDRATION",
        "action": "Drink 750 to 1000 ml of chilled electrolyte fluids hourly; apply cold damp cloths to neck and forehead for active thermal relief.",
        "source": "WHO",
        "source_reference": "WHO Active Cooling & Severe Heat Hydration Standard",
        "priority_base": 1,
    },
    {
        "id": "who_pub_vulnerable_very_high",
        "audience": "PUBLIC",
        "severity_levels": ["VERY_HIGH"],
        "category": "VULNERABLE_PERSON_CHECK",
        "action": "Actively check high-risk individuals (older adults living alone, infants, patients on medication) at least twice daily.",
        "source": "WHO",
        "source_reference": "WHO Vulnerable Population Surveillance in Severe Heatwaves",
        "priority_base": 2,
    },

    # Tier 5: EXTREME (WBGT >= 32.2°C)
    {
        "id": "who_pub_emergency_extreme",
        "audience": "PUBLIC",
        "severity_levels": ["EXTREME"],
        "category": "EXPOSURE_REDUCTION",
        "action": "CRITICAL HEAT HAZARD: Suspend all outdoor physical labor and recreational sports immediately. Remain in air-cooled shelters.",
        "source": "WHO",
        "source_reference": "WHO Extreme Heat Emergency Protective Action Plan",
        "priority_base": 1,
    },
    {
        "id": "who_pub_heatstroke_extreme",
        "audience": "PUBLIC",
        "severity_levels": ["EXTREME"],
        "category": "HEAT_ILLNESS_AWARENESS",
        "action": "Life-threatening heatstroke risk. Treat hot/dry skin, confusion, vomiting, or fainting as a medical emergency — call EMS immediately and immerse or sponge with cold water.",
        "source": "WHO",
        "source_reference": "WHO Emergency Heatstroke Recognition and First-Aid Protocol",
        "priority_base": 1,
    },
    {
        "id": "who_pub_hydration_extreme",
        "audience": "PUBLIC",
        "severity_levels": ["EXTREME"],
        "category": "HYDRATION",
        "action": "Sip chilled electrolyte fluids continuously (up to 1 liter/hr); avoid plain water intoxication by ensuring mineral and salt replenishment.",
        "source": "WHO",
        "source_reference": "WHO Emergency Hydration & Electrolyte Management in Extreme Heat",
        "priority_base": 1,
    },
    {
        "id": "who_pub_community_extreme",
        "audience": "PUBLIC",
        "severity_levels": ["EXTREME"],
        "category": "COOLING",
        "action": "Access air-conditioned public cooling centers, misting shelters, or designated emergency community cooling sites.",
        "source": "WHO",
        "source_reference": "WHO Community Cooling & Emergency Heat Relief Centers",
        "priority_base": 2,
    },

    # -------------------------------------------------------------------------
    # OUTDOOR WORKER RECOMMENDATIONS (NIOSH / OSHA Guidance)
    # -------------------------------------------------------------------------
    # Tier 1: LOW
    {
        "id": "osha_wrk_routine_low",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["LOW"],
        "category": "HYDRATION",
        "action": "Maintain baseline worker hydration (1 cup every 30 to 45 minutes) and ensure supervisor training on heat recognition.",
        "source": "OSHA",
        "source_reference": "OSHA Baseline Worker Heat Readiness & Educational Standards",
        "priority_base": 1,
    },
    {
        "id": "osha_wrk_ppe_low",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["LOW"],
        "category": "PROTECTIVE_EQUIPMENT",
        "action": "Wear breathable, light-colored long-sleeve clothing and wide-brim UV neck protection.",
        "source": "OSHA",
        "source_reference": "OSHA Personal Protective Equipment Guidance for Warm Weather",
        "priority_base": 2,
    },
    {
        "id": "osha_wrk_monitoring_low",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["LOW"],
        "category": "HEAT_ILLNESS_MONITORING",
        "action": "Review heat illness emergency procedures and establish designated shaded rest zones on worksites.",
        "source": "OSHA",
        "source_reference": "OSHA Heat Safety Protocol: Worksite Preparation Standards",
        "priority_base": 3,
    },

    # Tier 2: MODERATE
    {
        "id": "osha_wrk_hydration_mod",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["MODERATE"],
        "category": "HYDRATION",
        "action": "Drink at least 1 cup (250 ml) of water every 20 minutes; provide accessible cool drinking water stations at all worksites.",
        "source": "OSHA",
        "source_reference": "OSHA Heat Safety Campaign: Water. Rest. Shade. Hydration Standard",
        "priority_base": 1,
    },
    {
        "id": "osha_wrk_shade_mod",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["MODERATE"],
        "category": "SHADE_COOLING",
        "action": "Provide accessible shaded or ventilated rest areas near worksites for periodic thermal recovery.",
        "source": "OSHA",
        "source_reference": "OSHA Technical Manual: Heat Stress Shaded Rest Facilities",
        "priority_base": 2,
    },
    {
        "id": "niosh_wrk_acclimatization_mod",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["MODERATE"],
        "category": "ACCLIMATIZATION",
        "action": "Gradually acclimatize new and returning workers over 7 to 14 days by progressively increasing daily heat exposure duration.",
        "source": "NIOSH",
        "source_reference": "NIOSH Acclimatization Guidelines for Occupational Heat Stress",
        "priority_base": 2,
    },
    {
        "id": "niosh_wrk_workrest_mod",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["MODERATE"],
        "category": "REST_RECOVERY",
        "action": "Implement 50 min work / 10 min shaded rest intervals during moderate physical tasks.",
        "source": "NIOSH",
        "source_reference": "NIOSH Criteria for a Recommended Standard: Occupational Heat Exposure",
        "priority_base": 2,
    },

    # Tier 3: HIGH
    {
        "id": "niosh_wrk_workrest_high",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["HIGH"],
        "category": "REST_RECOVERY",
        "action": "Implement mandatory work-rest cycles: 45 min work / 15 min shaded rest per hour; adjust to 30/30 as exertion increases.",
        "source": "NIOSH",
        "source_reference": "NIOSH Criteria for a Recommended Standard: Occupational Heat Exposure Work/Rest Schedules",
        "priority_base": 1,
    },
    {
        "id": "niosh_wrk_scheduling_high",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["HIGH"],
        "category": "WORK_SCHEDULING",
        "action": "Shift physically demanding tasks to cooler morning hours (before 11:00 AM) and avoid continuous midday outdoor labor.",
        "source": "NIOSH",
        "source_reference": "NIOSH Heat Stress Hazard Prevention: Work Scheduling Modifications",
        "priority_base": 1,
    },
    {
        "id": "osha_wrk_hydration_high",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["HIGH"],
        "category": "HYDRATION",
        "action": "Provide cold drinking water and electrolyte solutions; enforce minimum intake of 500 to 750 ml/hr per worker.",
        "source": "OSHA",
        "source_reference": "OSHA Worksite Electrolyte & Fluid Replacement Guidelines",
        "priority_base": 1,
    },
    {
        "id": "osha_wrk_monitoring_high",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["HIGH"],
        "category": "HEAT_ILLNESS_MONITORING",
        "action": "Implement a mandatory buddy system to monitor co-workers for signs of heat illness (slurred speech, stumbling, excessive fatigue, confusion).",
        "source": "OSHA",
        "source_reference": "OSHA Heat Illness Prevention: Buddy System & Peer Physiological Monitoring",
        "priority_base": 2,
    },

    # Tier 4: VERY HIGH
    {
        "id": "niosh_wrk_workrest_very_high",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["VERY_HIGH"],
        "category": "REST_RECOVERY",
        "action": "Enforce strict 30 min work / 30 min shaded rest cycle (or 15 min work / 45 min rest for heavy physical labor).",
        "source": "NIOSH",
        "source_reference": "NIOSH Occupational Exposure to Heat: Work-Rest Regimens",
        "priority_base": 1,
    },
    {
        "id": "niosh_wrk_workload_very_high",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["VERY_HIGH"],
        "category": "WORKLOAD_REDUCTION",
        "action": "Curtail non-essential heavy physical labor, use mechanical equipment where feasible, and enforce mandatory rest intervals.",
        "source": "NIOSH",
        "source_reference": "NIOSH Occupational Heat Exposure: Administrative Controls on Heavy Labor",
        "priority_base": 1,
    },
    {
        "id": "niosh_wrk_scheduling_very_high",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["VERY_HIGH"],
        "category": "WORK_SCHEDULING",
        "action": "Split work shifts to early morning (5:00 AM to 9:30 AM) and evening (after 5:00 PM); halt open-sun roof and asphalt operations during midday.",
        "source": "NIOSH",
        "source_reference": "NIOSH Work Schedule Adjustments for Dangerous Heat",
        "priority_base": 1,
    },
    {
        "id": "osha_wrk_hydration_very_high",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["VERY_HIGH"],
        "category": "HYDRATION",
        "action": "Mandate 1 cup of cold electrolyte fluid every 15 minutes; stage ice vests and active cooling stations near workstations.",
        "source": "OSHA",
        "source_reference": "OSHA Severe Heat Stress Intervention Protocol",
        "priority_base": 1,
    },

    # Tier 5: EXTREME
    {
        "id": "osha_wrk_stoppage_extreme",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["EXTREME"],
        "category": "WORKLOAD_REDUCTION",
        "action": "MANDATORY WORK SUSPENSION: Stop all outdoor construction, agriculture, and heavy manual labor. Move workers to air-conditioned facilities.",
        "source": "OSHA",
        "source_reference": "OSHA Emergency Heat Hazard Work Suspension Protocol",
        "priority_base": 1,
    },
    {
        "id": "niosh_wrk_rest_extreme",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["EXTREME"],
        "category": "REST_RECOVERY",
        "action": "Critical physiological thermal threshold exceeded. If emergency work is required, restrict to 15 min work / 45 min rest in active air conditioning.",
        "source": "NIOSH",
        "source_reference": "NIOSH Extreme Heat Protective Standard: Maximum Rest Regimen",
        "priority_base": 1,
    },
    {
        "id": "osha_wrk_hydration_extreme",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["EXTREME"],
        "category": "HYDRATION",
        "action": "Enforce continuous chilled electrolyte hydration; mandatory physiological check before any brief emergency outdoor entry.",
        "source": "OSHA",
        "source_reference": "OSHA Emergency Response Heat Standard: Worker Hydration",
        "priority_base": 1,
    },
    {
        "id": "niosh_wrk_scheduling_extreme",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["EXTREME"],
        "category": "WORK_SCHEDULING",
        "action": "Prohibit all lone worker tasks; dedicated safety supervisors must maintain continuous line-of-sight physiological monitoring.",
        "source": "NIOSH",
        "source_reference": "NIOSH Extreme Hazard Supervision & Worksite Protection Standard",
        "priority_base": 1,
    },

    # -------------------------------------------------------------------------
    # AUTHORITY RECOMMENDATIONS (WHO Heat-Health Action Plans)
    # -------------------------------------------------------------------------
    # Tier 1: LOW
    {
        "id": "who_auth_routine_low",
        "audience": "AUTHORITY",
        "severity_levels": ["LOW"],
        "category": "HEAT_ACTION_PLAN",
        "action": "Maintain seasonal surveillance of meteorological indicators, review heat action protocols, and test emergency communication channels.",
        "source": "WHO",
        "source_reference": "WHO Heat-Health Action Plans: Pre-Season Readiness Protocols",
        "priority_base": 1,
    },
    {
        "id": "who_auth_infra_low",
        "audience": "AUTHORITY",
        "severity_levels": ["LOW"],
        "category": "RESOURCE_PREPARATION",
        "action": "Inspect public water supply distribution and maintain municipal green space shading infrastructure.",
        "source": "WHO",
        "source_reference": "WHO Municipal Heat Resilience Guidelines: Urban Infrastructure",
        "priority_base": 2,
    },
    {
        "id": "who_auth_training_low",
        "audience": "AUTHORITY",
        "severity_levels": ["LOW"],
        "category": "PUBLIC_ALERT",
        "action": "Conduct public awareness campaigns on summer heat safety and vulnerable population care.",
        "source": "WHO",
        "source_reference": "WHO Pre-Season Heat Awareness Guide for Municipalities",
        "priority_base": 3,
    },

    # Tier 2: MODERATE
    {
        "id": "who_auth_outreach_mod",
        "audience": "AUTHORITY",
        "severity_levels": ["MODERATE"],
        "category": "VULNERABLE_POPULATION_OUTREACH",
        "action": "Mobilize social workers, healthcare workers, and community volunteers to actively check on homeless, elderly, and vulnerable residents.",
        "source": "WHO",
        "source_reference": "WHO Public Health Interventions: Active Community Outreach in Heatwaves",
        "priority_base": 1,
    },
    {
        "id": "who_auth_water_mod",
        "audience": "AUTHORITY",
        "severity_levels": ["MODERATE"],
        "category": "RESOURCE_PREPARATION",
        "action": "Set up municipal drinking water stations (pyau) in busy transit hubs, markets, and bus terminals.",
        "source": "WHO",
        "source_reference": "WHO Heat-Health Action Plans: Urban Water Access Stations",
        "priority_base": 2,
    },
    {
        "id": "who_auth_advisory_mod",
        "audience": "AUTHORITY",
        "severity_levels": ["MODERATE"],
        "category": "PUBLIC_ALERT",
        "action": "Issue general heat-health advisories via local radio, social media, and digital transit displays.",
        "source": "WHO",
        "source_reference": "WHO Early Warning & Public Advisory Dissemination Standards",
        "priority_base": 2,
    },

    # Tier 3: HIGH
    {
        "id": "who_auth_alert_high",
        "audience": "AUTHORITY",
        "severity_levels": ["HIGH"],
        "category": "PUBLIC_ALERT",
        "action": "Issue multi-channel public heat-health alerts and public advisories via media, mobile alerts, and community networks.",
        "source": "WHO",
        "source_reference": "WHO Heat-Health Action Plans (HHAP): Early Warning & Public Advisory Dissemination",
        "priority_base": 1,
    },
    {
        "id": "who_auth_coolingcenters_high",
        "audience": "AUTHORITY",
        "severity_levels": ["HIGH"],
        "category": "COOLING_CENTERS",
        "action": "Open and publicize air-conditioned public cooling centers, misting stations, and shaded rest shelters with free drinking water.",
        "source": "WHO",
        "source_reference": "WHO Heat-Health Action Plans: Establishing Community Cooling Shelters",
        "priority_base": 1,
    },
    {
        "id": "who_auth_healthcare_high",
        "audience": "AUTHORITY",
        "severity_levels": ["HIGH"],
        "category": "HEALTHCARE_PREPAREDNESS",
        "action": "Alert emergency departments, EMS, and clinics to prepare for surges in heat-related emergency visits and acute admissions.",
        "source": "WHO",
        "source_reference": "WHO Guidelines on Health System Surge Capacity for Extreme Weather Events",
        "priority_base": 1,
    },
    {
        "id": "who_auth_resources_high",
        "audience": "AUTHORITY",
        "severity_levels": ["HIGH"],
        "category": "RESOURCE_PREPARATION",
        "action": "Ensure uninterrupted electrical grid reliability, protect water supply lines, and stage additional emergency response units in high-density urban areas.",
        "source": "WHO",
        "source_reference": "WHO Heat Action Planning: Critical Infrastructure & Municipal Resilience",
        "priority_base": 2,
    },

    # Tier 4: VERY HIGH
    {
        "id": "who_auth_alert_very_high",
        "audience": "AUTHORITY",
        "severity_levels": ["VERY_HIGH"],
        "category": "PUBLIC_ALERT",
        "action": "Issue Orange-tier Extreme Heat Warning: activate broadcast SMS push notifications and sound city advisory alerts.",
        "source": "WHO",
        "source_reference": "WHO Severe Heatwave Public Warning Protocol",
        "priority_base": 1,
    },
    {
        "id": "who_auth_workaction_very_high",
        "audience": "AUTHORITY",
        "severity_levels": ["VERY_HIGH"],
        "category": "OUTDOOR_WORK_ACTION",
        "action": "Enact municipal guidelines or advisories restricting non-essential outdoor public works and construction during peak thermal hours.",
        "source": "WHO",
        "source_reference": "WHO Heat-Health Guidance: Occupational and Municipal Labor Protective Measures",
        "priority_base": 1,
    },
    {
        "id": "who_auth_healthcare_very_high",
        "audience": "AUTHORITY",
        "severity_levels": ["VERY_HIGH"],
        "category": "HEALTHCARE_PREPAREDNESS",
        "action": "Deploy mobile health vans and emergency medical response teams equipped with IV fluids and ice packs to high-risk slums and construction clusters.",
        "source": "WHO",
        "source_reference": "WHO Mobile Medical Response in Severe Heatwaves",
        "priority_base": 1,
    },
    {
        "id": "who_auth_coolingcenters_very_high",
        "audience": "AUTHORITY",
        "severity_levels": ["VERY_HIGH"],
        "category": "COOLING_CENTERS",
        "action": "Extend cooling center operating hours to 24/7; distribute oral rehydration salts (ORS) across all public transit nodes.",
        "source": "WHO",
        "source_reference": "WHO Emergency Cooling Shelter Management",
        "priority_base": 2,
    },

    # Tier 5: EXTREME
    {
        "id": "who_auth_red_alert_extreme",
        "audience": "AUTHORITY",
        "severity_levels": ["EXTREME"],
        "category": "PUBLIC_ALERT",
        "action": "ISSUE RED HEAT EMERGENCY: Activate highest-level disaster management protocols across municipal, health, and labor departments.",
        "source": "WHO",
        "source_reference": "WHO Disaster Risk Management Heatwave Protocol",
        "priority_base": 1,
    },
    {
        "id": "who_auth_work_ban_extreme",
        "audience": "AUTHORITY",
        "severity_levels": ["EXTREME"],
        "category": "OUTDOOR_WORK_ACTION",
        "action": "Mandate total cessation of all open-air labor, construction, and outdoor school activities between 10:30 AM and 4:30 PM.",
        "source": "WHO",
        "source_reference": "WHO Municipal Emergency Labor Protection Orders",
        "priority_base": 1,
    },
    {
        "id": "who_auth_hospital_extreme",
        "audience": "AUTHORITY",
        "severity_levels": ["EXTREME"],
        "category": "HEALTHCARE_PREPAREDNESS",
        "action": "Activate hospital emergency surge capacity; establish dedicated heatstroke treatment units with rapid immersion cooling baths.",
        "source": "WHO",
        "source_reference": "WHO Mass-Casualty Heatwave Clinical Management Standard",
        "priority_base": 1,
    },
    {
        "id": "who_auth_resilience_extreme",
        "audience": "AUTHORITY",
        "severity_levels": ["EXTREME"],
        "category": "RESOURCE_PREPARATION",
        "action": "Prioritize emergency power routing to hospitals and water treatment plants; deploy water tankers to underserved heat-vulnerable zones.",
        "source": "WHO",
        "source_reference": "WHO Critical Municipal Life-Support Preservation in Extreme Heatwaves",
        "priority_base": 1,
    },
]


def get_library_recommendations(audience: str, severity: str) -> List[Dict[str, Any]]:
    """Retrieve all evidence-grounded recommendations matching target audience and severity level.

    Args:
        audience: 'PUBLIC', 'OUTDOOR_WORKER', or 'AUTHORITY' (case-insensitive).
        severity: 'LOW', 'MODERATE', 'HIGH', 'VERY_HIGH', or 'EXTREME' (case-insensitive).

    Returns:
        List of matching recommendation dictionaries.
    """
    aud_norm = audience.strip().upper()
    sev_norm = severity.strip().upper()

    results = []
    for item in RECOMMENDATION_LIBRARY:
        if item["audience"] == aud_norm and sev_norm in item["severity_levels"]:
            results.append(dict(item))

    return results


