const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchFromAPI(endpoint: string, options?: RequestInit) {
  const url = `${API_BASE_URL}/api/v1${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "X-Project-Id": "proj_default_production",
        "X-Environment": "production",
        ...(options?.headers || {})
      },
      cache: "no-store"
    });
    if (!res.ok) {
      throw new Error(`API error: ${res.status} ${res.statusText}`);
    }
    return await res.json();
  } catch (error) {
    console.error(`Fetch failed for ${endpoint}:`, error);
    throw error;
  }
}

export const api = {
  // Traces & Runs
  getTraces: (params?: { agent_name?: string; status?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.agent_name) q.set("agent_name", params.agent_name);
    if (params?.status) q.set("status", params.status);
    if (params?.limit) q.set("limit", String(params.limit));
    return fetchFromAPI(`/traces?${q.toString()}`);
  },
  getTraceDetail: (traceId: string) => fetchFromAPI(`/traces/${traceId}`),
  getTraceWaterfall: (traceId: string) => fetchFromAPI(`/traces/${traceId}/waterfall`),
  getRuns: () => fetchFromAPI("/runs"),
  getRunDetail: (runId: string) => fetchFromAPI(`/runs/${runId}`),
  getRunReport: (runId: string) => fetchFromAPI(`/runs/${runId}/report`),

  // Agents & Health
  getAgents: () => fetchFromAPI("/agents"),
  getAgentDetail: (name: string) => fetchFromAPI(`/agents/${name}`),

  // Reliability Findings
  getFindings: (params?: { finding_type?: string; severity?: string }) => {
    const q = new URLSearchParams();
    if (params?.finding_type) q.set("finding_type", params.finding_type);
    if (params?.severity) q.set("severity", params.severity);
    return fetchFromAPI(`/findings?${q.toString()}`);
  },

  // Policies & Violations
  getPolicies: () => fetchFromAPI("/policies"),
  updatePolicy: (policyId: string, payload: { enabled?: boolean; threshold?: number }) =>
    fetchFromAPI(`/policies/${policyId}`, { method: "PUT", body: JSON.stringify(payload) }),
  getPolicyViolations: () => fetchFromAPI("/policies/violations"),

  // Evaluations & Regressions
  getDatasets: () => fetchFromAPI("/evaluations/datasets"),
  getEvalRuns: () => fetchFromAPI("/evaluations/runs"),
  getEvalRunDetail: (runId: string) => fetchFromAPI(`/evaluations/runs/${runId}`),
  compareEvalRuns: (baselineId: string, candidateId: string) =>
    fetchFromAPI("/evaluations/compare", {
      method: "POST",
      body: JSON.stringify({ baseline_run_id: baselineId, candidate_run_id: candidateId })
    }),

  // Model comparison & Pricing
  getModelComparisons: () => fetchFromAPI("/compare/models"),
  getPricing: () => fetchFromAPI("/pricing"),

  // Metrics
  getTimeseriesMetrics: () => fetchFromAPI("/metrics/timeseries"),
  getSystemHealth: () => fetchFromAPI("/system/health"),
  getSystemObservability: () => fetchFromAPI("/system/observability"),

  // Demo Runner
  runDemoScenario: (scenario: string) =>
    fetchFromAPI(`/demo/run-scenario?scenario=${scenario}`, { method: "POST" })
};
