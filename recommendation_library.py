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
    {
        "id": "who_pub_hydration_01",
        "audience": "PUBLIC",
        "severity_levels": ["LOW", "MODERATE", "HIGH", "VERY_HIGH", "EXTREME"],
        "category": "HYDRATION",
        "action": "Drink plenty of water regularly throughout the day, avoiding alcohol and excessively sugary or caffeinated drinks.",
        "source": "WHO",
        "source_reference": "WHO Heat and Health Information Guide (Public Hydration Guidelines)",
        "priority_base": 1,
    },
    {
        "id": "who_pub_exposure_01",
        "audience": "PUBLIC",
        "severity_levels": ["HIGH", "VERY_HIGH", "EXTREME"],
        "category": "EXPOSURE_REDUCTION",
        "action": "Stay indoors during the hottest hours of the day (typically 11:00 AM to 4:00 PM) and avoid direct sun exposure.",
        "source": "WHO",
        "source_reference": "WHO Public Heat Protection Guidelines: Sun & Peak Heat Avoidance",
        "priority_base": 1,
    },
    {
        "id": "who_pub_cooling_01",
        "audience": "PUBLIC",
        "severity_levels": ["MODERATE", "HIGH", "VERY_HIGH", "EXTREME"],
        "category": "COOLING",
        "action": "Keep your living space cool; use fans, damp cloths, cool showers, and close shutters/curtains during peak sunshine.",
        "source": "WHO",
        "source_reference": "WHO Heat-Health Guidance: Domestic Cooling Interventions",
        "priority_base": 2,
    },
    {
        "id": "who_pub_activity_01",
        "audience": "PUBLIC",
        "severity_levels": ["HIGH", "VERY_HIGH", "EXTREME"],
        "category": "PHYSICAL_ACTIVITY",
        "action": "Reschedule strenuous physical activities, sports, and outdoor workouts to early morning or late evening.",
        "source": "WHO",
        "source_reference": "WHO Guidance on Physical Exertion During Extreme Heat",
        "priority_base": 2,
    },
    {
        "id": "who_pub_vulnerable_01",
        "audience": "PUBLIC",
        "severity_levels": ["MODERATE", "HIGH", "VERY_HIGH", "EXTREME"],
        "category": "VULNERABLE_PERSON_CHECK",
        "action": "Check frequently on high-risk individuals including infants, pregnant women, older adults, and people living alone or with chronic conditions.",
        "source": "WHO",
        "source_reference": "WHO Heat-Health Action Plans: Protecting Vulnerable Populations",
        "priority_base": 1,
    },
    {
        "id": "who_pub_awareness_01",
        "audience": "PUBLIC",
        "severity_levels": ["HIGH", "VERY_HIGH", "EXTREME"],
        "category": "HEAT_ILLNESS_AWARENESS",
        "action": "Watch for early symptoms of heat exhaustion (dizziness, nausea, rapid pulse, heavy sweating); seek immediate medical attention if confusion or fainting occurs.",
        "source": "WHO",
        "source_reference": "WHO Clinical Heat Illness Recognition Protocol",
        "priority_base": 1,
    },
    {
        "id": "who_pub_routine_01",
        "audience": "PUBLIC",
        "severity_levels": ["LOW"],
        "category": "EXPOSURE_REDUCTION",
        "action": "Maintain routine sun protection, wear lightweight loose-fitting clothing, and stay informed on weather forecasts.",
        "source": "WHO",
        "source_reference": "WHO General Warm Weather Advisory",
        "priority_base": 3,
    },

    # -------------------------------------------------------------------------
    # OUTDOOR WORKER RECOMMENDATIONS (NIOSH / OSHA Guidance)
    # -------------------------------------------------------------------------
    {
        "id": "osha_wrk_hydration_01",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["MODERATE", "HIGH", "VERY_HIGH", "EXTREME"],
        "category": "HYDRATION",
        "action": "Drink at least 1 cup (250 ml) of water every 15 to 20 minutes; do not wait until feeling thirsty.",
        "source": "OSHA",
        "source_reference": "OSHA Heat Safety Campaign: Water. Rest. Shade. Hydration Standard",
        "priority_base": 1,
    },
    {
        "id": "niosh_wrk_workrest_01",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["HIGH", "VERY_HIGH", "EXTREME"],
        "category": "REST_RECOVERY",
        "action": "Implement structured work-rest cycles (e.g. 45 min work / 15 min rest, adjusting to 30/30 or 15/45 as thermal stress increases).",
        "source": "NIOSH",
        "source_reference": "NIOSH Criteria for a Recommended Standard: Occupational Heat Exposure Work/Rest Schedules",
        "priority_base": 1,
    },
    {
        "id": "osha_wrk_shade_01",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["MODERATE", "HIGH", "VERY_HIGH", "EXTREME"],
        "category": "SHADE_COOLING",
        "action": "Provide accessible shaded or air-conditioned rest areas near worksites for periodic thermal recovery.",
        "source": "OSHA",
        "source_reference": "OSHA Technical Manual: Heat Stress Shaded Rest Facilities",
        "priority_base": 2,
    },
    {
        "id": "niosh_wrk_scheduling_01",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["HIGH", "VERY_HIGH", "EXTREME"],
        "category": "WORK_SCHEDULING",
        "action": "Shift physically demanding tasks to cooler hours (early morning or night shift) and avoid continuous midday outdoor labor.",
        "source": "NIOSH",
        "source_reference": "NIOSH Heat Stress Hazard Prevention: Work Scheduling Modifications",
        "priority_base": 1,
    },
    {
        "id": "niosh_wrk_workload_01",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["VERY_HIGH", "EXTREME"],
        "category": "WORKLOAD_REDUCTION",
        "action": "Curtail non-essential heavy physical labor, use mechanical equipment where feasible, and enforce mandatory rest intervals.",
        "source": "NIOSH",
        "source_reference": "NIOSH Occupational Heat Exposure: Administrative Controls on Heavy Labor",
        "priority_base": 1,
    },
    {
        "id": "niosh_wrk_acclimatization_01",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["MODERATE", "HIGH", "VERY_HIGH", "EXTREME"],
        "category": "ACCLIMATIZATION",
        "action": "Gradually acclimatize new and returning workers over 7 to 14 days by progressively increasing daily heat exposure duration.",
        "source": "NIOSH",
        "source_reference": "NIOSH Acclimatization Guidelines for Occupational Heat Stress",
        "priority_base": 2,
    },
    {
        "id": "osha_wrk_monitoring_01",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["HIGH", "VERY_HIGH", "EXTREME"],
        "category": "HEAT_ILLNESS_MONITORING",
        "action": "Implement a mandatory buddy system to monitor co-workers for signs of heat illness (slurred speech, stumbling, excessive fatigue, confusion).",
        "source": "OSHA",
        "source_reference": "OSHA Heat Illness Prevention: Buddy System & Peer Physiological Monitoring",
        "priority_base": 1,
    },
    {
        "id": "osha_wrk_routine_01",
        "audience": "OUTDOOR_WORKER",
        "severity_levels": ["LOW"],
        "category": "HYDRATION",
        "action": "Maintain routine fluid intake, wear breathable protective clothing, and ensure supervisor training on heat symptoms.",
        "source": "OSHA",
        "source_reference": "OSHA Baseline Worker Heat Readiness",
        "priority_base": 3,
    },

    # -------------------------------------------------------------------------
    # AUTHORITY RECOMMENDATIONS (WHO Heat-Health Action Plans)
    # -------------------------------------------------------------------------
    {
        "id": "who_auth_alert_01",
        "audience": "AUTHORITY",
        "severity_levels": ["HIGH", "VERY_HIGH", "EXTREME"],
        "category": "PUBLIC_ALERT",
        "action": "Issue multi-channel public heat-health alerts and public advisories via media, mobile alerts, and community networks.",
        "source": "WHO",
        "source_reference": "WHO Heat-Health Action Plans (HHAP): Early Warning & Public Advisory Dissemination",
        "priority_base": 1,
    },
    {
        "id": "who_auth_coolingcenters_01",
        "audience": "AUTHORITY",
        "severity_levels": ["HIGH", "VERY_HIGH", "EXTREME"],
        "category": "COOLING_CENTERS",
        "action": "Open and publicize air-conditioned public cooling centers, misting stations, and shaded rest shelters with free drinking water.",
        "source": "WHO",
        "source_reference": "WHO Heat-Health Action Plans: Establishing Community Cooling Shelters",
        "priority_base": 1,
    },
    {
        "id": "who_auth_healthcare_01",
        "audience": "AUTHORITY",
        "severity_levels": ["HIGH", "VERY_HIGH", "EXTREME"],
        "category": "HEALTHCARE_PREPAREDNESS",
        "action": "Alert emergency departments, EMS, and clinics to prepare for surges in heat-related emergency visits and acute admissions.",
        "source": "WHO",
        "source_reference": "WHO Guidelines on Health System Surge Capacity for Extreme Weather Events",
        "priority_base": 1,
    },
    {
        "id": "who_auth_workaction_01",
        "audience": "AUTHORITY",
        "severity_levels": ["VERY_HIGH", "EXTREME"],
        "category": "OUTDOOR_WORK_ACTION",
        "action": "Enact municipal guidelines or advisories restricting non-essential outdoor public works and construction during peak thermal hours.",
        "source": "WHO",
        "source_reference": "WHO Heat-Health Guidance: Occupational and Municipal Labor Protective Measures",
        "priority_base": 1,
    },
    {
        "id": "who_auth_outreach_01",
        "audience": "AUTHORITY",
        "severity_levels": ["MODERATE", "HIGH", "VERY_HIGH", "EXTREME"],
        "category": "VULNERABLE_POPULATION_OUTREACH",
        "action": "Mobilize social workers, healthcare workers, and community volunteers to actively check on homeless, elderly, and vulnerable residents.",
        "source": "WHO",
        "source_reference": "WHO Public Health Interventions: Active Community Outreach in Heatwaves",
        "priority_base": 2,
    },
    {
        "id": "who_auth_resources_01",
        "audience": "AUTHORITY",
        "severity_levels": ["HIGH", "VERY_HIGH", "EXTREME"],
        "category": "RESOURCE_PREPARATION",
        "action": "Ensure uninterrupted electrical grid reliability, protect water supply lines, and stage additional emergency response units in high-density urban areas.",
        "source": "WHO",
        "source_reference": "WHO Heat Action Planning: Critical Infrastructure & Municipal Resilience",
        "priority_base": 2,
    },
    {
        "id": "who_auth_routine_01",
        "audience": "AUTHORITY",
        "severity_levels": ["LOW"],
        "category": "HEAT_ACTION_PLAN",
        "action": "Maintain seasonal surveillance of meteorological indicators, review heat action protocols, and test emergency communication channels.",
        "source": "WHO",
        "source_reference": "WHO Heat-Health Action Plans: Pre-Season Readiness Protocols",
        "priority_base": 3,
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


