import React, { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { secondsFor } from "../utils.js";

export default function OverrideDialog({ rec, plant, onClose, onDone }) {
  const ref = useRef();
  const [mode, setMode] = useState("adjust");
  const [liters, setLiters] = useState(rec.volume_liters);
  const [validTo, setValidTo] = useState("");
  const [reason, setReason] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => { ref.current.showModal(); }, []);

  const n = reason.trim().length;
  const flow = plant?.pump_flow_lpm || 0;
  const maxL = plant?.max_liters_per_watering;

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      if (mode === "reject") {
        await api.reject(rec.rec_id, { reason });
      } else {
        const body = { volume_liters: Number(liters), reason };
        if (validTo) body.valid_to = validTo + ":00";
        await api.override(rec.rec_id, body);
      }
      ref.current.close();
      onDone(mode === "reject" ? "Đã từ chối đề xuất, lý do đã được lưu" : "Đã ghi đè, lý do đã được lưu");
    } catch (ex) {
      setErr(ex.message);
    }
  };

  return (
    <dialog ref={ref} onClose={onClose}>
      <form onSubmit={submit}>
        <h2>Ghi đè đề xuất #{rec.rec_id}</h2>
        <p className="hint">Hiện tại: {rec.scope_note}</p>
        <div className="ov-mode">
          <label><input type="radio" checked={mode === "adjust"} onChange={() => setMode("adjust")} /> Sửa lượng nước</label>
          <label><input type="radio" checked={mode === "reject"} onChange={() => setMode("reject")} /> Từ chối</label>
        </div>
        {mode === "adjust" && (
          <>
            <label>Lượng nước tối đa mới (lít){maxL ? ` · không quá ${maxL} L` : ""}
              <span className="row">
                <input type="number" step="0.05" min="0" max={maxL} value={liters} onChange={(e) => setLiters(e.target.value)} />
                <span className="conv">= {secondsFor(Number(liters) || 0, flow)} giây bơm ({flow} L/phút)</span>
              </span>
            </label>
            <label>Kéo dài hiệu lực đến (không bắt buộc)
              <input type="datetime-local" value={validTo} onChange={(e) => setValidTo(e.target.value)} />
            </label>
          </>
        )}
        <label>Lý do <span className="muted">{n}/10 ký tự</span>
          <textarea rows="3" value={reason} onChange={(e) => setReason(e.target.value)}
                    placeholder="vd: chiều nay dự báo mưa rào, giảm còn một nửa" />
        </label>
        <p className="err">{err}</p>
        <div className="row end">
          <button type="button" className="btn" onClick={() => ref.current.close()}>Hủy</button>
          <button className="btn warn" disabled={n < 10}>{mode === "reject" ? "Xác nhận từ chối" : "Xác nhận ghi đè"}</button>
        </div>
      </form>
    </dialog>
  );
}
