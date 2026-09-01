"""Evidence-Guided AI Recommendation Engine for Heat-Health Warning System.

Combines:
1. Deterministic Scientific Risk Context (WBGT, MRI, RR, Forecast Trend, Persistence)
2. Authoritative Evidence Library (WHO, NIOSH, OSHA)
3. Deterministic Safety & Rule Engine
4. AI Prioritization & Personalization (with strict validation & zero-failure fallback)
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from recommendation_library import RECOMMENDATION_LIBRARY, get_library_recommendations
from risk_context_engine import build_risk_context
from weather_api import fetch_heat_risk_for_city, fetch_heat_risk_for_coordinates

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.7-flash:generateContent"
CACHE_TTL_SECONDS = 300  # 5 minutes cache
GEMINI_TIMEOUT_SECONDS = int(os.environ.get("GEMINI_TIMEOUT_SECONDS", "30"))

logger = logging.getLogger(__name__)

_recommendation_cache: Dict[str, Dict[str, Any]] = {}


def get_ai_api_key() -> Optional[str]:
    """Retrieve Gemini / AI API key from environment or .env file."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("AI_API_KEY")
    if key:
        return key.strip()

    # Check .env file
    env_path = ".env"
    if os.path.exists(env_path):
        try:
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    clean = line.strip()
                    if clean and not clean.startswith("#") and "=" in clean:
                        k, v = clean.split("=", 1)
                        if k.strip().upper() in ["GEMINI_API_KEY", "AI_API_KEY"]:
                            return v.strip()
        except Exception:
            pass

    return None


def generate_deterministic_recommendations(risk_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate evidence-grounded recommendations using deterministic rules and MRI weighting."""
    audience = risk_context.get("audience", "PUBLIC")
    overall_level = risk_context.get("overall_heat_health_level", "LOW")
    wbgt = risk_context.get("wbgt")
    mri = risk_context.get("mortality_risk_index")
    trend = risk_context.get("forecast_trend", "STABLE")
    elevated_days = risk_context.get("elevated_heat_days", 0)

    raw_items = get_library_recommendations(audience, overall_level)
    if not raw_items:
        # Fallback to LOW if no exact match
        raw_items = get_library_recommendations(audience, "LOW")

    processed: List[Dict[str, Any]] = []

    for item in raw_items:
        base_priority = item.get("priority_base", 3)
        category = item.get("category", "")
        action = item.get("action", "")
        source = item.get("source", "")
        source_ref = item.get("source_reference", "")

        # Dynamic priority adjustment based on MRI and Trend
        priority = base_priority
        if overall_level in ["VERY_HIGH", "EXTREME"]:
            priority = 1
        elif overall_level == "HIGH":
            if category in ["EXPOSURE_REDUCTION", "HYDRATION", "REST_RECOVERY", "PUBLIC_ALERT"]:
                priority = 1
            else:
                priority = 2
        elif overall_level == "MODERATE" and trend in ["RAPIDLY_INCREASING", "INCREASING"]:
            if category in ["HYDRATION", "COOLING", "WORK_SCHEDULING"]:
                priority = min(priority, 2)

        # Context-aware reason generation
        wbgt_str = f"{wbgt:.1f}Â°C" if wbgt is not None else "elevated"
        if overall_level in ["VERY_HIGH", "EXTREME"]:
            reason = f"Current WBGT is critical ({wbgt_str}) with very high epidemiological risk (MRI: {mri or 'N/A'}); immediate protective action is necessary."
        elif overall_level == "HIGH":
            reason = f"WBGT is high ({wbgt_str}) with significant thermal strain; protective measures are recommended before heat peaks."
        elif trend in ["RAPIDLY_INCREASING", "INCREASING"]:
            reason = f"Thermal stress is currently moderate ({wbgt_str}) but forecast to intensify over the 5-day period."
        else:
            reason = f"Routine heat-health precaution for baseline environmental conditions (WBGT: {wbgt_str})."

        processed.append({
            "priority": priority,
            "category": category,
            "recommendation": action,
            "reason": reason,
            "source": source,
            "source_reference": source_ref,
        })

    # Sort by priority (1 is highest)
    processed.sort(key=lambda x: x["priority"])
    return processed


def call_ai_personalizer(
    risk_context: Dict[str, Any],
    approved_recommendations: List[Dict[str, Any]],
    api_key: str
) -> Optional[List[Dict[str, Any]]]:
    """Call Google Gemini API to prioritize, contextualize, and tailor wording of approved actions."""
    system_prompt = (
        "You are an Evidence-Guided Heat-Health Recommendation Assistant.\n"
        "STRICT SAFETY & METHODOLOGICAL RULES:\n"
        "1. You MUST ONLY use the supplied approved recommendations from the Evidence Library.\n"
        "2. Do NOT invent new medical treatments, drugs, medications, or clinical interventions.\n"
        "3. Do NOT predict or state exact death counts or make ungrounded mortality claims.\n"
        "4. Do NOT alter WBGT, Mortality Risk Index (MRI), or Relative Risk (RR) values.\n"
        "5. Tailor the language and prioritize the actions according to the supplied risk context, forecast trend, and audience.\n"
        "6. Provide a concise, scientifically sound 'reason' for each recommendation explaining how it relates to the current WBGT/MRI/trend.\n"
        "7. Return ONLY a valid JSON array of objects with the exact schema:\n"
        "   [{\n"
        "     \"priority\": 1,\n"
        "     \"category\": \"CATEGORY_NAME\",\n"
        "     \"recommendation\": \"Action text tailored to audience\",\n"
        "     \"reason\": \"Contextual justification from risk data\",\n"
        "     \"source\": \"WHO/NIOSH/OSHA\",\n"
        "     \"source_reference\": \"Document reference from input\"\n"
        "   }]"
    )

    user_payload = {
        "risk_context": {
            "wbgt": risk_context.get("wbgt"),
            "wbgt_level": risk_context.get("wbgt_level"),
            "mortality_risk_index": risk_context.get("mortality_risk_index"),
            "mortality_risk_level": risk_context.get("mortality_risk_level"),
            "relative_risk": risk_context.get("relative_risk"),
            "forecast_trend": risk_context.get("forecast_trend"),
            "elevated_heat_days": risk_context.get("elevated_heat_days"),
            "peak_wbgt": risk_context.get("peak_wbgt"),
            "peak_day": risk_context.get("peak_day"),
            "overall_heat_health_level": risk_context.get("overall_heat_health_level"),
            "audience": risk_context.get("audience")
        },
        "approved_recommendations": approved_recommendations
    }

    url = f"{GEMINI_API_BASE}?key={api_key}"
    body_data = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_prompt}\n\nINPUT DATA:\n{json.dumps(user_payload, indent=2)}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }

    req = Request(
        url,
        data=json.dumps(body_data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urlopen(req, timeout=GEMINI_TIMEOUT_SECONDS) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            candidates = res_json.get("candidates", [])
            if not candidates:
                return None
            content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            parsed = json.loads(content_text)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict) and "recommendations" in parsed:
                return parsed["recommendations"]
            return None
    except HTTPError as error:
        logger.warning("Gemini personalization unavailable (HTTP %s); using deterministic recommendations.", error.code)
        return None
    except URLError as error:
        logger.warning("Gemini personalization network error (%s); using deterministic recommendations.", error.reason)
        return None
    except TimeoutError:
        logger.warning("Gemini personalization timed out after %s seconds; using deterministic recommendations.", GEMINI_TIMEOUT_SECONDS)
        return None
    except (json.JSONDecodeError, KeyError, ValueError) as error:
        logger.warning("Gemini returned an invalid personalization response (%s); using deterministic recommendations.", type(error).__name__)
        return None


def validate_ai_output(
    ai_output: Optional[List[Dict[str, Any]]],
    approved_recommendations: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Validate AI recommendations against approved categories, sources, and safety rules."""
    def _normalize_fallback(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        norm = []
        for it in items:
            copy_it = dict(it)
            if "recommendation" not in copy_it and "action" in copy_it:
                copy_it["recommendation"] = copy_it["action"]
            if "reason" not in copy_it:
                copy_it["reason"] = "Evidence-based heat-health protective intervention."
            norm.append(copy_it)
        return norm

    if not ai_output or not isinstance(ai_output, list):
        return _normalize_fallback(approved_recommendations)

    approved_categories = {item["category"] for item in approved_recommendations}
    approved_sources = {"WHO", "NIOSH", "OSHA"}

    forbidden_keywords = [
        "prescribe", "medication", "pill", "aspirin", "paracetamol",
        "ibuprofen", "antibiotic", "exact deaths", "will die", "fatalities count"
    ]

    validated: List[Dict[str, Any]] = []

    for item in ai_output:
        if not isinstance(item, dict):
            continue

        cat = item.get("category", "")
        rec = str(item.get("recommendation", "")).strip()
        reason = str(item.get("reason", "")).strip()
        source = str(item.get("source", "")).strip().upper()
        prio = item.get("priority", 3)

        # Check safety keywords
        text_to_check = (rec + " " + reason).lower()
        if any(bad_word in text_to_check for bad_word in forbidden_keywords):
            continue

        # Check valid structure
        if not rec or not reason:
            continue

        # Match category and source
        if cat not in approved_categories and approved_categories:
            # Re-map or fallback
            cat = list(approved_categories)[0]
        if source not in approved_sources:
            source = "WHO"

        validated.append({
            "priority": int(prio) if isinstance(prio, (int, float)) and 1 <= prio <= 5 else 2,
            "category": cat,
            "recommendation": rec,
            "reason": reason,
            "source": source,
            "source_reference": item.get("source_reference", "Authoritative Heat-Health Guidelines")
        })

    def _normalize_fallback(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        norm = []
        for it in items:
            copy_it = dict(it)
            if "recommendation" not in copy_it and "action" in copy_it:
                copy_it["recommendation"] = copy_it["action"]
            if "reason" not in copy_it:
                copy_it["reason"] = "Evidence-based heat-health protective intervention."
            norm.append(copy_it)
        return norm

    if not validated:
        return _normalize_fallback(approved_recommendations)

    validated.sort(key=lambda x: x["priority"])
    return validated


def get_heat_health_recommendations_for_risk_payload(
    heat_risk_payload: Dict[str, Any],
    audience: str = "PUBLIC"
) -> Dict[str, Any]:
    """Generate recommendations from an existing heat-risk pipeline payload."""
    curr = heat_risk_payload.get("current", {})
    forecast = heat_risk_payload.get("forecast", [])
    loc = heat_risk_payload.get("location", {})

    risk_ctx = build_risk_context(
        current_wbgt=curr.get("wbgt"),
        current_mri=curr.get("mortalityRiskIndex"),
        current_rr=curr.get("relativeRisk"),
        current_af=curr.get("attributableFraction"),
        forecast_days=forecast,
        audience=audience
    )

    # 1. Deterministic evidence selection
    deterministic_recs = generate_deterministic_recommendations(risk_ctx)

    # 2. AI Prioritization / Personalization if key available
    api_key = get_ai_api_key()
    ai_used = False
    final_recs = deterministic_recs

    if api_key:
        ai_raw = call_ai_personalizer(risk_ctx, deterministic_recs, api_key)
        if ai_raw:
            validated = validate_ai_output(ai_raw, deterministic_recs)
            if validated:
                final_recs = validated
                ai_used = True

    return {
        "location": loc,
        "risk_context": {
            "wbgt": risk_ctx["wbgt"],
            "wbgt_level": risk_ctx["wbgt_level"],
            "mortality_risk_index": risk_ctx["mortality_risk_index"],
            "mortality_risk_level": risk_ctx["mortality_risk_level"],
            "relative_risk": risk_ctx["relative_risk"],
            "forecast_trend": risk_ctx["forecast_trend"],
            "elevated_heat_days": risk_ctx["elevated_heat_days"],
            "peak_wbgt": risk_ctx["peak_wbgt"],
            "peak_day": risk_ctx["peak_day"],
            "overall_heat_health_level": risk_ctx["overall_heat_health_level"],
            "audience": risk_ctx["audience"],
        },
        "insights": risk_ctx["insights"],
        "recommendations": final_recs,
        "engine_metadata": {
            "ai_personalization_applied": ai_used,
            "ai_model": GEMINI_API_BASE.rsplit("/", 1)[-1].split(":", 1)[0],
            "ai_timeout_seconds": GEMINI_TIMEOUT_SECONDS,
            "evidence_sources": ["WHO", "NIOSH", "OSHA"],
            "safety_model": "Deterministic Evidence Selection with AI Prioritization and Output Validation"
        }
    }


def get_heat_health_recommendations(
    city_name: str,
    audience: str = "PUBLIC",
    forecast_days: int = 5
) -> Dict[str, Any]:
    """Execute end-to-end recommendation pipeline for ANY city worldwide with caching."""
    cache_key = f"{city_name.strip().lower()}:{audience.strip().upper()}:{forecast_days}"
    cached = _recommendation_cache.get(cache_key)
    if cached and (time.time() - cached["created"] < CACHE_TTL_SECONDS):
        return cached["payload"]

    heat_risk_payload = fetch_heat_risk_for_city(city_name, forecast_days=forecast_days)
    payload = get_heat_health_recommendations_for_risk_payload(heat_risk_payload, audience=audience)
    
    _recommendation_cache[cache_key] = {"created": time.time(), "payload": payload}
    return payload


def get_heat_health_recommendations_for_coords(
    latitude: float,
    longitude: float,
    audience: str = "PUBLIC",
    city_name: Optional[str] = None,
    forecast_days: int = 5
) -> Dict[str, Any]:
    """Execute recommendation pipeline for arbitrary coordinates with caching."""
    cache_key = f"{round(latitude, 4)},{round(longitude, 4)}:{audience.strip().upper()}:{forecast_days}"
    cached = _recommendation_cache.get(cache_key)
    if cached and (time.time() - cached["created"] < CACHE_TTL_SECONDS):
        return cached["payload"]

    heat_risk_payload = fetch_heat_risk_for_coordinates(
        latitude, longitude, city_name=city_name, forecast_days=forecast_days
    )
    payload = get_heat_health_recommendations_for_risk_payload(heat_risk_payload, audience=audience)

    _recommendation_cache[cache_key] = {"created": time.time(), "payload": payload}
    return payload

