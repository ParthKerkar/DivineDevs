const cities = [
  { name: "Pune", lat: 18.5204, lon: 73.8567 }, { name: "Mumbai", lat: 19.0760, lon: 72.8777 },
  { name: "Delhi", lat: 28.6139, lon: 77.2090 }, { name: "Ahmedabad", lat: 23.0225, lon: 72.5714 },
  { name: "Chennai", lat: 13.0827, lon: 80.2707 }, { name: "Kolkata", lat: 22.5726, lon: 88.3639 },
];
const mortalityColors = { Low: "#2e7d32", Moderate: "#f9a825", High: "#ef6c00", "Very high": "#c62828", Unavailable: "#aab7c2" };
const map = L.map("map", { zoomControl: true }).setView([21.2, 78.2], 5);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "© OpenStreetMap contributors" }).addTo(map);
const markers = new Map(); let selected;

function text(value, fallback = "No result") { return value == null ? fallback : value; }
function celsius(value) { return value == null ? "—" : `${value.toFixed(1)}°C`; }
function flagClass(flag) { return (flag || "White").toLowerCase(); }
function mortalityClass(band) { return (band || "Unavailable").toLowerCase().replaceAll(" ", "-"); }
function markerIcon(color) { return L.divIcon({ className: "", iconSize: [25, 25], iconAnchor: [12, 12], html: `<div class="city-marker" style="width:25px;height:25px;background:${color}"></div>` }); }

function renderDetails(city, payload) {
  const current = payload.current;
  document.querySelector("#place").textContent = `${city.name.toUpperCase()} · ${current.time}`;
  document.querySelector("#updated").textContent = `Last refreshed ${new Date(payload.updated_at).toLocaleTimeString()} · updates every 5 min`;
  document.querySelector("#current").className = `current-card ${flagClass(current.risk)}`;
  document.querySelector("#current").innerHTML = current.wbgt_c == null ? "<h3>Current WBGT unavailable</h3><p>The solver did not converge for this observation.</p>" : `<h3>Current WBGT · ${current.risk}</h3><p class="wbgt">${celsius(current.wbgt_c)}</p><p>Air ${celsius(current.tair_c)} · RH ${text(current.rh_pct)}% · Wind ${text(current.wind_ms)} m/s</p>`;
  const forecast = document.querySelector("#forecast"); forecast.replaceChildren();
  payload.daily_max_wbgt.forEach(item => { const row = document.querySelector("#forecast-row").content.cloneNode(true); const article = row.querySelector("article"); article.classList.add(flagClass(item.risk)); row.querySelector("time").textContent = new Date(`${item.time.slice(0, 10)}T00:00:00Z`).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" }); row.querySelector("strong").textContent = celsius(item.wbgt_c); row.querySelector("span").textContent = item.risk; forecast.append(row); });
}

function renderMortality(data, error = null) {
  const panel = document.querySelector("#mortality");
  if (error) { panel.className = "mortality-card"; panel.innerHTML = `<h3>Risk unavailable</h3><p>${error}</p>`; return; }
  panel.className = `mortality-card ${mortalityClass(data.mortality_risk_band)}`;
  panel.innerHTML = `<h3>${data.mortality_risk_band} forecast risk</h3><p class="score">${data.mortality_risk_factor_0_100.toFixed(1)} / 100</p><p>Town vulnerability ${data.demographic_vulnerability_0_100.toFixed(1)} · Peak WBGT ${celsius(data.forecast_peak_wbgt_c)}</p>`;
}

async function fetchMortality(city) {
  const response = await fetch(`/api/mortality-risk?city=${encodeURIComponent(city.name)}&lat=${city.lat}&lon=${city.lon}`);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Risk unavailable");
  return payload;
}

async function colourMarkerForRisk(city) {
  try {
    const risk = await fetchMortality(city); const marker = markers.get(city.name);
    marker.setIcon(markerIcon(mortalityColors[risk.mortality_risk_band]));
    marker.bindPopup(`${city.name}<br>Mortality risk: ${risk.mortality_risk_factor_0_100.toFixed(1)} / 100 · ${risk.mortality_risk_band}`);
    return risk;
  } catch (_) {
    markers.get(city.name).setIcon(markerIcon(mortalityColors.Unavailable));
    return null;
  }
}

async function selectCity(city, updateView = true) {
  selected = city; document.querySelector("#place").textContent = `${city.name.toUpperCase()} · UPDATING`;
  try {
    const weatherRequest = fetch(`/api/wbgt?lat=${city.lat}&lon=${city.lon}`).then(async response => { const payload = await response.json(); if (!response.ok) throw new Error(payload.error || "Request failed"); return payload; });
    const [payload, mortality] = await Promise.all([weatherRequest, colourMarkerForRisk(city)]);
    renderDetails(city, payload); renderMortality(mortality, mortality ? null : "No unambiguous Census-town demographic match is configured for this city.");
    if (updateView) { map.flyTo([city.lat, city.lon], 8); markers.get(city.name).openPopup(); }
  } catch (error) { document.querySelector("#current").innerHTML = `<h3>Update failed</h3><p>${error.message}</p>`; document.querySelector("#updated").textContent = "Could not fetch live weather"; renderMortality(null, error.message); }
}

cities.forEach(city => { const marker = L.marker([city.lat, city.lon], { icon: markerIcon(mortalityColors.Unavailable) }).addTo(map).bindTooltip(city.name); marker.on("click", () => selectCity(city)); markers.set(city.name, marker); });
cities.forEach(colourMarkerForRisk);
selectCity(cities[0], false);
setInterval(() => selected && selectCity(selected, false), 5 * 60 * 1000);
