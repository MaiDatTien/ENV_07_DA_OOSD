import React, { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { fmt, fmtTime, MANUAL_MAX_LITERS, PUMP_FLOW, REQ_STATUS, secondsFor } from "../utils.js";

export default function PumpRequests({ can, notify, deviceOk, busy, onChange, refreshKey }) {
  const [rows, setRows] = useState([]);
  const [liters, setLiters] = useState(0.5);
  const [reason, setReason] = useState("");
  const [reviewing, setReviewing] = useState(null);
  const [note, setNote] = useState("");
  const canApprove = can("pump.approve");

  const load = useCallback(() => api.pumpRequests().then(setRows).catch(() => {}), []);
  useEffect(() => { load(); }, [load, refreshKey]);

  const L = Number(liters) || 0;
  const n = reason.trim().length;

  const send = async (e) => {
    e.preventDefault();
    try {
      const r = await api.requestPump(L, reason);
      notify(r.message);
      setReason("");
      load(); onChange();
    } catch (ex) { notify(ex.message, true); }
  };

  const review = async () => {
    try {
      const r = reviewing.mode === "approve"
        ? await api.approveRequest(reviewing.id, note)
        : await api.rejectRequest(reviewing.id, note);
      notify(r.message || "Đã từ chối yêu cầu");
      setReviewing(null); setNote("");
      load(); onChange();
    } catch (ex) { notify(ex.message, true); }
  };

  const pending = rows.filter((r) => r.Status === "PENDING");

  return (
    <article className="panel">
      <h2>Bơm ngoài đề xuất</h2>

      {can("pump.request") && (
        <form onSubmit={send}>
          <p className="hint">Bơm tay tối đa <b>{MANUAL_MAX_LITERS} lít (60 giây)</b> mỗi lần, bắt buộc ghi lý do.
            {canApprove ? " Bạn có quyền duyệt nên lệnh được gửi ngay (vẫn ghi tên bạn là người duyệt)."
                        : " Yêu cầu sẽ chờ Kỹ sư canh tác hoặc Quản trị duyệt mới bơm."}</p>
          <div className="row">
            <input type="number" min="0.05" max={MANUAL_MAX_LITERS} step="0.05" value={liters} onChange={(e) => setLiters(e.target.value)} />
            <span className="unit">lít</span>
            <span className="conv">= {secondsFor(L, PUMP_FLOW)} giây bơm</span>
          </div>
          <label className="block-label">Lý do <span className="muted">{n}/10 ký tự</span>
            <textarea rows="2" value={reason} onChange={(e) => setReason(e.target.value)}
                      placeholder="vd: lá héo lúc trưa, đất mặt khô nhưng cảm biến chưa báo" />
          </label>
          <button className="btn water" disabled={n < 10 || L <= 0 || L > MANUAL_MAX_LITERS || (canApprove && (!deviceOk || busy))}>
            {canApprove ? "Bơm ngay" : "Gửi yêu cầu bơm"}
          </button>
          {canApprove && !deviceOk && <span className="err"> ESP32 chưa kết nối, chưa bơm được.</span>}
        </form>
      )}

      {canApprove && pending.length > 0 && (
        <>
          <h3>Chờ duyệt ({pending.length})</h3>
          {pending.map((r) => (
            <div className="req-card" key={r.RequestId}>
              <div><b>{r.RequestedByName}</b> xin bơm <b>{fmt(r.Liters, 2)} L</b> ({r.DurationSec} giây) · {fmtTime(r.RequestedAt)}</div>
              <div className="muted">Lý do: {r.Reason}</div>
              {reviewing?.id === r.RequestId ? (
                <div className="row">
                  <input className="grow" value={note} onChange={(e) => setNote(e.target.value)}
                         placeholder={reviewing.mode === "reject" ? "Lý do từ chối (bắt buộc ≥ 10 ký tự)" : "Ghi chú (không bắt buộc)"} />
                  <button className={"btn " + (reviewing.mode === "approve" ? "water" : "warn")} onClick={review}
                          disabled={reviewing.mode === "reject" && note.trim().length < 10}>
                    {reviewing.mode === "approve" ? "Xác nhận duyệt & bơm" : "Xác nhận từ chối"}
                  </button>
                  <button className="btn" onClick={() => setReviewing(null)}>Hủy</button>
                </div>
              ) : (
                <div className="row">
                  <button className="btn sm water" disabled={!deviceOk || busy} onClick={() => { setReviewing({ id: r.RequestId, mode: "approve" }); setNote(""); }}>Duyệt</button>
                  <button className="btn sm" onClick={() => { setReviewing({ id: r.RequestId, mode: "reject" }); setNote(""); }}>Từ chối</button>
                  {!deviceOk && <span className="muted">ESP32 chưa kết nối, chưa duyệt được</span>}
                </div>
              )}
            </div>
          ))}
        </>
      )}

      <h3>Yêu cầu gần đây</h3>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Lúc</th><th>Người yêu cầu</th><th className="num">Lít</th><th>Lý do</th><th>Người duyệt</th><th>Trạng thái</th></tr></thead>
          <tbody>
            {!rows.length && <tr><td colSpan="6" className="muted">Chưa có yêu cầu.</td></tr>}
            {rows.slice(0, 8).map((r) => (
              <tr key={r.RequestId}>
                <td>{fmtTime(r.RequestedAt)}</td>
                <td>{r.RequestedByName}</td>
                <td className="num">{fmt(r.Liters, 2)}</td>
                <td className="scope">{r.Reason}</td>
                <td>{r.ReviewedByName || "--"}{r.ReviewNote ? <div className="muted">{r.ReviewNote}</div> : null}</td>
                <td><span className={"tag " + ({ PENDING: "PROPOSED", APPROVED: "APPLIED", REJECTED: "REJECTED" }[r.Status] || "EXPIRED")}>{REQ_STATUS[r.Status]}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
