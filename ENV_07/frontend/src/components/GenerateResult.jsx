import React from "react";
import { fmt, fmtTime } from "../utils.js";

export default function GenerateResult({ result, onClose }) {
  if (!result) return null;
  const r = result.recommendation;
  const used = result.reading;
  const cls = result.created ? "ok" : result.existing ? "warn" : "info";

  return (
    <div className={"gen-result " + cls}>
      <div className="gen-head">
        <b>{result.created ? "Đã tạo đề xuất mới" : result.existing ? "Đang có đề xuất chờ xử lý" : "Không tạo đề xuất"}</b>
        <button className="btn sm" onClick={onClose}>Đóng</button>
      </div>
      {used && (
        <p className="gen-reading">
          Dựa trên số đo lúc {fmtTime(used.read_at)}: đất <b>{fmt(used.soil)}%</b>
          {used.air_temp != null && <> · {fmt(used.air_temp)}°C</>}
          {used.air_humidity != null && <> · ẩm không khí {fmt(used.air_humidity, 0)}%</>}
        </p>
      )}
      <p>{result.message}</p>
      {r && (
        <p className="gen-rec">
          #{r.rec_id}: tưới tới <b>{fmt(r.target_moisture, 0)}%</b>, tối đa <b>{fmt(r.volume_liters, 2)} L</b> ({r.duration_sec} giây)
          <br /><span className="muted">{r.reason}</span>
        </p>
      )}
    </div>
  );
}
