export const state = {
  mode: "reference",
  runId: "reference",
  runName: "Synthetic reference case",
  runStatus: "Approved",
  modelVersion: "reference-scorecard",
  findings: null,
  health: null,
  twins: null,
  remediation: null,
  watch: null,
  policy: null,
  loading: {},
  error: {},
  confirmedAssumptions: false,
  selectedScenario: 0,
};

export function setState(patch) {
  Object.assign(state, patch);
  document.dispatchEvent(new CustomEvent("janus:state"));
}
