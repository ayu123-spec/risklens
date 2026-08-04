import { useEffect, useState } from "react";
import { Doughnut, Bar, Line } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale,
         LinearScale, BarElement, PointElement, LineElement, Filler } from "chart.js";
import { apiGet } from "../api.js";
import { CHART_COLORS, RISK_RAMP, gradeColor, baseOptions } from "../chartTheme.js";
import { useCountUp } from "../useCountUp.js";

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale,
                 BarElement, PointElement, LineElement, Filler);

function Kpi({ icon, label, value, trend, trendClass, gradient }) {
  return (
    <div className="kpi">
      <div className="kpi-icon">{icon}</div>
      <div className="kpi-label">{label}</div>
      <div className={`kpi-value ${gradient ? "gradient" : ""}`}>{value}</div>
      {trend && <div className={`kpi-trend ${trendClass || ""}`}>{trend}</div>}
    </div>
  );
}

export default function AnalyticsPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      apiGet("/api/analytics/approval-rate"),
      apiGet("/api/analytics/risk-distribution"),
      apiGet("/api/analytics/grade-distribution"),
      apiGet("/api/analytics/portfolio-exposure"),
      apiGet("/api/analytics/over-time"),
    ]).then(([a, r, g, e, t]) =>
      setData({ approval: a, risk: r.distribution, grade: g.distribution, exposure: e, time: t.series })
    ).catch((e) => setError(e.message));
  }, []);

  const animRate = useCountUp(data ? Math.round(data.approval.approval_rate * 100) : 0, 900);
  const animTotal = useCountUp(data ? data.approval.total : 0, 900);

  if (error) return <div className="page"><div className="empty-state"><div className="big-icon">⚠</div><div>Can't load analytics.</div><div style={{fontSize:".8rem",marginTop:".5rem"}}>{error}</div></div></div>;
  if (!data) return <div className="page"><div className="loading"><div className="spinner" />Loading analytics…</div></div>;

  const hasData = data.approval.total > 0;
  const riskChart = { labels: data.risk.map(r=>r.risk_category), datasets:[{ data:data.risk.map(r=>r.count),
    backgroundColor:data.risk.map(r=>RISK_RAMP[r.risk_category]||CHART_COLORS.accent), borderWidth:0 }] };
  const gradeChart = { labels: data.grade.map(g=>g.grade), datasets:[{ label:"Assessments",
    data:data.grade.map(g=>g.count), backgroundColor:data.grade.map(g=>gradeColor(g.grade)), borderRadius:6 }] };
  const timeChart = { labels: data.time.map(t=>t.date), datasets:[{ label:"Assessments", data:data.time.map(t=>t.count),
    borderColor:CHART_COLORS.accent, backgroundColor:"rgba(43,77,255,0.12)", fill:true, tension:.35, pointRadius:3 }] };
  const exposurePct = Math.round(data.exposure.avg_default_probability * 100);

  return (
    <div className="page">
      <div className="page-head">
        <div className="eyebrow"><span className="pulse" />Portfolio analytics</div>
        <h1 className="page-title">Analytics</h1>
        <p className="page-desc">Live insight across every assessment — approval rates, risk composition, and portfolio exposure, drawn from the assessment database.</p>
      </div>
      {!hasData ? (
        <div className="empty-state"><div className="big-icon">◔</div>
          <div>No assessments yet. Run one on the Assess page and the charts populate here.</div></div>
      ) : (
        <>
          <div className="kpi-grid">
            <Kpi icon="◆" label="Total assessments" value={animTotal} gradient />
            <Kpi icon="✓" label="Approval rate" value={`${animRate}%`} trend={`${data.approval.approved} approved`} trendClass="down" />
            <Kpi icon="◈" label="Avg default prob." value={`${exposurePct}%`} trend="Portfolio-weighted" />
            <Kpi icon="▲" label="High-risk count" value={data.exposure.high_risk_count} trend="PD ≥ 35%" trendClass="up" />
          </div>
          <div className="chart-grid-2">
            <div className="card">
              <div className="card-title"><span className="dot" />Risk distribution</div>
              <div className="chart-box">
                <Doughnut data={riskChart} options={{ ...baseOptions, cutout:"62%", scales:{},
                  plugins:{legend:{position:"right",labels:{color:CHART_COLORS.text,font:{size:11},padding:12}}} }} />
              </div>
            </div>
            <div className="card">
              <div className="card-title"><span className="dot" />Grade distribution</div>
              <div className="chart-box"><Bar data={gradeChart} options={{...baseOptions, plugins:{legend:{display:false}}}} /></div>
            </div>
          </div>
          <div className="card">
            <div className="card-title"><span className="dot" />Assessment volume over time</div>
            <div className="chart-box tall"><Line data={timeChart} options={{...baseOptions, plugins:{legend:{display:false}}}} /></div>
          </div>
        </>
      )}
    </div>
  );
}
