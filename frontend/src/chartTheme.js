export const CHART_COLORS = {
  accent: "#2b4dff", accent2: "#5b3bff", amber: "#f59e0b",
  ok: "#10b981", warn: "#eab308", danger: "#ef4444",
  grid: "rgba(255,255,255,0.06)", text: "#9a9aa8",
};

export const RISK_RAMP = {
  "Very Low Risk": "#10b981", "Low Risk": "#84cc16", "Moderate Risk": "#eab308",
  "High Risk": "#f97316", "Very High Risk": "#ef4444", "Extreme Risk": "#b91c1c",
};

export const gradeColor = (g) => {
  if (g === "AAA" || g === "AA") return "#10b981";
  if (g === "A" || g === "BBB") return "#84cc16";
  if (g === "BB" || g === "B") return "#eab308";
  if (g === "CCC" || g === "CC") return "#f97316";
  return "#b91c1c";
};

export const fraudBandColor = (band) => ({
  "Very High": "#b91c1c", "High": "#ef4444", "Elevated": "#f59e0b",
  "Low": "#84cc16", "Very Low": "#10b981",
}[band] || "#9a9aa8");

export const baseOptions = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { labels: { color: CHART_COLORS.text, font: { size: 11 } } } },
  scales: {
    x: { grid: { color: CHART_COLORS.grid }, ticks: { color: CHART_COLORS.text, font: { size: 11 } } },
    y: { grid: { color: CHART_COLORS.grid }, ticks: { color: CHART_COLORS.text, font: { size: 11 } }, beginAtZero: true },
  },
};
