const cities = [
  { name: "Pune", lat: 18.5204, lon: 73.8567 }, { name: "Mumbai", lat: 19.0760, lon: 72.8777 },
  { name: "Delhi", lat: 28.6139, lon: 77.2090 }, { name: "Ahmedabad", lat: 23.0225, lon: 72.5714 },
  { name: "Chennai", lat: 13.0827, lon: 80.2707 }, { name: "Kolkata", lat: 22.5726, lon: 88.3639 },
];
const colors = { White: "#ffffff", Green: "#38d430", Yellow: "#fff700", Red: "#ff0909", Black: "#050505" };
const map = L.map("map", { zoomControl: true }).setView([21.2, 78.2], 5);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "© OpenStreetMap contributors" }).addTo(map);
const markers = new Map(); let selected;

function text(value, fallback = "No result") { return value == null ? fallback : value; }
function celsius(value) { return value == null ? "—" : `${value.toFixed(1)}°C`; }
function flagClass(flag) { return (flag || "White").toLowerCase(); }
function markerIcon(flag) { return L.divIcon({ className: "", iconSize: [25, 25], iconAnchor: [12, 12], html: `<div class="city-marker" style="width:25px;height:25px;background:${colors[flag] || "#aab7c2"}"></div>` }); }

function renderDetails(city, payload) {
  const current = payload.current;
  document.querySelector("#place").textContent = `${city.name.toUpperCase()} · ${current.time}`;
  document.querySelector("#updated").textContent = `Last refreshed ${new Date(payload.updated_at).toLocaleTimeString()} · updates every 5 min`;
  document.querySelector("#current").className = `current-card ${flagClass(current.risk)}`;
  document.querySelector("#current").innerHTML = current.wbgt_c == null ? "<h3>Current WBGT unavailable</h3><p>The solver did not converge for this observation.</p>" : `<h3>Current WBGT · ${current.risk}</h3><p class="wbgt">${celsius(current.wbgt_c)}</p><p>Air ${celsius(current.tair_c)} · RH ${text(current.rh_pct)}% · Wind ${text(current.wind_ms)} m/s</p>`;
  const forecast = document.querySelector("#forecast"); forecast.replaceChildren();
  payload.daily_max_wbgt.forEach(item => { const row = document.querySelector("#forecast-row").content.cloneNode(true); const article = row.querySelector("article"); article.classList.add(flagClass(item.risk)); row.querySelector("time").textContent = new Date(`${item.time.slice(0, 10)}T00:00:00Z`).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" }); row.querySelector("strong").textContent = celsius(item.wbgt_c); row.querySelector("span").textContent = item.risk; forecast.append(row); });
}

async function selectCity(city, updateView = true) {
  selected = city; document.querySelector("#place").textContent = `${city.name.toUpperCase()} · UPDATING`;
  try {
    const response = await fetch(`/api/wbgt?lat=${city.lat}&lon=${city.lon}`); const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Request failed");
    const marker = markers.get(city.name); marker.setIcon(markerIcon(payload.current.risk)); marker.bindPopup(`${city.name}<br>${celsius(payload.current.wbgt_c)} · ${payload.current.risk}`);
    renderDetails(city, payload); if (updateView) { map.flyTo([city.lat, city.lon], 8); marker.openPopup(); }
  } catch (error) { document.querySelector("#current").innerHTML = `<h3>Update failed</h3><p>${error.message}</p>`; document.querySelector("#updated").textContent = "Could not fetch live weather"; }
}

cities.forEach(city => { const marker = L.marker([city.lat, city.lon], { icon: markerIcon() }).addTo(map).bindTooltip(city.name); marker.on("click", () => selectCity(city)); markers.set(city.name, marker); });
selectCity(cities[0], false);
setInterval(() => selected && selectCity(selected, false), 5 * 60 * 1000);
