(() => {
  const form = document.getElementById('cityCompareForm');
  const inputA = document.getElementById('compareCityA');
  const inputB = document.getElementById('compareCityB');
  const inputs = [inputA, inputB];
  const lists = [document.getElementById('compareSuggestionsA'), document.getElementById('compareSuggestionsB')];
  const clearButtons = [...document.querySelectorAll('.compare-clear')];
  const submit = document.getElementById('compareCitiesButton');
  const status = document.getElementById('comparisonStatus');
  const results = document.getElementById('comparisonResults');
  const cityNames = [null, null];
  const timers = [null, null];
  const controllers = [null, null];
  let requestController = null;
  let requestVersion = 0;

  function invalidateComparison() {
    const pending = submit.disabled;
    const visible = !results.classList.contains('hidden');
    if (!pending && !visible) return;
    if (pending) {
      requestVersion++;
      if (requestController) requestController.abort();
      submit.disabled = false;
      submit.textContent = 'Compare Cities';
    }
    results.classList.add('hidden');
    banner('City selection changed. Compare again to refresh the report.', 'info');
  }

  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const n = value => value === null || value === undefined || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);
  const fmt = (value, digits = 1, suffix = '') => n(value) === null ? 'Unavailable' : `${n(value).toFixed(digits)}${suffix}`;
  const colors = ['#38bdf8', '#fb923c'];

  function banner(message, kind = 'info') {
    status.className = `status-banner ${kind}`;
    status.textContent = message;
  }

  function clearList(index) {
    lists[index].replaceChildren();
    inputs[index].setAttribute('aria-expanded', 'false');
  }

  function syncClearButton(index) {
    if (clearButtons[index]) clearButtons[index].hidden = !inputs[index].value;
  }

  function selectCity(index, item) {
    cityNames[index] = item.name;
    inputs[index].value = [item.name, item.admin1].filter(Boolean).join(', ');
    syncClearButton(index);
    clearList(index);
    if (!submit.disabled && !results.classList.contains('hidden')) {
      results.classList.add('hidden');
      banner('City selection changed. Compare again to refresh the report.', 'info');
    }
  }

  async function search(index) {
    const query = inputs[index].value.trim();
    if (controllers[index]) controllers[index].abort();
    clearList(index);
    if (query.length < 2) return;
    const controller = new AbortController();
    controllers[index] = controller;
    try {
      const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`, {signal: controller.signal});
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'City suggestions are unavailable.');
      if (inputs[index].value.trim() !== query) return;
      const matches = Array.isArray(payload.results) ? payload.results.slice(0, 7) : [];
      if (!matches.length) {
        const empty = document.createElement('div');
        empty.className = 'suggestion-empty';
        empty.textContent = 'No matching Indian cities found.';
        lists[index].append(empty);
      }
      matches.forEach(item => {
        const option = document.createElement('button');
        option.type = 'button';
        option.className = 'search-option';
        option.setAttribute('role', 'option');
        option.innerHTML = `<span class="search-option-name">${esc(item.name)}</span><span class="search-option-meta">${esc([item.admin1, item.country].filter(Boolean).join(', ') || 'India')}</span>`;
        option.setAttribute('aria-label', [item.name, item.admin1, item.country].filter(Boolean).join(', '));
        option.addEventListener('click', () => selectCity(index, item));
        option.addEventListener('keydown', event => {
          const options = [...lists[index].querySelectorAll('.search-option')];
          const current = options.indexOf(option);
          if (event.key === 'ArrowDown') { event.preventDefault(); (options[current + 1] || options[0])?.focus(); }
          if (event.key === 'ArrowUp') { event.preventDefault(); current > 0 ? options[current - 1].focus() : inputs[index].focus(); }
          if (event.key === 'Escape') { clearList(index); inputs[index].focus(); }
        });
        lists[index].append(option);
      });
      inputs[index].setAttribute('aria-expanded', 'true');
    } catch (error) {
      if (error.name !== 'AbortError') {
        const message = document.createElement('div');
        message.className = 'suggestion-empty';
        message.textContent = 'City search is unavailable. Enter a city and retry.';
        lists[index].replaceChildren(message);
        inputs[index].setAttribute('aria-expanded', 'true');
      }
    }
  }

  inputs.forEach((input, index) => {
    input.addEventListener('input', () => {
      cityNames[index] = null;
      syncClearButton(index);
      invalidateComparison();
      clearTimeout(timers[index]);
      clearList(index);
      if (!results.classList.contains('hidden')) {
        results.classList.add('hidden');
        banner('City selection changed. Compare again to refresh the report.', 'info');
      }
      timers[index] = setTimeout(() => search(index), 220);
    });
    input.addEventListener('keydown', event => {
      if (event.key === 'ArrowDown') {
        const first = lists[index].querySelector('.search-option');
        if (first) { event.preventDefault(); first.focus(); }
      }
      if (event.key === 'Escape') clearList(index);
    });
  });
  clearButtons.forEach((button, index) => button.addEventListener('click', () => {
    inputs[index].value = '';
    cityNames[index] = null;
    syncClearButton(index);
    clearList(index);
    invalidateComparison();
    inputs[index].focus();
    inputs[index].dispatchEvent(new Event('input', {bubbles:true}));
  }));
  document.addEventListener('click', event => inputs.forEach((input, index) => {
    if (!event.target.closest(`#${input.id}`)?.parentElement?.contains(event.target)) clearList(index);
  }));

  function localTime(value, timezone, options = {}) {
    if (!value) return 'Unavailable';
    const date = new Date(value);
    if (!Number.isFinite(date.getTime())) return String(value);
    try { return new Intl.DateTimeFormat('en-IN', {timeZone: timezone || 'UTC', ...options}).format(date); }
    catch { return new Intl.DateTimeFormat('en-IN', {timeZone:'UTC', ...options}).format(date); }
  }

  function peakCard(city, index, otherPeak) {
    const peak = city.peak;
    const difference = peak && otherPeak ? Number(peak.wbgt) - Number(otherPeak.wbgt) : null;
    const night = city.nighttime || {};
    const change = city.change || {};
    const streak = city.elevatedRun || {};
    const location = city.location || {};
    const peakLabel = peak ? `${localTime(peak.time, city.timezone, {weekday:'short', day:'numeric', month:'short', hour:'numeric', minute:'2-digit'})} ${city.timezone}` : 'Peak unavailable';
    const nightDetails = night.minimum ? `${fmt(night.minimum.minimumWbgt, 1, '°C')} · ${localTime(night.minimum.time, city.timezone, {weekday:'short', day:'numeric', month:'short', hour:'numeric'})}${night.minimum.reductionC === undefined ? '' : ` · ${fmt(night.minimum.reductionC, 1, '°C')} below ${fmt(night.minimum.daytimePeakWbgt, 1, '°C')} daytime peak at ${localTime(night.minimum.daytimePeakTime, city.timezone, {hour:'numeric'})}`}` : 'Unavailable';
    const changeDetails = change.deltaC === null ? 'Unavailable' : `${Number(change.deltaC) > 0 ? '+' : ''}${Number(change.deltaC).toFixed(1)}°C · ${change.trend}${change.first ? ` · ${localTime(change.first.time, city.timezone, {day:'numeric', month:'short', hour:'numeric'})} to ${localTime(change.last.time, city.timezone, {day:'numeric', month:'short', hour:'numeric'})}` : ''}`;
    return `<article class="metric-card compare-city-card"><div class="compare-city-title"><span class="city-series-dot" style="--city-series:${colors[index]}"></span><h3>${esc(location.city || `City ${index + 1}`)}</h3></div><span class="metric-label">Peak WBGT · ${esc(peak?.category || 'Unavailable')}</span><strong>${esc(fmt(peak?.wbgt, 1, '°C'))}</strong><small>${esc(peakLabel)}</small><dl class="compare-mini-metrics"><div><dt>High-stress hours</dt><dd>${esc(city.highStress?.hours ?? 'Unavailable')} / ${esc(city.highStress?.validHours ?? 0)} valid hours</dd></div><div><dt>Consecutive elevated days</dt><dd>${esc(streak.days ?? 'Unavailable')}${streak.startDate ? ` · ${esc(streak.startDate)} to ${esc(streak.endDate)}` : ''}</dd></div><div><dt>Lowest overnight WBGT</dt><dd>${esc(nightDetails)}</dd></div><div><dt>First-to-last WBGT change</dt><dd>${esc(changeDetails)}</dd></div><div><dt>Peak difference vs other city</dt><dd>${esc(difference === null ? 'Unavailable' : `${difference > 0 ? '+' : ''}${difference.toFixed(1)}°C`)}</dd></div><div><dt>Forecast coverage</dt><dd>${esc(city.coverage?.availableHours ?? 0)} valid / ${esc(city.coverage?.expectedHours ?? 0)} expected hours</dd></div></dl>${city.coverage?.incompleteDays?.length ? `<p class="forecast-data-status incomplete">Incomplete forecast dates: ${esc(city.coverage.incompleteDays.join(', '))}. Metrics use only valid calculated observations.</p>` : ''}</article>`;
  }

  function metricsTable(cities) {
    const rows = cities.map(city => {
      const night = city.nighttime?.minimum;
      const change = city.change || {};
      return `<tr><th>${esc(city.location?.city)}</th><td>${esc(fmt(city.peak?.wbgt, 1, '°C'))} · ${esc(city.peak?.category || 'Unavailable')}</td><td>${esc(city.highStress?.hours ?? 'Unavailable')} / ${esc(city.highStress?.validHours ?? 0)} valid</td><td>${esc(city.elevatedRun?.days ?? 'Unavailable')}</td><td>${esc(night ? `${fmt(night.minimumWbgt, 1, '°C')} at ${localTime(night.time, city.timezone, {day:'numeric', month:'short', hour:'numeric'})}` : 'Unavailable')}</td><td>${esc(change.deltaC === null ? 'Unavailable' : `${Number(change.deltaC) > 0 ? '+' : ''}${Number(change.deltaC).toFixed(1)}°C · ${change.trend}`)}</td></tr>`;
    }).join('');
    return `<div class="table-scroll"><table><thead><tr><th>City</th><th>Peak WBGT</th><th>High-stress hours</th><th>Longest elevated run</th><th>Lowest overnight WBGT</th><th>Forecast WBGT change</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function hourlyChart(cities) {
    const allTimes = [...new Set(cities.flatMap(city => city.hourly.map(item => item.time)).filter(Boolean))].sort();
    const points = cities.map(city => new Map(city.hourly.filter(item => item.time && n(item.wbgt) !== null).map(item => [item.time, n(item.wbgt)])));
    if (!allTimes.length || points.every(map => !map.size)) return '<p class="empty-state">No hourly WBGT values are available for a direct comparison.</p>';
    const values = points.flatMap(map => [...map.values()]);
    const min = Math.floor(Math.min(...values) - 1), max = Math.ceil(Math.max(...values) + 1);
    const width = Math.max(850, allTimes.length * 8), height = 320, left = 54, right = 16, top = 24, bottom = 270;
    const plotWidth = width - left - right;
    const x = index => left + (allTimes.length < 2 ? plotWidth / 2 : index / (allTimes.length - 1) * plotWidth);
    const y = value => bottom - (value - min) / Math.max(1, max - min) * (bottom - top);
    const grid = Array.from({length:5}, (_, index) => {
      const value = min + (max - min) * index / 4, yy = y(value);
      return `<g><line x1="${left}" x2="${width-right}" y1="${yy.toFixed(1)}" y2="${yy.toFixed(1)}" stroke="currentColor" stroke-opacity=".16"/><text x="${left-8}" y="${(yy+4).toFixed(1)}" text-anchor="end">${value.toFixed(1)}</text></g>`;
    }).join('');
    const series = cities.map((city, cityIndex) => {
      const map = points[cityIndex], segments = [];
      for (let i = 1; i < allTimes.length; i++) {
        const a = map.get(allTimes[i-1]), b = map.get(allTimes[i]);
        if (a !== undefined && b !== undefined) segments.push(`<line x1="${x(i-1).toFixed(1)}" y1="${y(a).toFixed(1)}" x2="${x(i).toFixed(1)}" y2="${y(b).toFixed(1)}" stroke="${colors[cityIndex]}" stroke-width="2.5"/>`);
      }
      const markers = allTimes.map((time, i) => {
        const value = map.get(time);
        if (value === undefined || i % 3 !== 0 && i !== allTimes.length - 1) return '';
        const local = localTime(time, city.timezone, {weekday:'short', day:'numeric', month:'short', hour:'numeric', minute:'2-digit'});
        return `<circle cx="${x(i).toFixed(1)}" cy="${y(value).toFixed(1)}" r="3.5" fill="${colors[cityIndex]}"><title>${esc(city.location?.city)} · ${esc(local)} local · ${esc(time)} UTC · WBGT ${value.toFixed(1)}°C</title></circle>`;
      }).join('');
      return segments.join('') + markers;
    }).join('');
    const xLabels = [0, Math.floor((allTimes.length - 1) / 2), allTimes.length - 1].map(index => `<text x="${x(index).toFixed(1)}" y="298" text-anchor="middle">${esc(localTime(allTimes[index], 'UTC', {day:'numeric', month:'short', hour:'numeric'}))} UTC</text>`).join('');
    const legend = cities.map((city, index) => `<span><i style="--city-series:${colors[index]}"></i>${esc(city.location?.city)} · ${esc(city.timezone)}</span>`).join('');
    return `<div class="severity-legend compare-legend">${legend}</div><div class="chart-wrap"><svg class="comparison-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Hourly WBGT city comparison aligned by absolute UTC timestamp">${grid}<text x="8" y="15">WBGT °C</text>${series}${xLabels}</svg></div>`;
  }

  function dailyTable(cities) {
    const dates = [...new Set(cities.flatMap(city => city.daily.map(day => day.date)))].sort();
    if (!dates.length) return '<p class="empty-state">No daily peak data is available.</p>';
    const headers = cities.map(city => `<th>${esc(city.location?.city)}</th>`).join('');
    const rows = dates.map(date => `<tr><th>${esc(date)}</th>${cities.map(city => {
      const day = city.daily.find(item => item.date === date);
      return `<td>${day ? `${esc(fmt(day.wbgt, 1, '°C'))} · ${esc(city.coverage?.days?.find(item => item.date === date)?.complete ? 'complete' : 'incomplete')}` : 'Unavailable'}</td>`;
    }).join('')}</tr>`).join('');
    return `<div class="table-scroll"><table><thead><tr><th>Local forecast date</th>${headers}</tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function dailyPeakChart(cities) {
    const dates = [...new Set(cities.flatMap(city => city.daily.map(day => day.date)))].sort();
    const values = cities.flatMap(city => city.daily.map(day => n(day.wbgt)).filter(value => value !== null));
    if (dates.length < 2 || !values.length) return '';
    const min = Math.floor(Math.min(...values) - 1), max = Math.ceil(Math.max(...values) + 1);
    const width = 850, height = 260, left = 52, right = 16, top = 24, bottom = 210, plotWidth = width-left-right;
    const x = index => left + index / (dates.length-1) * plotWidth;
    const y = value => bottom - (value-min) / Math.max(1, max-min) * (bottom-top);
    const grid = Array.from({length:5}, (_, i) => {
      const value = min + (max-min) * i/4, yy=y(value);
      return `<g><line x1="${left}" x2="${width-right}" y1="${yy.toFixed(1)}" y2="${yy.toFixed(1)}" stroke="currentColor" stroke-opacity=".15"/><text x="${left-8}" y="${(yy+4).toFixed(1)}" text-anchor="end">${value.toFixed(1)}</text></g>`;
    }).join('');
    const lines = cities.map((city, cityIndex) => {
      const byDate = new Map(city.daily.map(day => [day.date, day]));
      const segments = [], markers = [];
      for (let i=0; i<dates.length; i++) {
        const day = byDate.get(dates[i]), value = n(day?.wbgt);
        if (value === null) continue;
        markers.push(`<circle cx="${x(i).toFixed(1)}" cy="${y(value).toFixed(1)}" r="4" fill="${colors[cityIndex]}"><title>${esc(city.location?.city)} · ${esc(dates[i])} · peak ${value.toFixed(1)}°C WBGT · ${esc(day?.complete ? 'complete day' : 'incomplete day')}</title></circle>`);
        if (i > 0) {
          const previous = n(byDate.get(dates[i-1])?.wbgt);
          if (previous !== null) segments.push(`<line x1="${x(i-1).toFixed(1)}" y1="${y(previous).toFixed(1)}" x2="${x(i).toFixed(1)}" y2="${y(value).toFixed(1)}" stroke="${colors[cityIndex]}" stroke-width="2.5"/>`);
        }
      }
      return segments.join('') + markers.join('');
    }).join('');
    const labels = dates.map((date, index) => `<text x="${x(index).toFixed(1)}" y="236" text-anchor="middle">${esc(date.slice(5))}</text>`).join('');
    return `<div class="chart-wrap"><svg class="comparison-chart daily-peak-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Daily maximum WBGT comparison for five local forecast dates">${grid}<text x="8" y="15">Daily peak WBGT °C</text>${lines}${labels}</svg></div>`;
  }

  function render(payload) {
    const cities = payload.cities || [];
    if (cities.length !== 2) throw new Error('The server returned an incomplete city comparison.');
    results.innerHTML = `<div class="summary-grid compare-city-grid">${cities.map((city, index) => peakCard(city, index, cities[1-index].peak)).join('')}</div><section class="timeline-panel"><div class="section-heading"><div><h3>Metric comparison</h3><p>Each row summarizes valid values for one city.</p></div></div>${metricsTable(cities)}</section><section class="insight-panel"><h3>Comparison at a glance</h3><ul class="comparison-interpretation">${(payload.interpretation || []).map(item => `<li>${esc(item)}</li>`).join('')}</ul></section><section class="timeline-panel"><div class="section-heading"><div><h3>Hourly WBGT comparison</h3><p>Series are aligned to absolute UTC timestamps; tooltips show each city’s local time and UTC time.</p></div></div>${hourlyChart(cities)}<p class="chart-caption">Only valid WBGT values are plotted. Gaps remain where an hourly result is unavailable.</p></section><section class="timeline-panel"><div class="section-heading"><div><h3>Daily peak WBGT comparison</h3><p>Daily maxima use the same five local forecast dates for each city.</p></div></div><div class="severity-legend compare-legend">${cities.map((city, i) => `<span><i style="--city-series:${colors[i]}"></i>${esc(city.location?.city)}</span>`).join('')}</div>${dailyPeakChart(cities)}${dailyTable(cities)}</section><details class="hourly-details"><summary>Comparison definitions and data coverage</summary><div class="insight-panel compact"><p>High-stress hours count WBGT ≥ ${esc(payload.methodology?.highStressThresholdWbgt)}°C (High or above). Elevated-day runs count complete local days whose maximum WBGT is ≥ ${esc(payload.methodology?.elevatedDayThresholdWbgt)}°C; incomplete days interrupt the run.</p><p>Overnight window: ${esc(payload.methodology?.nighttimeWindow)} WBGT change is not air-temperature change. MRI is a modeled population measure based on a Taiwan study and is not a personal clinical probability.</p><p>WBGT uses the existing Liljegren physical model. Source: Open-Meteo forecast. Local timestamp labels are shown alongside UTC alignment in the hourly chart.</p></div></details>`;
    results.classList.remove('hidden');
  }

  async function compare(cities) {
    if (submit.disabled) return;
    const version = ++requestVersion;
    if (requestController) requestController.abort();
    requestController = new AbortController();
    submit.disabled = true;
    submit.textContent = 'Comparing forecasts…';
    results.classList.add('hidden');
    banner('Resolving both cities and calculating comparable WBGT forecasts…', 'loading');
    try {
      const response = await fetch('/api/city-comparison', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({cities}), signal:requestController.signal});
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'The city comparison could not be calculated.');
      if (version !== requestVersion) return;
      render(payload);
      banner('Comparison ready. Values use valid calculated forecast observations.', 'success');
    } catch (error) {
      if (error.name === 'AbortError' || version !== requestVersion) return;
      banner(error.message || 'City forecasts are temporarily unavailable. Please retry.', 'error');
    } finally {
      if (version === requestVersion) { submit.disabled = false; submit.textContent = 'Compare Cities'; }
    }
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    const names = inputs.map((input, index) => cityNames[index] || input.value.trim().split(',')[0].trim());
    if (!names[0] || !names[1]) { banner('Choose two cities before comparing forecasts.', 'error'); return; }
    if (names[0].toLocaleLowerCase() === names[1].toLocaleLowerCase()) { banner('Choose two distinct cities.', 'error'); return; }
    compare(names);
  });
})();
