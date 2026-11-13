import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { fmt, fmtTime, SOURCE } from "../utils.js";

export default function PumpLog({ notify }) {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.events().then(setRows).catch((e) => notify(e.message, true)); }, [notify]);

  const total = rows.reduce((a, r) => a + r.EstimatedLiters, 0);

  return (
    <article className="panel">
      <h2>Nhật ký bơm</h2>
      <p className="hint">Chỉ ghi khi ESP32 báo đã bơm xong, nên số giây và số lít là số thật (60 giây = 2 lít).</p>
      <div className="table-wrap">
        <table>
          <thead><tr>
            <th>Thời điểm</th><th>Cây</th><th>Nguồn</th><th className="num">Giây</th><th className="num">Lít</th>
            <th className="num">Ẩm sau</th><th>Người ra lệnh</th><th>Yêu cầu / duyệt</th><th>Lý do dừng</th>
          </tr></thead>
          <tbody>
            {!rows.length && <tr><td colSpan="9" className="muted">Chưa bơm lần nào.</td></tr>}
            {rows.map((e) => (
              <tr key={e.EventId}>
                <td>{fmtTime(e.StartedAt)}</td>
                <td>{e.CropName || "--"}</td>
                <td>{SOURCE[e.Source] || e.Source}{e.RecId ? ` #${e.RecId}` : ""}</td>
                <td className="num">{e.DurationSec}</td>
                <td className="num">{fmt(e.EstimatedLiters, 2)}</td>
                <td className="num">{e.FinalMoisture != null ? fmt(e.FinalMoisture) + "%" : "--"}</td>
                <td>{e.IssuedByName || (e.Source === "AUTO" ? "Hệ thống (tự động)" : "--")}</td>
                <td className="scope">
                  {e.RequestId ? <>
                    <b>{e.RequestedByName}</b> yêu cầu, <b>{e.ReviewedByName}</b> duyệt
                    <div className="muted">Lý do: {e.RequestReason}</div>
                  </> : "--"}
                </td>
                <td className="scope">{e.StopReason || "--"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > 0 && <p className="hint">Tổng {rows.length} lần, {fmt(total, 2)} lít.</p>}
    </article>
  );
}
