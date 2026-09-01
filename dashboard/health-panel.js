/*
 * Connect the existing GIS selection request to the health dashboard.
 * The map's /api/wbgt response now includes `health`, calculated from the
 * same current and forecast WBGT records as the colour field and map card.
 */
(() => {
  const originalFetch = window.fetch.bind(window);
  const summary = document.getElementById("healthSummary");
  const recommendations = document.getElementById("recommendations");
  let selectedPayload;
  let payloadReady;
  // Registered before the legacy panel observer, so a new selection cannot
  // accidentally receive the preceding city's cached health response.
  new MutationObserver(() => { selectedPayload = undefined; }).observe(
    document.getElementById("place"), { childList: true, characterData: true, subtree: true }
  );

  const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[char]));

  const INFO_ICON = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;

  function getLevelClass(levelStr) {
    const s = String(levelStr || "").trim().toLowerCase();
    if (s.includes("extreme") || s.includes("critical") || s.includes("red")) return "level-extreme";
    if (s.includes("very") || s.includes("orange")) return "level-very_high";
    if (s.includes("high") || s.includes("yellow") || s.includes("elevated")) return "level-high";
    if (s.includes("mod") || s.includes("green")) return "level-moderate";
    return "level-low";
  }

  function renderHealth(payload) {
    const current = payload.current || {};
    const health = payload.health || {};
    const context = health.risk_context || {};
    const levelDisplay = context.overall_heat_health_level || current.epidemiological_risk_category || "Low";
    const levelClass = getLevelClass(levelDisplay);

    summary.innerHTML = `
      <article>
        <div class="card-label-row">
          <span class="card-label">Mortality risk index</span>
          <span class="info-tip" tabindex="0" role="tooltip" aria-label="Mortality Risk Index: 0–100 scale measuring excess heat-related mortality risk.">
            ${INFO_ICON}
            <span class="tip-content"><strong>Mortality Risk Index (MRI)</strong>Normalized 0–100 score estimating excess population mortality risk modeled from current WBGT thermal exposure.</span>
          </span>
        </div>
        <strong>${current.mortality_risk_index ?? "--"}/100</strong>
      </article>
      <article>
        <div class="card-label-row">
          <span class="card-label">Relative risk</span>
          <span class="info-tip" tabindex="0" role="tooltip" aria-label="Relative Risk: Multiplier comparing expected mortality vs 30°C WBGT baseline.">
            ${INFO_ICON}
            <span class="tip-content"><strong>Relative Risk (RR)</strong>Statistical multiplier comparing expected mortality under current heat vs. 30.0°C baseline (e.g. 1.15 = +15% excess mortality).</span>
          </span>
        </div>
        <strong>${current.relative_risk ?? "--"}</strong>
      </article>
      <article class="health-level ${levelClass}">
        <div class="card-label-row">
          <span class="card-label">Overall heat-health level</span>
          <span class="info-tip" tabindex="0" role="tooltip" aria-label="Overall Heat-Health Level: Synthesized public health risk category.">
            ${INFO_ICON}
            <span class="tip-content"><strong>Overall Heat-Health Level</strong>Synthesized severity tier (Low to Extreme) integrating physical WBGT, mortality risk, and 5-day heat persistence.</span>
          </span>
        </div>
        <strong>${escapeHtml(levelDisplay)}</strong>
      </article>`;
    const items = (health.recommendations || []).slice(0, 3);
    recommendations.innerHTML = items.length ? items.map(item => `
      <article class="recommendation"><strong>${escapeHtml(item.category || "Heat-health action")}</strong>
      <p>${escapeHtml(item.recommendation || item.action || "")}</p>
      <small>${escapeHtml(item.reason || item.source || "Evidence-guided recommendation")}</small></article>`).join("") :
      '<p class="empty">Recommendations are unavailable for this observation.</p>';
  }

  window.fetch = async (...args) => {
    const url = String(args[0]);
    // The legacy inline dashboard asks these two endpoints after the selected
    // city label changes.  Serve its response from the pending map payload so
    // it remains backwards-compatible without calculating WBGT a second time.
    if (url.includes("/api/heat-risk?") || url.includes("/api/recommendations?")) {
      if (!selectedPayload) await new Promise(resolve => { payloadReady = resolve; });
      const health = selectedPayload.health || {};
      const body = url.includes("/api/heat-risk?")
        ? { current: { mortalityRiskIndex: selectedPayload.current?.mortality_risk_index, relativeRisk: selectedPayload.current?.relative_risk, riskCategory: selectedPayload.current?.epidemiological_risk_category } }
        : health;
      return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
    }
    const response = await originalFetch(...args);
    if (url.includes("/api/wbgt?") && response.ok) {
      response.clone().json().then(payload => {
        selectedPayload = payload;
        if (payloadReady) { payloadReady(); payloadReady = undefined; }
        renderHealth(payload);
      }).catch(() => {});
    }
    return response;
  };
})();
