(() => {
  let run;
  let reviews = [];
  async function load() {
    if (!run) {
      const response = await fetch("./frozen-experiment.json");
      run = await response.json();
      reviews = run.candidates.flatMap((candidate) => candidate.rows
        .filter((row) => row.needs_review)
        .map((row) => ({
          review_id: `review-${candidate.candidate_id}-${row.case_id}`,
          run_id: run.run_id,
          candidate_id: candidate.candidate_id,
          case_id: row.case_id,
          status: "open",
          expected_correction: row.expected_output || null,
        })));
    }
    return run;
  }
  const clone = (value) => structuredClone(value);
  window.PROOFGRID_BROWSER_API = async (path, options = {}) => {
    const current = await load();
    await new Promise((resolve) => setTimeout(resolve, path === "/api/runs" ? 320 : 60));
    if (path === "/api/suite") return { case_count: current.cases.length, heldout_count: current.cases.filter((item) => item.split === "heldout").length };
    if (path === "/api/runs" && options.method === "POST") return clone(current);
    if (path.startsWith("/api/reviews?")) return clone(reviews);
    if (path.startsWith("/api/reviews/") && path.endsWith("/resolve")) {
      const reviewId = decodeURIComponent(path.split("/")[3]);
      const review = reviews.find((item) => item.review_id === reviewId);
      if (review) review.status = "resolved";
      return clone(review);
    }
    if (path.startsWith("/api/runs/")) return clone(current);
    throw new Error(`Unknown browser-workspace route: ${path}`);
  };
})();
