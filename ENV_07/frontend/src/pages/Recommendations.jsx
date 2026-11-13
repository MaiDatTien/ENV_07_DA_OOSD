import React, { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { fmt, fmtTime, STATUS } from "../utils.js";
import OverrideDialog from "../components/OverrideDialog.jsx";
import GenerateResult from "../components/GenerateResult.jsx";

export default function Recommendations({ notify, can, plant }) {
  const [rows, setRows] = useState([]);
  const [dialogRec, setDialogRec] = useState(null);
  const [history, setHistory] = useState(null);
  const [genResult, setGenResult] = useState(null);
  const histRef = useRef();

  const load = useCallback(() => api.recs().then(setRows).catch((e) => notify(e.message, true)), [notify]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (history) histRef.current.showModal(); }, [history]);

  const toEntity = (r) => ({ rec_id: r.RecId, volume_liters: r.VolumeLiters, scope_note: r.ScopeNote });

  const run = async (fn, msg) => {
    try { const res = await fn(); notify(typeof msg === "function" ? msg(res) : msg); load(); }
    catch (e) { notify(e.message, true); }
  };

  const generate = async () => {
    try { setGenResult(await api.generate()); load(); }
    catch (e) { notify(e.message, true); }
  };

  return (
    <article className="panel">
      <div className="panel-head">
        <h2>Đề xuất tưới</h2>
        {can("rec.generate") && <button className="btn water" onClick={generate}>Tạo đề xuất từ số đo mới nhất</button>}
      </div>
      <GenerateResult result={genResult} onClose={() => setGenResult(null)} />
      <p className="hint">Mỗi đề xuất chỉ có hiệu lực trong <b>phạm vi áp dụng</b>: trong khung giờ ghi trên đề xuất và chỉ khi
        đất còn khô hơn ngưỡng. Khi áp dụng, ESP32 bơm từng nhịp 5 giây, chờ 20 giây cho nước thấm rồi đo lại;
        đất đạt <b>mục tiêu</b> là dừng, không bao giờ vượt <b>lượng nước tối đa</b>.
        Kỹ sư canh tác có thể <b>ghi đè</b> lượng nước hoặc <b>từ chối</b>, bắt buộc ghi lý do.</p>
      <div className="table-wrap">
        <table>
          <thead><tr>
            <th>#</th><th>Tạo lúc</th><th>Giai đoạn</th><th className="num">Ẩm lúc tạo</th><th className="num">Mục tiêu</th>
            <th className="num">Tối đa (lít)</th><th className="num">= giây</th><th>Phạm vi áp dụng</th><th>Người tạo / áp dụng</th><th>Trạng thái</th><th />
          </tr></thead>
          <tbody>
            {!rows.length && <tr><td colSpan="11" className="muted">Chưa có đề xuất. Bấm "Tạo đề xuất từ số đo mới nhất".</td></tr>}
            {rows.map((r) => {
              const open = r.Status === "PROPOSED" || r.Status === "OVERRIDDEN";
              return (
                <tr key={r.RecId} className={open ? "open-row" : ""}>
                  <td>{r.RecId}</td>
                  <td>{fmtTime(r.CreatedAt)}</td>
                  <td>{r.StageName || "--"}</td>
                  <td className="num">{fmt(r.MoistureAtCreate)}%</td>
                  <td className="num">{r.TargetMoisture != null ? fmt(r.TargetMoisture, 0) + "%" : "--"}</td>
                  <td className="num">{fmt(r.VolumeLiters, 2)}</td>
                  <td className="num">{r.DurationSec}</td>
                  <td className="scope">{r.ScopeNote}</td>
                  <td className="scope">{r.CreatedByName || "Hệ thống"}
                    {r.Status === "APPLIED" && <div className="muted">áp dụng: {r.AppliedByName || "tự động"}</div>}</td>
                  <td><span className={"tag " + r.Status}>{STATUS[r.Status]}</span></td>
                  <td className="actions">
                    {open && can("rec.apply") && <>
                      <button className="btn sm water" onClick={() => run(() => api.apply(r.RecId), (x) => `Đã gửi lệnh tưới, tối đa ${fmt(x.liters, 2)} L (${x.duration_sec} giây)`)}>Áp dụng</button>{" "}
                    </>}
                    {open && can("rec.override") && <>
                      <button className="btn sm" onClick={() => setDialogRec(toEntity(r))}>Ghi đè</button>{" "}
                    </>}
                    {r.OverrideCount > 0 && (
                      <button className="btn sm" onClick={() => api.overrides(r.RecId).then((h) => setHistory({ id: r.RecId, items: h }))}>
                        Lịch sử ({r.OverrideCount})
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {dialogRec && (
        <OverrideDialog rec={dialogRec} plant={plant} onClose={() => setDialogRec(null)}
                        onDone={(m) => { notify(m); setDialogRec(null); load(); }} />
      )}

      {history && (
        <dialog ref={histRef} onClose={() => setHistory(null)}>
          <h2>Lịch sử ghi đè #{history.id}</h2>
          {history.items.map((o) => (
            <div className="hist" key={o.OverrideId}>
              <div>{fmtTime(o.CreatedAt)} · {o.FullName} · <b>
                {o.Action === "REJECT" ? "Từ chối" : `${o.OldDurationSec} → ${o.NewDurationSec} giây`}</b></div>
              <div className="muted">{o.Reason}</div>
            </div>
          ))}
          <div className="row end"><button className="btn" onClick={() => histRef.current.close()}>Đóng</button></div>
        </dialog>
      )}
    </article>
  );
}
