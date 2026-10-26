(() => {
  const tabs = [...document.querySelectorAll('.view-tab')];
  const panels = {national: document.getElementById('nationalView'), personal: document.getElementById('personalView'), comparison: document.getElementById('comparisonView')};
  const form = document.getElementById('personalAdvisorForm');
  const cityInput = document.getElementById('personalCity');
  const situationSelect = document.getElementById('personalSituation');
  const results = document.getElementById('personalResults');
  const status = document.getElementById('personalStatus');
  const submit = document.getElementById('personalAnalyzeBtn');
  const suggestions = document.getElementById('personalSearchResults');
  let selectedLocation = null;
  let searchTimer;
  let searchController;
  let requestController;
  let requestVersion = 0;
  let latestRequest = null;

  function invalidatePendingAnalysis() {
    const pending = submit.disabled;
    const reportVisible = !results.classList.contains('hidden');
    if (!pending && (!latestRequest || !reportVisible)) return;
    if (pending) {
      requestVersion++;
      if (requestController) requestController.abort();
      submit.disabled = false;
      submit.textContent = 'Analyze My Heat Risk';
    }
    latestRequest = null;
    results.classList.add('hidden');
    setStatus('Your inputs changed. Submit again to analyze the updated selection.', 'info');
  }

  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const finite = value => value === null || value === undefined || value === '' ? null : Number.isFinite(Number(value)) ? Number(value) : null;
  const celsius = value => finite(value) === null ? 'Unavailable' : `${finite(value).toFixed(1)}°C`;
  const numeric = (value, digits = 2) => finite(value) === null ? 'Unavailable' : finite(value).toFixed(digits);

  function setView(name) {
    tabs.forEach((tab, index) => {
      const active = tab.dataset.view === name;
      tab.classList.toggle('active', active);
      tab.setAttribute('aria-pressed', String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    Object.entries(panels).forEach(([key, panel]) => panel.classList.toggle('active', key === name));
    if (name === 'national' && window.heatShieldResizeMap) requestAnimationFrame(() => window.heatShieldResizeMap());
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => setView(tab.dataset.view));
    tab.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
      tabs[next].focus();
      setView(tabs[next].dataset.view);
    });
  });

  function setStatus(message, kind = 'info', retry = false) {
    status.replaceChildren();
    status.className = `status-banner ${kind}`;
    const text = document.createElement('span');
    text.textContent = message;
    status.append(text);
    if (retry && latestRequest) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'retry-btn';
      button.textContent = 'Retry';
      button.addEventListener('click', () => runAnalysis(latestRequest));
      status.append(button);
    }
  }

  function showSuggestions(items, query) {
    suggestions.replaceChildren();
    if (!items.length) {
      const empty = document.createElement('div');
      empty.className = 'suggestion-empty';
      empty.textContent = 'No matching Indian locations found.';
      suggestions.append(empty);
      cityInput.setAttribute('aria-expanded', 'true');
      return;
    }
    items.forEach(item => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'search-option';
      button.textContent = [item.name, item.admin1].filter(Boolean).join(', ');
      button.setAttribute('role', 'option');
      button.addEventListener('click', () => {
        selectedLocation = {city: item.name, lat: item.lat, lon: item.lon, timezone: item.timezone || 'Asia/Kolkata', label: button.textContent};
        cityInput.value = button.textContent;
        clearSuggestions();
      });
      suggestions.append(button);
    });
    cityInput.setAttribute('aria-expanded', 'true');
  }

  function clearSuggestions() {
    suggestions.replaceChildren();
    cityInput.setAttribute('aria-expanded', 'false');
  }

  cityInput.addEventListener('input', () => {
    invalidatePendingAnalysis();
    selectedLocation = null;
    clearTimeout(searchTimer);
    if (searchController) searchController.abort();
    const query = cityInput.value.trim();
    clearSuggestions();
    if (query.length < 2) return;
    searchTimer = setTimeout(async () => {
      const controller = new AbortController();
      searchController = controller;
      try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`, {signal: controller.signal});
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || 'Search is unavailable.');
        if (cityInput.value.trim() !== query) return;
        showSuggestions(Array.isArray(payload.results) ? payload.results.slice(0, 7) : [], query);
      } catch (error) {
        if (error.name !== 'AbortError' && cityInput.value.trim() === query) {
          const message = document.createElement('div');
          message.className = 'suggestion-empty';
          message.textContent = 'Location suggestions are unavailable. You can still enter a city name.';
          suggestions.replaceChildren(message);
          cityInput.setAttribute('aria-expanded', 'true');
        }
      }
    }, 250);
  });

  situationSelect.addEventListener('change', invalidatePendingAnalysis);

  cityInput.addEventListener('keydown', event => {
    if (event.key === 'ArrowDown') {
      const first = suggestions.querySelector('.search-option');
      if (first) { event.preventDefault(); first.focus(); }
    } else if (event.key === 'Escape') {
      clearSuggestions();
    }
  });

  document.addEventListener('click', event => {
    if (!event.target.closest('.search-stack')) clearSuggestions();
  });

  const levels = [[27.8,'Moderate','#10b981'],[29.5,'High','#f59e0b'],[31.1,'Very high','#ea580c'],[32.2,'Extreme','#dc2626']];
  function category(value) {
    const n = finite(value);
    if (n === null) return 'Unavailable';
    if (n < 27.8) return 'Low';
    if (n < 29.5) return 'Moderate';
    if (n < 31.1) return 'High';
    if (n < 32.2) return 'Very high';
    return 'Extreme';
  }
  function categoryColor(value) {
    const name = category(value);
    return ({Low:'#0284c7',Moderate:'#10b981',High:'#f59e0b','Very high':'#ea580c',Extreme:'#dc2626'})[name] || '#64748b';
  }
  function categoryMeaning(value) {
    const name = category(value);
    if (name === 'Low') return 'This falls in the project’s lower environmental heat-stress tier.';
    if (name === 'Moderate') return 'This tier represents increased environmental heat stress, especially during exertion.';
    if (name === 'High') return 'This tier represents high environmental heat stress; exposure reduction and precautions are relevant.';
    if (name === 'Very high' || name === 'Extreme') return 'This tier represents very high environmental heat stress; prioritize reducing exposure and follow the situation-specific precautions below.';
    return 'A category cannot be assigned because WBGT is unavailable.';
  }
  function dateFor(value, timezone, options) {
    if (!value) return 'Time unavailable';
    const d = new Date(value);
    if (!Number.isFinite(d.getTime())) return String(value);
    try { return new Intl.DateTimeFormat('en-IN', {...options, timeZone: timezone || 'UTC'}).format(d); }
    catch { return new Intl.DateTimeFormat('en-IN', {...options, timeZone: 'UTC'}).format(d); }
  }

  function localDateKey(value, timezone) {
    if (!value) return '';
    const date = new Date(value);
    if (!Number.isFinite(date.getTime())) return '';
    let parts;
    try { parts = new Intl.DateTimeFormat('en-CA', {timeZone: timezone || 'UTC', year:'numeric', month:'2-digit', day:'2-digit'}).formatToParts(date); }
    catch { parts = new Intl.DateTimeFormat('en-CA', {timeZone:'UTC', year:'numeric', month:'2-digit', day:'2-digit'}).formatToParts(date); }
    const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
    return `${values.year}-${values.month}-${values.day}`;
  }

  function renderTimeline(hourly, timezone, coverageDays = []) {
    const days = new Map();
    coverageDays.forEach(day => days.set(day.date, []));
    hourly.forEach(item => {
      const localDay = localDateKey(item.time, timezone);
      if (!days.has(localDay)) days.set(localDay, []);
      days.get(localDay).push(item);
    });
    if (!days.size) return '<p class="empty-state">Hourly WBGT is unavailable for this forecast.</p>';
    const dayEntries = [...days.entries()];
    const selectedDay = dayEntries[0][0], selectedItems = dayEntries[0][1];
    const coverageFor = day => coverageDays.find(item => item.date === day);
    const buttons = dayEntries.map(([day, items], index) => {
      const coverage = coverageFor(day);
      const valid = coverage?.validHours ?? items.filter(item => finite(item.wbgt) !== null).length;
      const expected = coverage?.expectedHours ?? 24;
      const dateLabel = dateFor(items[0]?.time || `${day}T12:00:00Z`, timezone, {weekday:'short', day:'numeric', month:'short'});
      return `<button type="button" class="day-tab${index === 0 ? ' active' : ''}${coverage && !coverage.complete ? ' incomplete' : ''}" data-day-index="${index}" aria-pressed="${index === 0}">${escapeHtml(dateLabel)} <small>${valid}/${expected}h</small></button>`;
    }).join('');
    const coverage = coverageFor(selectedDay);
    const valid = coverage?.validHours ?? selectedItems.filter(item => finite(item.wbgt) !== null).length;
    const expected = coverage?.expectedHours ?? 24;
    const statusText = coverage && !coverage.complete
      ? `Incomplete forecast data: ${valid} valid WBGT hours of ${expected} expected for this local date. No missing values are filled.`
      : `${valid} valid WBGT hours for this local forecast date.`;
    const chart = renderDayChart(selectedItems, timezone);
    const tableRows = renderHourlyRows(selectedItems, timezone);
    return `<section class="timeline-panel"><div class="section-heading"><div><h3>Hourly WBGT forecast</h3><p>Environmental heat stress forecast, calculated using the project’s Liljegren model.</p></div></div><div class="severity-legend" aria-label="WBGT category thresholds"><span><i style="--swatch:#0284c7"></i>Low &lt; 27.8°C</span><span><i style="--swatch:#10b981"></i>Moderate 27.8–29.4°C</span><span><i style="--swatch:#f59e0b"></i>High 29.5–31.0°C</span><span><i style="--swatch:#ea580c"></i>Very high 31.1–32.1°C</span><span><i style="--swatch:#dc2626"></i>Extreme ≥ 32.2°C</span></div><div class="day-tabs" role="group" aria-label="Choose forecast day">${buttons}</div><p class="forecast-data-status${coverage && !coverage.complete ? ' incomplete' : ''}" id="personalDayStatus">${escapeHtml(statusText)}</p><div id="personalChart" class="chart-wrap">${chart}</div><p class="chart-caption">Bars show WBGT, not air temperature. The selected day’s peak WBGT hour is outlined. Lower WBGT periods are comparative and are not guaranteed safe conditions.</p><details class="hourly-details"><summary>View hourly values for selected day</summary><div class="table-scroll"><table><thead><tr><th>Local forecast time</th><th>WBGT</th><th>Stress category</th><th>Air temperature</th></tr></thead><tbody id="personalHourlyRows">${tableRows}</tbody></table></div></details></section>`;
  }

  function renderHourlyRows(items, timezone) {
    return items.map(item => `<tr><td>${escapeHtml(dateFor(item.time, timezone, {weekday:'short', day:'numeric', month:'short', hour:'numeric', minute:'2-digit'}))}</td><td>${escapeHtml(celsius(item.wbgt))}</td><td>${escapeHtml(category(item.wbgt))}</td><td>${escapeHtml(celsius(item.temperature_c))}</td></tr>`).join('');
  }

  function renderDayChart(items, timezone) {
    const valid = items.filter(item => finite(item.wbgt) !== null);
    if (!valid.length) return '<p class="empty-state">No calculated hourly WBGT values are available for this day.</p>';
    const values = valid.map(item => finite(item.wbgt));
    const min = Math.min(24, Math.floor(Math.min(...values) - 1));
    const max = Math.max(34, Math.ceil(Math.max(...values) + 1));
    const width = Math.max(720, valid.length * 36), height = 260, baseline = 220, top = 25, plotLeft = 52, plotWidth = width - plotLeft - 8;
    const barWidth = Math.max(8, Math.min(22, plotWidth / valid.length * .56));
    const peak = Math.max(...values);
    const bars = valid.map((item, index) => {
      const value = finite(item.wbgt), x = plotLeft + index * plotWidth / valid.length + (plotWidth / valid.length - barWidth) / 2;
      const barHeight = Math.max(2, (value - min) / (max - min) * (baseline - top));
      const y = baseline - barHeight;
      const local = dateFor(item.time, timezone, {hour:'numeric', minute:'2-digit'});
      const hot = value === peak;
      return `<g><title>${escapeHtml(local)} · WBGT ${value.toFixed(1)}°C · ${escapeHtml(category(value))}${finite(item.temperature_c) === null ? '' : ` · air ${finite(item.temperature_c).toFixed(1)}°C`}${hot ? ' · selected-day peak' : ''}</title><rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${barHeight.toFixed(1)}" rx="3" fill="${categoryColor(value)}"${hot ? ' stroke="currentColor" stroke-width="2.5"' : ''}/>${index % 3 === 0 || index === valid.length - 1 ? `<text x="${(x + barWidth/2).toFixed(1)}" y="242" text-anchor="middle">${escapeHtml(dateFor(item.time, timezone, {hour:'numeric'}))}</text>` : ''}</g>`;
    }).join('');
    const thresholds = levels.map(([value, label]) => {
      const y = baseline - (value - min) / (max - min) * (baseline - top);
      return y > top && y < baseline ? `<g><line x1="${plotLeft}" x2="${width}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}" stroke="currentColor" stroke-opacity=".2" stroke-dasharray="4 5"/><text x="${plotLeft - 5}" y="${(y + 4).toFixed(1)}" text-anchor="end">${value.toFixed(1)}</text><title>${label} threshold ${value}°C WBGT</title></g>` : '';
    }).join('');
    return `<svg class="wbgt-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Hourly WBGT bars for selected day. ${valid.length} available forecast values; selected-day peak ${peak.toFixed(1)} degrees Celsius."><text x="4" y="14">WBGT °C</text>${thresholds}${bars}<line x1="${plotLeft}" x2="${width}" y1="${baseline}" y2="${baseline}" stroke="currentColor" stroke-opacity=".3"/></svg>`;
  }

  function render(data) {
    if (!data || !data.summary) throw new Error('The server returned an incomplete report.');
    const s = data.summary, location = data.location || {}, timezone = location.timezone || 'UTC';
    const peak = s.peakForecast || {}, improvement = s.improvement || {};
    const nextLower = (s.lowerPeriods || []).find(item => item.time);
    const hourly = Array.isArray(data.hourly) ? data.hourly : [];
    const daily = Array.isArray(data.forecast) ? data.forecast : [];
    const currentTime = dateFor(data.current?.time, timezone, {weekday:'short', day:'numeric', month:'short', hour:'numeric', minute:'2-digit'});
    const peakTime = dateFor(peak.time, timezone, {weekday:'short', day:'numeric', month:'short', hour:'numeric', minute:'2-digit'});
    const aiUsed = data.recommendation_engine?.ai_personalization_applied === true;
    const recommendations = Array.isArray(data.recommendations) ? data.recommendations : [];
    const dailyRows = daily.map(day => `<tr><td>${escapeHtml(dateFor(day.time, timezone, {weekday:'short', day:'numeric', month:'short'}))}</td><td>${escapeHtml(celsius(day.wbgt))}</td><td>${escapeHtml(category(day.wbgt))}</td></tr>`).join('');
    results.innerHTML = `<div class="selected-context"><div><span class="eyebrow">SELECTED LOCATION</span><strong>${escapeHtml(location.city || s.location || 'Selected location')}${location.admin1 ? `, ${escapeHtml(location.admin1)}` : ''}</strong><small>${escapeHtml(location.latitude)}, ${escapeHtml(location.longitude)} · ${escapeHtml(data.situation?.label || 'General public')}</small></div><span class="data-badge">${data.current?.converged ? 'Current calculation available' : 'Current calculation unavailable'}</span></div>
      <div class="summary-grid"><article class="metric-card current-metric"><span class="metric-label">Current WBGT estimate</span><strong>${escapeHtml(celsius(s.currentWbgt))}</strong><small>${escapeHtml(category(s.currentWbgt))} · ${escapeHtml(currentTime)}</small></article><article class="metric-card peak-metric"><span class="metric-label">Five-day peak WBGT</span><strong>${escapeHtml(celsius(peak.wbgt))}</strong><small>${escapeHtml(peakTime)}</small></article><article class="metric-card"><span class="metric-label">Overall heat-health level</span><strong>${escapeHtml(s.riskCategory || 'Unavailable')}</strong><small>Combines physical and modeled population risk context.</small></article><article class="metric-card"><span class="metric-label">Forecast trend</span><strong>${escapeHtml(s.trendLabel || 'Unavailable')}</strong><small>${escapeHtml(s.persistence || 'Persistence unavailable.')}</small></article></div>
      <section class="insight-panel"><h3>What this heat-stress category means</h3><p>WBGT estimates environmental heat stress from air temperature, humidity, wind and solar radiation. ${escapeHtml(categoryMeaning(s.currentWbgt))} It describes outdoor conditions, not body temperature or an individual illness probability.</p><p>Current conditions are a model estimate for ${escapeHtml(currentTime)}. Other values below are future forecast estimates in ${escapeHtml(timezone)} local time.</p></section>
      ${renderTimeline(hourly, timezone, data.forecastCoverage?.days || [])}
      <div class="outlook-grid"><section class="insight-panel"><h3>When conditions may ease</h3><p>${escapeHtml(improvement.message || 'The available forecast does not show a clear improvement period.')}</p>${improvement.time ? `<p><strong>Supporting forecast:</strong> ${escapeHtml(dateFor(improvement.time, timezone, {weekday:'short', day:'numeric', month:'short', hour:'numeric', minute:'2-digit'}))} · WBGT ${escapeHtml(celsius(improvement.wbgt))} (from ${escapeHtml(celsius(improvement.fromWbgt))}).</p>` : ''}${nextLower ? `<p><strong>Below the forecast peak:</strong> ${escapeHtml(dateFor(nextLower.time, timezone, {weekday:'short', day:'numeric', month:'short', hour:'numeric', minute:'2-digit'}))} · WBGT ${escapeHtml(celsius(nextLower.wbgt))}.</p>` : ''}<small>Rule: first forecast hour at least 0.8°C below current WBGT. Comparatively lower stress does not guarantee safety.</small></section><section class="insight-panel"><h3>Nighttime relief</h3><p>${escapeHtml(s.nighttimeRelief?.message || 'Nighttime forecast information is unavailable.')}</p><small>${s.nighttimeRelief?.maxWbgt == null ? 'No usable nighttime values in the returned hourly series.' : `Calculated from available hours ${escapeHtml(s.nighttimeRelief?.period || '00:00–05:59 local time')}.`}</small></section></div>
      <details class="hourly-details daily-details"><summary>Daily maximum WBGT</summary><div class="table-scroll"><table><thead><tr><th>Local forecast day</th><th>Maximum WBGT</th><th>Stress category</th></tr></thead><tbody>${dailyRows}</tbody></table></div></details>
      <details class="hourly-details"><summary>Modeled population risk context</summary><div class="table-scroll"><table><tbody><tr><th>Mortality Risk Index</th><td>${escapeHtml(numeric(data.current?.mortalityRiskIndex, 1))}/100</td></tr><tr><th>Relative risk</th><td>${escapeHtml(numeric(data.current?.relativeRisk, 4))}</td></tr><tr><th>Attributable fraction</th><td>${finite(data.current?.attributableFraction) === null ? 'Unavailable' : `${(finite(data.current.attributableFraction) * 100).toFixed(1)}%`}</td></tr></tbody></table><p class="chart-caption">These values are from a population epidemiological relationship based on a Taiwan study. They are not a personal clinical probability and are not locally calibrated to Indian health outcome data.</p></div></details>
      <section class="recommendations-panel"><div class="section-heading"><div><h3>Recommendations for your situation</h3><p>${escapeHtml(s.activityFocus || '')}</p></div><span class="data-badge">${aiUsed ? 'Gemini personalization applied' : 'Evidence-based recommendations'}</span></div>${recommendations.length ? recommendations.map(item => `<article class="recommendation-item"><span class="pill">${escapeHtml(item.category || 'Heat action')}</span><strong>${escapeHtml(item.recommendation || item.action || 'Heat-health precaution')}</strong><p>${escapeHtml(item.reason || 'Evidence-based guidance for the available forecast.')}</p><small>${escapeHtml(item.source || 'Evidence library')}${item.source_reference ? ` · ${escapeHtml(item.source_reference)}` : ''}</small></article>`).join('') : '<p class="empty-state">No recommendations are available for this situation.</p>'}</section>
      `;
    results.classList.remove('hidden');
    results.querySelectorAll('.day-tab').forEach(button => button.addEventListener('click', () => {
      const index = Number(button.dataset.dayIndex);
      results.querySelectorAll('.day-tab').forEach(tab => { const active = tab === button; tab.classList.toggle('active', active); tab.setAttribute('aria-pressed', String(active)); });
      const days = new Map();
      (data.forecastCoverage?.days || []).forEach(day => days.set(day.date, []));
      hourly.forEach(item => { const day = localDateKey(item.time, timezone); if (!days.has(day)) days.set(day, []); days.get(day).push(item); });
      const entries = [...days.values()];
      const dayKeys = [...days.keys()];
      const dayName = dayKeys[index], dayItems = entries[index] || [];
      results.querySelector('#personalChart').innerHTML = renderDayChart(entries[index] || [], timezone);
      results.querySelector('#personalHourlyRows').innerHTML = renderHourlyRows(dayItems, timezone);
      const coverage = (data.forecastCoverage?.days || []).find(item => item.date === dayName);
      const validHours = coverage?.validHours ?? dayItems.filter(item => finite(item.wbgt) !== null).length;
      const expectedHours = coverage?.expectedHours ?? 24;
      const dayStatus = results.querySelector('#personalDayStatus');
      dayStatus.classList.toggle('incomplete', Boolean(coverage && !coverage.complete));
      dayStatus.textContent = coverage && !coverage.complete
        ? `Incomplete forecast data: ${validHours} valid WBGT hours of ${expectedHours} expected for this local date. No missing values are filled.`
        : `${validHours} valid WBGT hours for this local forecast date.`;
    }));
  }

  async function runAnalysis(request) {
    if (submit.disabled) return;
    const version = ++requestVersion;
    if (requestController) requestController.abort();
    requestController = new AbortController();
    submit.disabled = true;
    submit.textContent = 'Analyzing forecast…';
    results.classList.add('hidden');
    setStatus('Resolving location and calculating the five-day WBGT forecast…', 'loading');
    try {
      const response = await fetch('/api/personal-heat-risk', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(request), signal:requestController.signal});
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Unable to calculate the heat-risk report.');
      if (version !== requestVersion) return;
      render(payload);
      const aiUsed = payload.recommendation_engine?.ai_personalization_applied === true;
      setStatus(aiUsed ? 'Analysis complete. Recommendations were personalized using the approved evidence set.' : 'Analysis complete. Recommendations use the project’s deterministic evidence library.', 'success');
    } catch (error) {
      if (error.name === 'AbortError' || version !== requestVersion) return;
      setStatus(error.message || 'The heat-risk analysis could not be completed.', 'error', true);
      results.classList.remove('hidden');
      results.innerHTML = `<div class="empty-state">${escapeHtml(error.message || 'The request failed.')} Choose Retry to request the forecast again.</div>`;
    } finally {
      if (version === requestVersion) {
        submit.disabled = false;
        submit.textContent = 'Analyze My Heat Risk';
      }
    }
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    const city = cityInput.value.trim();
    if (!city) {
      setStatus('Enter a city or choose a location from the suggestions.', 'error');
      cityInput.focus();
      return;
    }
    const request = {city, situation:situationSelect.value};
    request.audience = situationSelect.value === 'outdoor-worker' ? 'OUTDOOR_WORKER' : 'PUBLIC';
    if (selectedLocation && cityInput.value === selectedLocation.label) {
      request.lat = selectedLocation.lat;
      request.lon = selectedLocation.lon;
      request.city = selectedLocation.city;
      request.timezone = selectedLocation.timezone;
    }
    latestRequest = request;
    runAnalysis(request);
  });
})();
