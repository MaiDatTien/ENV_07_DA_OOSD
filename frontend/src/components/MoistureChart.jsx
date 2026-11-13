import React from "react";
import { fmtTime } from "../utils.js";

export default function MoistureChart({ rows, stage }) {
  const W = 600, H = 220, P = 26;
  if (!rows.length) {
    return (
      <svg className="chart" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        <text x={W / 2} y={H / 2} textAnchor="middle" fill="#8b8676" fontSize="13">Chưa có số đo từ ESP32</text>
      </svg>
    );
  }
  const x = (i) => P + (i * (W - P * 2)) / Math.max(1, rows.length - 1);
  const y = (v) => H - P - (v / 100) * (H - P * 2);
  const line = (key) =>
    rows.map((r, i) => (r[key] == null ? null : `${x(i).toFixed(1)},${y(r[key]).toFixed(1)}`)).filter(Boolean).join(" ");

  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      {[0, 25, 50, 75, 100].map((v) => (
        <g key={v}>
          <line x1={P} x2={W - 8} y1={y(v)} y2={y(v)} stroke="#e2d9c6" />
          <text x="4" y={y(v) + 4} fontSize="10" fill="#8b8676">{v}</text>
        </g>
      ))}
      {stage && (
        <rect x={P} width={W - P - 8} y={y(stage.moisture_max)}
              height={y(stage.moisture_min) - y(stage.moisture_max)} fill="rgba(76,122,54,.16)" />
      )}
      <polyline points={line("AirHumidity")} fill="none" stroke="#c9902a" strokeWidth="2" strokeDasharray="4 3" />
      <polyline points={line("SoilMoisture")} fill="none" stroke="#2c6a87" strokeWidth="2" />
      <text x={P} y={H - 6} fontSize="10" fill="#8b8676">{fmtTime(rows[0].ReadAt)}</text>
      <text x={W - 8} y={H - 6} fontSize="10" fill="#8b8676" textAnchor="end">{fmtTime(rows[rows.length - 1].ReadAt)}</text>
    </svg>
  );
}
