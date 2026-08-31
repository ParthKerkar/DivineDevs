/**
 * Extreme Heatwave Early Warning & Epidemiological Mortality Risk GIS Client.
 */

const defaultCities = [
  { name: "Pune", query: "Pune", lat: 18.5196, lon: 73.8554 },
  { name: "Mumbai", query: "Mumbai", lat: 19.0760, lon: 72.8777 },
  { name: "Delhi", query: "Delhi", lat: 28.6139, lon: 77.2090 },
  { name: "Jaipur", query: "Jaipur", lat: 26.9124, lon: 75.7873 },
  { name: "Nagpur", query: "Nagpur", lat: 21.1458, lon: 79.0882 },
  { name: "Kochi", query: "Kochi, India", lat: 9.9399, lon: 76.2602 },
  { name: "Ahmedabad", query: "Ahmedabad", lat: 23.0225, lon: 72.5714 },
  { name: "Hyderabad", query: "Hyderabad", lat: 17.3850, lon: 78.4867 },
  { name: "Bhopal", query: "Bhopal", lat: 23.2599, lon: 77.4126 },
  { name: "Kolkata", query: "Kolkata", lat: 22.5726, lon: 88.3639 },
  { name: "Chennai", query: "Chennai", lat: 13.0827, lon: 80.2707 },
  { name: "Lucknow", query: "Lucknow", lat: 26.8467, lon: 80.9462 },
  { name: "Patna", query: "Patna", lat: 25.5941, lon: 85.1376 },
];

const categoryColors = {
  Low: "#10b981",
  Moderate: "#f59e0b",
  High: "#f97316",
  "Very High": "#ef4444",
  Extreme: "#dc2626"
};

const map = L.map("map", { zoomControl: true }).setView([21.5, 78.9], 5);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
  attribution: "© OpenStreetMap contributors | Open-Meteo"
}).addTo(map);

const markers = new Map();
let currentSelectedCity = null;
let currentAudience = "PUBLIC";
let recommendationsOpen = false;

function getCategoryClass(category) {
  if (!category) return "low";
  return category.toLowerCase().replace(/\s+/g, "-");
}

function createMarkerIcon(riskCategory, wbgt) {
  const color = categoryColors[riskCategory] || "#38bdf8";
  const label = wbgt != null ? `${wbgt.toFixed(1)}°` : "—";
  return L.divIcon({
    className: "custom-map-icon",
    iconSize: [38, 38],
    iconAnchor: [19, 19],
    html: `<div class="marker-bubble" style="background:${color};" title="${riskCategory || 'Unknown'}">
      <span>${label}</span>
    </div>`
  });
}

function celsius(val) {
  return val == null ? "—" : `${Number(val).toFixed(1)}°C`;
}

function renderDetails(payload) {
  const loc = payload.location;
  const curr = payload.current;
  const forecast = payload.forecast || [];

  // 1. Header Location
  document.querySelector("#place").textContent = `${loc.city.toUpperCase()} · LIVE OBSERVATION`;
  const regionParts = [loc.admin1, loc.country, `(${loc.latitude.toFixed(2)}°N, ${loc.longitude.toFixed(2)}°E)`].filter(Boolean);
  document.querySelector("#region-info").textContent = regionParts.join(", ");
  document.querySelector("#updated").textContent = `Last updated: ${new Date().toLocaleTimeString()} · Updates every 5m`;

  // 2. Current WBGT Card
  const currentCard = document.querySelector("#current");
  if (curr.wbgt == null) {
    currentCard.innerHTML = `<h3>Current Observation</h3><p>Observation data currently unavailable for this point.</p>`;
  } else {
    currentCard.innerHTML = `
      <h3>
        <span>Outdoor WBGT (Liljegren Model)</span>
        <span class="metric-badge ${getCategoryClass(curr.riskCategory)}">${curr.riskCategory} Risk</span>
      </h3>
      <div class="wbgt-display">${celsius(curr.wbgt)}</div>
      <div class="weather-stats">
        <span><strong>Air Temp:</strong> ${celsius(curr.temperature_c)}</span>
        <span><strong>Humidity:</strong> ${curr.relative_humidity_pct ?? "—"}%</span>
        <span><strong>Wind:</strong> ${curr.wind_speed_ms != null ? curr.wind_speed_ms.toFixed(1) + " m/s" : "—"}</span>
        <span><strong>Solar:</strong> ${curr.shortwave_radiation_wm2 != null ? curr.shortwave_radiation_wm2.toFixed(0) + " W/m²" : "—"}</span>
      </div>
    `;
  }

  // 3. Epidemiological Mortality Metrics Card
  const mriVal = curr.mortalityRiskIndex != null ? curr.mortalityRiskIndex.toFixed(1) : "—";
  const rrVal = curr.relativeRisk != null ? curr.relativeRisk.toFixed(3) : "—";
  const afVal = curr.attributableFraction != null ? `${(curr.attributableFraction * 100).toFixed(1)}%` : "0.0%";
  const cat = curr.riskCategory || "Low";

  document.querySelector("#mri-val").textContent = `${mriVal} / 100`;
  const mriPercent = Math.min(100, Math.max(0, curr.mortalityRiskIndex || 0));
  const mriBar = document.querySelector("#mri-bar");
  mriBar.style.width = `${mriPercent}%`;
  mriBar.style.backgroundColor = categoryColors[cat] || "#38bdf8";

  document.querySelector("#rr-val").textContent = rrVal;
  const isAboveBaseline = curr.wbgt != null && curr.wbgt > 30.0;
  const excessPct = curr.relativeRisk != null && curr.relativeRisk > 1.0 
    ? `+${((curr.relativeRisk - 1) * 100).toFixed(1)}% excess risk over baseline` 
    : "Baseline risk (WBGT ≤ 30°C)";
  document.querySelector("#rr-sub").textContent = excessPct;

  document.querySelector("#af-val").textContent = afVal;
  const afSub = document.querySelector("#af-sub");
  if (afSub) {
    afSub.textContent = isAboveBaseline ? "Attributable to heat > 30°C" : "0.0% (below 30°C threshold)";
  }

  const catBadge = document.querySelector("#category-badge");
  catBadge.textContent = cat;
  catBadge.className = `metric-badge ${getCategoryClass(cat)}`;

  // 4. 5-Day Forecast
  const forecastContainer = document.querySelector("#forecast");
  forecastContainer.replaceChildren();

  forecast.forEach(day => {
    const row = document.querySelector("#forecast-row").content.cloneNode(true);
    const dateObj = new Date(`${day.date}T00:00:00Z`);
    const dateStr = dateObj.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
    
    row.querySelector("time").textContent = dateStr;
    row.querySelector(".wbgt-val").textContent = celsius(day.wbgt);
    
    const mriBadge = row.querySelector(".mri-badge");
    mriBadge.textContent = `MRI ${day.mortalityRiskIndex != null ? day.mortalityRiskIndex.toFixed(0) : "—"} · ${day.riskCategory}`;
    mriBadge.className = `mri-badge ${getCategoryClass(day.riskCategory)}`;

    const rrText = row.querySelector(".rr-text");
    const afText = day.attributableFraction != null && day.attributableFraction > 0 ? ` (AF ${(day.attributableFraction * 100).toFixed(1)}%)` : "";
    rrText.textContent = day.relativeRisk != null ? `RR ${day.relativeRisk.toFixed(3)}${afText}` : "—";

    forecastContainer.append(row);
  });

  // If recommendations are open, refresh them for current city
  if (recommendationsOpen && currentSelectedCity) {
    fetchAndRenderRecommendations(currentSelectedCity, currentAudience);
  }
}

async function selectCityByQuery(query, updateMap = true) {
  document.querySelector("#place").textContent = `FETCHING ${query.toUpperCase()}…`;
  try {
    const response = await fetch(`/api/heat-risk?city=${encodeURIComponent(query)}`);
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || "Failed to fetch heat risk data");
    }
    const payload = await response.json();
    currentSelectedCity = payload.location.city;

    // Update / place marker on map
    const lat = payload.location.latitude;
    const lon = payload.location.longitude;
    const key = payload.location.city;

    let marker = markers.get(key);
    if (!marker) {
      marker = L.marker([lat, lon], {
        icon: createMarkerIcon(payload.current.riskCategory, payload.current.wbgt)
      }).addTo(map);
      marker.on("click", () => renderDetails(payload));
      markers.set(key, marker);
    } else {
      marker.setIcon(createMarkerIcon(payload.current.riskCategory, payload.current.wbgt));
    }

    marker.bindPopup(`
      <div style="font-family:sans-serif; text-align:center;">
        <strong>${payload.location.city}</strong><br/>
        WBGT: <strong>${celsius(payload.current.wbgt)}</strong><br/>
        Mortality Risk: <span style="color:${categoryColors[payload.current.riskCategory] || '#333'}; font-weight:bold;">${payload.current.riskCategory}</span>
      </div>
    `);

    renderDetails(payload);

    if (updateMap) {
      map.flyTo([lat, lon], 8, { duration: 1.2 });
      marker.openPopup();
    }
  } catch (error) {
    document.querySelector("#current").innerHTML = `
      <h3>Update Failed</h3>
      <p style="color:#ef4444;">${error.message}</p>
    `;
    document.querySelector("#updated").textContent = "Could not fetch city";
  }
}

async function fetchAndRenderRecommendations(city, audience) {
  const recContainer = document.querySelector("#recommendations-container");
  const insightsList = document.querySelector("#rec-insights");
  const cardsList = document.querySelector("#rec-cards");

  if (!recContainer || !insightsList || !cardsList) return;

  insightsList.innerHTML = `<p style="color:#94a3b8; font-size:0.85rem;">Synthesizing risk insights for ${city}…</p>`;
  cardsList.innerHTML = `<p style="color:#94a3b8; font-size:0.85rem;">Loading evidence-based recommendations…</p>`;

  try {
    const res = await fetch(`/api/recommendations?city=${encodeURIComponent(city)}&audience=${encodeURIComponent(audience)}`);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "Failed to load recommendations");
    }
    const data = await res.json();

    // Render Insights
    insightsList.replaceChildren();
    if (data.insights && data.insights.length > 0) {
      data.insights.forEach(ins => {
        const div = document.createElement("div");
        div.className = "insight-item";
        div.innerHTML = `<span class="insight-tag ${ins.priority}">${ins.type.replace(/_/g, " ")}</span> <span>${ins.message}</span>`;
        insightsList.appendChild(div);
      });
    }

    // Render Recommendations
    cardsList.replaceChildren();
    if (data.recommendations && data.recommendations.length > 0) {
      data.recommendations.forEach(rec => {
        const card = document.createElement("div");
        card.className = `rec-card-item priority-${rec.priority}`;
        card.innerHTML = `
          <div class="rec-card-top">
            <span class="rec-cat-badge">${rec.category.replace(/_/g, " ")} · Priority ${rec.priority}</span>
            <span class="rec-source-badge">${rec.source}</span>
          </div>
          <div class="rec-action-text">${rec.recommendation}</div>
          <div class="rec-reason-text"><strong>Why:</strong> ${rec.reason}</div>
        `;
        cardsList.appendChild(card);
      });
    } else {
      cardsList.innerHTML = `<p style="color:#94a3b8;">No immediate high-severity interventions required for baseline conditions.</p>`;
    }
  } catch (err) {
    cardsList.innerHTML = `<p style="color:#ef4444;">Error loading recommendations: ${err.message}</p>`;
  }
}

function toggleRecommendations() {
  const container = document.querySelector("#recommendations-container");
  const btnText = document.querySelector("#rec-btn-text");
  recommendationsOpen = !recommendationsOpen;

  if (recommendationsOpen) {
    container.style.display = "block";
    btnText.textContent = "Hide Heat-Health Recommendations";
    if (currentSelectedCity) {
      fetchAndRenderRecommendations(currentSelectedCity, currentAudience);
    }
  } else {
    container.style.display = "none";
    btnText.textContent = "Get AI Heat-Health Recommendations";
  }
}

function switchAudience(aud) {
  currentAudience = aud;
  document.querySelectorAll(".aud-tab").forEach(tab => {
    tab.classList.toggle("active", tab.textContent.toUpperCase().includes(aud === "OUTDOOR_WORKER" ? "WORKER" : aud));
  });
  if (currentSelectedCity) {
    fetchAndRenderRecommendations(currentSelectedCity, currentAudience);
  }
}

function searchCity(name) {
  const searchInput = document.querySelector("#city-search");
  if (searchInput) searchInput.value = name;
  selectCityByQuery(name, true);
}

function handleSearch() {
  const query = document.querySelector("#city-search").value.trim();
  if (query) {
    selectCityByQuery(query, true);
  }
}

// Initialize default city markers on the map
async function initDashboard() {
  defaultCities.forEach(city => {
    const marker = L.marker([city.lat, city.lon], {
      icon: createMarkerIcon("Low", null)
    }).addTo(map).bindTooltip(city.name);

    marker.on("click", () => selectCityByQuery(city.query || city.name, false));
    markers.set(city.name, marker);
  });

  // Load first city (Pune) into view
  await selectCityByQuery(defaultCities[0].query, false);

  // Background refresh markers with live values
  for (const city of defaultCities) {
    try {
      const res = await fetch(`/api/heat-risk?city=${encodeURIComponent(city.query || city.name)}`);
      if (res.ok) {
        const data = await res.json();
        const m = markers.get(city.name);
        if (m) {
          m.setIcon(createMarkerIcon(data.current.riskCategory, data.current.wbgt));
          m.bindPopup(`
            <div style="font-family:sans-serif; text-align:center;">
              <strong>${data.location.city}</strong><br/>
              WBGT: <strong>${celsius(data.current.wbgt)}</strong><br/>
              Mortality Risk: <span style="color:${categoryColors[data.current.riskCategory] || '#333'}; font-weight:bold;">${data.current.riskCategory}</span>
            </div>
          `);
        }
      }
    } catch (e) {
      console.warn("Could not preload marker for", city.name, e);
    }
  }
}

initDashboard();

// 5-minute auto refresh
setInterval(() => {
  if (currentSelectedCity) {
    selectCityByQuery(currentSelectedCity, false);
  }
}, 5 * 60 * 1000);
