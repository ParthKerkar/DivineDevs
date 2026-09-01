// HeatShield Dashboard Application
function initTheme() {
  const saved = localStorage.getItem("heatshield_theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const theme = saved || (prefersDark ? "dark" : "light");
  setTheme(theme);
}

function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("heatshield_theme", theme);
  const toggleBtn = document.getElementById("themeToggle");
  if (toggleBtn) {
    toggleBtn.setAttribute("aria-pressed", theme === "dark");
    const label = toggleBtn.querySelector(".theme-btn-text");
    if (label) label.textContent = theme === "dark" ? "Light Mode" : "Dark Mode";
  }
}

const themeToggleBtn = document.getElementById("themeToggle");
if (themeToggleBtn) {
  themeToggleBtn.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") || "light";
    setTheme(current === "dark" ? "light" : "dark");
  });
}
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", e => {
  if (!localStorage.getItem("heatshield_theme")) {
    setTheme(e.matches ? "dark" : "light");
  }
});
initTheme();

const cities=[["Mumbai",19.076,72.878],["Delhi",28.614,77.209],["Bengaluru",12.972,77.595],["Hyderabad",17.385,78.487],["Chennai",13.083,80.271],["Kolkata",22.573,88.364],["Pune",18.520,73.857],["Ahmedabad",23.023,72.571],["Jaipur",26.912,75.787],["Lucknow",26.847,80.947],["Kanpur",26.449,80.332],["Nagpur",21.146,79.088],["Indore",22.719,75.857],["Bhopal",23.260,77.412],["Surat",21.170,72.831],["Vadodara",22.307,73.181],["Visakhapatnam",17.686,83.218],["Vijayawada",16.506,80.648],["Kochi",9.932,76.267],["Thiruvananthapuram",8.525,76.936],["Coimbatore",11.017,76.955],["Madurai",9.925,78.120],["Mysuru",12.295,76.640],["Patna",25.594,85.138],["Ranchi",23.345,85.309],["Bhubaneswar",20.296,85.825],["Guwahati",26.145,91.736],["Srinagar",34.083,74.797],["Chandigarh",30.734,76.779],["Dehradun",30.316,78.032],["Raipur",21.251,81.629],["Jodhpur",26.239,73.024],["Nashik",19.997,73.790],["Aurangabad",19.876,75.343],["Faridabad",28.409,77.317],["Noida",28.535,77.391]].map(([name,lat,lon])=>({name,lat,lon}));
// Fixed threshold stops mirror the WBGT flag methodology, not the current API range.
const colors={Blue:"#0284c7",Green:"#10b981",Yellow:"#f59e0b",Orange:"#ea580c",Red:"#dc2626",White:"#0284c7",Black:"#dc2626"}, stops=[[24,"#0284c7"],[27.8,"#10b981"],[29.5,"#f59e0b"],[31.1,"#ea580c"],[32.2,"#dc2626"],[35,"#881337"]];
const map=L.map("map",{zoomControl:false,minZoom:4}).setView([22.7,79.2],5);
// Leaflet's normal overlay pane is 400.  Keep the base context below it and
// put the provider's transparent annotation tiles in their own label pane.
map.createPane("basemap");map.getPane("basemap").style.zIndex=200;
map.createPane("labels");map.getPane("labels").style.zIndex=450;
L.control.zoom({position:"bottomright"}).addTo(map);
L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}",{pane:"basemap",maxZoom:18,attribution:"Tiles © Esri — Source: Esri, USGS, NOAA"}).addTo(map);
L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Reference_Overlay/MapServer/tile/{z}/{y}/{x}",{pane:"labels",maxZoom:18,attribution:"© Esri"}).addTo(map);const markers=new Map();let selected,fieldLayer;
// The bundled server hosts both UI and API on :8000.  When a development
// server hosts the static dashboard on another local port, use that backend
// explicitly instead of issuing a broken relative request to the dev server.
const apiBase=(location.hostname==="localhost"||location.hostname==="127.0.0.1")&&location.port!=="8000"?"http://localhost:8000":"";
const apiUrl=path=>`${apiBase}${path}`;
const text=(v,f="—")=>v==null?f:v,celsius=v=>v==null?"—":`${v.toFixed(1)}°C`,flagClass=f=>(f||"Blue").toLowerCase().replace(/\s+/g,"");
const istTime=(v,opts={hour:"numeric",minute:"2-digit",hour12:true})=>v?new Date(v).toLocaleTimeString("en-IN",{timeZone:"Asia/Kolkata",...opts})+" IST":"—";
const istDateTime=v=>v?new Date(v).toLocaleString("en-IN",{timeZone:"Asia/Kolkata",day:"numeric",month:"short",hour:"numeric",minute:"2-digit",hour12:true})+" IST":"—";
function markerIcon(flag,active=false){return L.divIcon({className:"",iconSize:[active?18:10,active?18:10],iconAnchor:[active?9:5,active?9:5],html:`<span class="city-marker ${active?"selected":""}" style="background:${colors[flag]||"#71818b"}"></span>`})}
function renderDetails(city,payload){const c=payload.current;const currentRisk=(c.risk==="White")?"Blue":(c.risk==="Black"?"Red":(c.risk||"Blue"));place.textContent=`${city.name.toUpperCase()} · ${istDateTime(c.time)}`;updated.textContent=`Analysis updated ${istTime(payload.updated_at,{hour:"2-digit",minute:"2-digit",second:"2-digit"})}`;current.className=`current-card ${flagClass(currentRisk)}`;current.style.backgroundColor=colors[currentRisk]||"#0284c7";current.style.color=(currentRisk==="Yellow")?"#0f172a":"#ffffff";current.innerHTML=c.wbgt_c==null?"<h3>Current WBGT unavailable</h3><p>The physical solver did not converge.</p>":`<h3>Current WBGT <span>${currentRisk}</span></h3><p class="wbgt">${celsius(c.wbgt_c)}</p><p>Air ${celsius(c.tair_c)} · RH ${text(c.rh_pct)}% · Wind ${text(c.wind_ms)} m/s</p><p>Solar ${text(c.solar_wm2)} W/m²</p>`;forecast.replaceChildren();payload.daily_max_wbgt.forEach(i=>{const rowRisk=(i.risk==="White")?"Blue":(i.risk==="Black"?"Red":(i.risk||"Blue"));const row=forecastRow.content.cloneNode(true),a=row.querySelector("article");a.classList.add(flagClass(rowRisk));a.style.backgroundColor=colors[rowRisk]||"#0284c7";a.style.color=(rowRisk==="Yellow")?"#0f172a":"#ffffff";row.querySelector("time").textContent=new Date(i.time).toLocaleDateString("en-IN",{timeZone:"Asia/Kolkata",weekday:"short",month:"short",day:"numeric"});row.querySelector("strong").textContent=celsius(i.wbgt_c);row.querySelector("span").textContent=rowRisk;forecast.append(row)});details.classList.add("visible")}
async function selectCity(city,view=true){selected=city;place.textContent=`${city.name.toUpperCase()} · UPDATING`;for(const[n,m]of markers)m.setIcon(markerIcon(m.options.risk,n===city.name));try{const r=await fetch(apiUrl(`/api/wbgt?lat=${city.lat}&lon=${city.lon}`)),p=await r.json();if(!r.ok)throw Error(p.error||"Weather service is temporarily unavailable.");const m=markers.get(city.name);if(m){m.options.risk=p.current.risk;m.setIcon(markerIcon(p.current.risk,true));m.bindPopup(`<b>${city.name}</b><br>${celsius(p.current.wbgt_c)} · ${p.current.risk}`).openPopup()}renderDetails(city,p);if(view)map.flyTo([city.lat,city.lon],Math.max(map.getZoom(),7),{duration:.7})}catch(e){current.innerHTML=`<h3>Weather update failed</h3><p>${e.message==="Failed to fetch"?"Unable to reach the local WBGT service. Start dashboard_server.py and try again.":e.message}</p>`;details.classList.add("visible")}}
function colorFor(v){for(let i=1;i<stops.length;i++)if(v<=stops[i][0]){const a=stops[i-1],b=stops[i],t=(v-a[0])/(b[0]-a[0]),aa=a[1].match(/\w\w/g).map(x=>parseInt(x,16)),bb=b[1].match(/\w\w/g).map(x=>parseInt(x,16));return `rgb(${aa.map((x,j)=>Math.round(x+(bb[j]-x)*t)).join(",")})`}return stops.at(-1)[1]}
function interpolate(lat,lon,points){let w=0,sum=0;for(const p of points){const d=Math.max(.08,Math.hypot((p.lat-lat)*1.1,(p.lon-lon)*Math.cos(lat*Math.PI/180))),x=1/(d*d);w+=x;sum+=x*p.wbgt_c}return sum/w}
// Leaflet's base tiles are EPSG:3857.  SVG coordinates therefore use the same
// Web-Mercator Y axis rather than treating degrees of latitude as linear pixels.
function mercatorY(lat){const r=lat*Math.PI/180;return Math.log(Math.tan(Math.PI/4+r/2))}
function latitudeFromMercator(y){return (2*Math.atan(Math.exp(y))-Math.PI/2)*180/Math.PI}
function renderField(d,boundary){
 const[minLon,minLat,maxLon,maxLat]=[66,6,99,37],width=660,height=680,top=mercatorY(maxLat),bottom=mercatorY(minLat);
 const x=lon=>(lon-minLon)/(maxLon-minLon)*width, y=lat=>(top-mercatorY(lat))/(top-bottom)*height;
 const polygons=boundary.features[0].geometry.coordinates;
 const path=polygons.flatMap(polygon=>polygon.map(ring=>ring.map(([lon,lat],i)=>`${i?"L":"M"}${x(lon).toFixed(2)} ${y(lat).toFixed(2)}`).join(" ")+" Z"));
 const cols=110,rows=110;let cells="";
 for(let row=0;row<rows;row++)for(let col=0;col<cols;col++){const yy=row/rows*height,lat=latitudeFromMercator(top-(yy+height/rows/2)/height*(top-bottom)),lon=minLon+(col+.5)/cols*(maxLon-minLon);cells+=`<rect x="${col/cols*width}" y="${yy}" width="${width/cols+.3}" height="${height/rows+.3}" fill="${colorFor(interpolate(lat,lon,d.points))}"/>`}
 const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}"><defs><clipPath id="india"><path d="${path.join(" ")}" fill-rule="evenodd"/></clipPath><filter id="blur"><feGaussianBlur stdDeviation="1.4"/></filter></defs><g clip-path="url(#india)" filter="url(#blur)">${cells}</g></svg>`;
 const encoded=btoa(unescape(encodeURIComponent(svg)));if(fieldLayer)map.removeLayer(fieldLayer);
 fieldLayer=L.imageOverlay(`data:image/svg+xml;base64,${encoded}`,[[minLat,minLon],[maxLat,maxLon]],{opacity:.84,interactive:false}).addTo(map);fieldLayer.bringToBack()
}
async function loadField(){try{const [grid,boundary]=await Promise.all([fetch(apiUrl("/api/wbgt-grid")),fetch("india-boundary.geojson")]),d=await grid.json(),shape=await boundary.json();if(!grid.ok||!boundary.ok||!d.points.length)throw Error(d.error||"No valid observations");renderField(d,shape);fieldStatus.textContent=`Live spatial analysis · ${d.points.length} calculated observations`;if(d.updated_at)updated.textContent=`Analysis updated ${istTime(d.updated_at,{hour:"2-digit",minute:"2-digit",second:"2-digit"})}`}catch(e){fieldStatus.textContent=`Spatial analysis unavailable: ${e.message}`;fieldStatus.classList.add("error")}}
const cityAliases={bangalore:"Bengaluru",bombay:"Mumbai",calcutta:"Kolkata",madras:"Chennai",cochin:"Kochi",trivandrum:"Thiruvananthapuram",poona:"Pune",gurgaon:"Gurugram",baroda:"Vadodara",benares:"Varanasi",banaras:"Varanasi",mysore:"Mysuru"};
function renderSearchResults(results){searchResults.replaceChildren();if(!results||!results.length){searchResults.innerHTML="<p>City not found in India.</p>";return}const seen=new Set();results.forEach(p=>{const key=`${p.name}_${Number(p.lat).toFixed(2)}_${Number(p.lon).toFixed(2)}`;if(seen.has(key))return;seen.add(key);const b=document.createElement("button");b.type="button";b.textContent=`${p.name}${p.admin1?`, ${p.admin1}`:""}`;b.onclick=()=>{citySearch.value=p.name;searchResults.replaceChildren();const c={name:p.name,lat:p.lat,lon:p.lon};if(!markers.has(c.name)){const m=L.marker([c.lat,c.lon],{icon:markerIcon(),risk:null}).addTo(map);m.on("click",()=>selectCity(c));markers.set(c.name,m)}selectCity(c)};searchResults.append(b)})}
cities.forEach(c=>{const m=L.marker([c.lat,c.lon],{icon:markerIcon(),risk:null}).addTo(map).bindTooltip(c.name,{direction:"top",offset:[0,-7],opacity:.9});m.on("click",()=>selectCity(c));markers.set(c.name,m)});map.on("zoomend",()=>{const show=map.getZoom()>=6;markers.forEach(m=>show?m.openTooltip():m.closeTooltip())});let timer,searchController;citySearch.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();const b=searchResults.querySelector("button");if(b)b.click()}});citySearch.addEventListener("input",()=>{clearTimeout(timer);if(searchController)searchController.abort();const q=citySearch.value.trim();searchResults.replaceChildren();if(q.length<2)return;const qLow=q.toLowerCase(),alias=cityAliases[qLow]||q,target=alias.toLowerCase();const localMatches=cities.filter(c=>c.name.toLowerCase().includes(qLow)||c.name.toLowerCase().includes(target));if(localMatches.length)renderSearchResults(localMatches);timer=setTimeout(async()=>{searchController=new AbortController();try{const r=await fetch(apiUrl(`/api/search?q=${encodeURIComponent(q)}`),{signal:searchController.signal}),d=await r.json();if(citySearch.value.trim()!==q)return;const combined=[...localMatches];if(d.results&&d.results.length)d.results.forEach(p=>combined.push(p));renderSearchResults(combined)}catch(e){if(e.name==="AbortError")return;if(citySearch.value.trim()===q){if(localMatches.length){renderSearchResults(localMatches)}else{searchResults.replaceChildren();searchResults.innerHTML=`<p>${e.message==="Failed to fetch"?"Unable to reach the local WBGT service. Start dashboard_server.py and try again.":e.message}</p>`}}}},200)});loadField();selectCity(cities[0],false);setInterval(()=>selected&&selectCity(selected,false),300000);

