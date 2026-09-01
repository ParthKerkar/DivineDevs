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

  function renderHealth(payload) {
    const current = payload.current || {};
    const health = payload.health || {};
    const context = health.risk_context || {};
    summary.innerHTML = `
      <article><span>Mortality risk index</span><strong>${current.mortality_risk_index ?? "--"}/100</strong></article>
      <article><span>Relative risk</span><strong>${current.relative_risk ?? "--"}</strong></article>
      <article class="health-level"><span>Overall heat-health level</span><strong>${escapeHtml(context.overall_heat_health_level || current.epidemiological_risk_category || "Unavailable")}</strong></article>`;
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
