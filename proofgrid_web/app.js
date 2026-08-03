const state = { run: null, selected: null, reviews: [] };

const byId = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
}[char]));

async function api(path, options = {}) {
  if (window.PROOFGRID_BROWSER_API && (location.hostname.endsWith("github.io") || new URLSearchParams(location.search).has("static"))) {
    return window.PROOFGRID_BROWSER_API(path, options);
  }
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try { detail = (await response.json()).detail || detail; } catch (_) { /* response is not JSON */ }
    throw new Error(detail);
  }
  return response.json();
}

function notice(message, isError = false) {
  byId("notice").textContent = message;
  byId("notice").classList.toggle("error", isError);
}

function statusClass(row) {
  if (row.needs_review) return row.schema_score < 1 ? "fail" : "review";
  return "pass";
}

function compactOutput(row) {
  if (row.output === null) return row.error || "No output";
  try { return JSON.stringify(JSON.parse(row.output), null, 1); } catch (_) { return row.output; }
}

function renderMatrix() {
  const matrix = byId("matrix");
  if (!state.run) {
    matrix.innerHTML = '<div class="empty">Run the frozen suite to populate the proof sheet.</div>';
    return;
  }
  const candidates = state.run.candidates;
  const heldoutCases = state.run.cases.filter((item) => item.split === "heldout");
  matrix.style.gridTemplateColumns = `190px repeat(${candidates.length}, minmax(250px, 1fr))`;
  let html = `<div class="axis">Frozen case axis<br>heldout / ${heldoutCases.length}</div>`;
  for (const candidate of candidates) {
    const summary = candidate.summary;
    html += `<div class="run-head ${summary.promoted ? "promoted" : ""}"><b>${escapeHtml(candidate.label)}</b><span>prompt ${candidate.prompt_hash.slice(0, 6)} · ${escapeHtml(candidate.model)}<br>exact ${(summary.exact_pass_rate * 100).toFixed(1)}% · ${summary.median_latency_ms.toFixed(2)} ms · $${summary.total_cost_usd.toFixed(4)}</span></div>`;
  }
  for (const item of heldoutCases) {
    html += `<div class="case"><span class="id">${escapeHtml(item.case_id)}</span><b>${escapeHtml(item.category.replaceAll("-", " "))}</b><small>${escapeHtml(item.tags.join(" · "))}</small></div>`;
    for (const candidate of candidates) {
      const row = candidate.rows.find((candidateRow) => candidateRow.case_id === item.case_id);
      const selected = state.selected?.candidateId === candidate.candidate_id && state.selected?.caseId === item.case_id;
      const label = row.needs_review ? (row.schema_score < 1 ? "FAIL" : "REVIEW") : "PASS";
      html += `<button class="cell ${statusClass(row)} ${selected ? "selected" : ""}" data-candidate="${escapeHtml(candidate.candidate_id)}" data-case="${escapeHtml(item.case_id)}"><pre>${escapeHtml(compactOutput(row))}</pre><span class="score">${row.task_score.toFixed(2)} ${label}</span></button>`;
    }
  }
  matrix.innerHTML = html;
  matrix.querySelectorAll(".cell").forEach((cell) => cell.addEventListener("click", () => selectCell(cell.dataset.candidate, cell.dataset.case)));
}

function selectedData() {
  if (!state.run || !state.selected) return null;
  const candidate = state.run.candidates.find((item) => item.candidate_id === state.selected.candidateId);
  const row = candidate?.rows.find((item) => item.case_id === state.selected.caseId);
  const review = state.reviews.find((item) => item.candidate_id === state.selected.candidateId && item.case_id === state.selected.caseId);
  return candidate && row ? { candidate, row, review } : null;
}

function selectCell(candidateId, caseId) {
  state.selected = { candidateId, caseId };
  renderMatrix();
  renderEvidence();
}

function renderEvidence() {
  const selected = selectedData();
  if (!selected) return;
  const { candidate, row, review } = selected;
  byId("selected-title").textContent = `${row.case_id} / ${candidate.label}`;
  byId("selected-summary").textContent = row.needs_review ? (row.review_reason || "Manual review required") : "All frozen deterministic checks pass.";
  const checks = [
    ["Schema", row.schema_score, row.schema_score >= 1],
    ["Task", row.task_score, row.task_score >= state.run.promotion_rule.review_below_task_score],
    ["Exact", row.exact_score, row.exact_score >= 1],
    ["Retries", row.retry_count, row.failure_class === null],
  ];
  byId("selected-checks").innerHTML = checks.map(([label, value, ok]) => `<div class="check ${ok ? "ok" : "bad"}">${label}<br>${label === "Retries" ? value : value.toFixed(2)}</div>`).join("");
  byId("selected-output").textContent = compactOutput(row);
  const canResolve = Boolean(review && review.status === "open" && row.needs_review);
  byId("resolve-button").disabled = !canResolve;
  byId("keep-button").disabled = !canResolve;
}

function renderGate() {
  if (!state.run) return;
  const winner = state.run.decision.winner;
  const candidate = winner ? state.run.candidates.find((item) => item.candidate_id === winner) : null;
  if (candidate) {
    const passing = state.run.decision.promoted_candidates.length;
    const reason = passing === 1
      ? `${escapeHtml(candidate.label)} alone meets the frozen heldout thresholds`
      : `${escapeHtml(candidate.label)} wins the frozen cost/retry/latency tie-break among ${passing} passing candidates`;
    byId("gate-copy").innerHTML = `<b>PASS</b> · ${reason} · not a provider ranking`;
  } else {
    byId("gate-copy").innerHTML = `<b>BLOCKED</b> · no single candidate meets every frozen threshold`;
  }
  byId("export-link").href = window.PROOFGRID_BROWSER_API && (location.hostname.endsWith("github.io") || new URLSearchParams(location.search).has("static"))
    ? "./frozen-experiment.json"
    : "/api/reports/latest?format=csv";
  byId("export-link").setAttribute("aria-disabled", "false");
}

async function runSuite() {
  const button = byId("run-button");
  button.disabled = true;
  notice("Running 18 frozen cases across three candidate paths…");
  try {
    state.run = await api("/api/runs", { method: "POST", body: "{}" });
    state.reviews = await api(`/api/reviews?run_id=${encodeURIComponent(state.run.run_id)}`);
    state.selected = { candidateId: "structured", caseId: "EXT-017" };
    byId("run-title").textContent = `${state.run.run_id} comparison`;
    notice(`Run complete · ${state.reviews.filter((item) => item.status === "open").length} review items · deterministic no-key profile`);
    renderMatrix();
    renderEvidence();
    renderGate();
  } catch (error) {
    notice(error.message, true);
  } finally {
    button.disabled = false;
  }
}

async function resolveSelected() {
  const selected = selectedData();
  if (!selected?.review) return;
  try {
    await api(`/api/reviews/${encodeURIComponent(selected.review.review_id)}/resolve`, {
      method: "POST",
      body: JSON.stringify({ corrected_output: selected.row.expected, note: "Accepted frozen expected correction in workbench" }),
    });
    state.run = await api(`/api/runs/${encodeURIComponent(state.run.run_id)}`);
    state.reviews = await api(`/api/reviews?run_id=${encodeURIComponent(state.run.run_id)}`);
    notice(`${selected.row.case_id} correction recorded; promotion gate recomputed.`);
    renderMatrix();
    renderEvidence();
    renderGate();
  } catch (error) { notice(error.message, true); }
}

byId("run-button").addEventListener("click", runSuite);
byId("resolve-button").addEventListener("click", resolveSelected);
byId("keep-button").addEventListener("click", () => notice("Review remains open; no evidence was changed."));

api("/api/suite").then((suite) => {
  byId("suite-count").textContent = `${suite.case_count} cases · ${suite.heldout_count} heldout`;
}).catch((error) => notice(error.message, true));
