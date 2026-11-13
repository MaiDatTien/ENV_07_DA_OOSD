import React, { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { fmt, fmtTime, litersFor, secondsFor, SOURCE, STATUS } from "../utils.js";
import MoistureChart from "../components/MoistureChart.jsx";
import OverrideDialog from "../components/OverrideDialog.jsx";
import GenerateResult from "../components/GenerateResult.jsx";
import PumpRequests from "../components/PumpRequests.jsx";

export default function Monitor({ notify, can, reloadPlant }) {
  const [d, setD] = useState(null);
  const [rows, setRows] = useState([]);
  const [dialogRec, setDialogRec] = useState(null);
  const [genResult, setGenResult] = useState(null);
  const [tick, setTick] = useState(0);

  const load = useCallback(async () => {
    try {
      const [dash, rd] = await Promise.all([api.dashboard(), api.readings(60)]);
      setD(dash);
      setRows(rd);
      setTick((t) => t + 1);
    } catch (e) { notify(e.message, true); }
  }, [notify]);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  if (!d || !d.plant) return <p className="pad">Đang tải…</p>;

  const r = d.latest;
  const plant = d.plant;
  const flow = plant.pump_flow_lpm;
  const st = plant.current_stage;
  const q = d.quota;
  const qPct = q.limit > 0 ? Math.min(100, (q.used / q.limit) * 100) : 0;
  const dry = r && st && r.SoilMoisture < st.moisture_min;
  const rec = d.open_recommendation;
  const job = d.active_command;
  const dev = d.device;
  const online = dev.connected;

  let pumpText = "TẮT", pumpCls = "";
  if (!online) { pumpText = "KHÔNG KẾT NỐI"; pumpCls = "dry"; }
  else if (dev.PumpIsOn) { pumpText = "ĐANG BƠM"; pumpCls = "on"; }
  else if (job && job.Status === "DELIVERED") { pumpText = "ĐANG TƯỚI"; pumpCls = "on"; }

  const run = async (fn, msg) => {
    try { const res = await fn(); notify(typeof msg === "function" ? msg(res) : msg); load(); }
    catch (e) { notify(e.message, true); }
  };

  const generate = async () => {
    try { setGenResult(await api.generate()); load(); }
    catch (e) { notify(e.message, true); }
  };

  const jobText = job && (job.StopAtMoisture != null
    ? <>tưới từng nhịp tới khi đất đạt <b>{fmt(job.StopAtMoisture, 0)}%</b>, tối đa {fmt(litersFor(job.DurationSec, flow), 2)} L ({job.DurationSec} giây)</>
    : <>bơm {fmt(litersFor(job.DurationSec, flow), 2)} L ({job.DurationSec} giây)</>);

  return (
    <>
      {!online && (
        <div className="device-bar">
          <b>{dev.never ? "ESP32 chưa từng kết nối" : "ESP32 đang mất kết nối"}</b>
          {!dev.never && <> · lần cuối {fmtTime(dev.LastSeen)}</>}
          {" "}· Máy bơm không nhận được lệnh. Kiểm tra nguồn USB, WiFi và địa chỉ SERVER_URL trong code Arduino.
          Các nút bơm tạm khóa cho tới khi ESP32 kết nối lại.
        </div>
      )}

      <div className="strip">
        <div className="cell">
          <label>Độ ẩm đất</label>
          <b className={dry ? "dry" : ""}>{r ? fmt(r.SoilMoisture) + "%" : "--"}</b>
          <small>{r ? `ADC ${r.SoilRaw ?? "--"} · ${fmtTime(r.ReadAt)}` : "chưa có số đo"}{r && !online ? " · số đo cũ" : ""}</small>
        </div>
        <div className="cell">
          <label>Nhiệt độ không khí</label>
          <b>{r?.AirTemp != null ? fmt(r.AirTemp) + "°C" : "--"}</b>
          <small>DHT11</small>
        </div>
        <div className="cell">
          <label>Độ ẩm không khí</label>
          <b>{r?.AirHumidity != null ? fmt(r.AirHumidity, 0) + "%" : "--"}</b>
          <small>DHT11</small>
        </div>
        <div className="cell">
          <label>Máy bơm</label>
          <b className={pumpCls}>{pumpText}</b>
          <small>{dev.never ? "ESP32 chưa gửi dữ liệu" : `${dev.DeviceCode} · ${dev.message}`}</small>
        </div>
      </div>

      {job && (
        <div className={"job-bar" + (job.Status === "PENDING" ? " waiting" : "")}>
          {job.Status === "PENDING"
            ? <><b>Lệnh đang chờ gửi xuống ESP32</b> ({SOURCE[job.Source]}{job.IssuedByName ? ` · ${job.IssuedByName}` : ""}): {jobText}.
                {!online && " ESP32 chưa kết nối nên máy bơm CHƯA chạy, lệnh tự hủy sau 2 phút."}</>
            : <><b>Đang tưới</b> ({SOURCE[job.Source]}{job.IssuedByName ? ` · ${job.IssuedByName}` : " · tự động"}): {jobText}</>}
          {can("pump.stop") && <button className="btn sm" onClick={() => run(api.stopPump, "Đã gửi lệnh dừng / hủy")}>{job.Status === "PENDING" ? "Hủy lệnh" : "Dừng ngay"}</button>}
        </div>
      )}

      <div className="grid2">
        <div>
          <article className="panel">
            <h2>Độ ẩm đất so với nhu cầu giai đoạn</h2>
            <div className="gauge">
              {st && <div className="band" style={{ left: st.moisture_min + "%", width: st.moisture_max - st.moisture_min + "%" }} />}
              {r && (
                <div className="mark" style={{ left: `calc(${Math.min(100, r.SoilMoisture)}% - 1px)` }}>
                  <span>{fmt(r.SoilMoisture)}%</span>
                </div>
              )}
            </div>
            <div className="gauge-scale"><span>0%</span><span>25</span><span>50</span><span>75</span><span>100%</span></div>
            <p className="hint">
              {st ? `${plant.name} · giai đoạn "${st.name}" cần giữ đất ẩm ${st.moisture_min}–${st.moisture_max}%. Dưới ${st.moisture_min}% thì đề xuất tưới, tưới tới ${fmt((st.moisture_min + st.moisture_max) / 2, 0)}% thì dừng.`
                  : "Loại cây này chưa có lịch giai đoạn."}
            </p>
          </article>

          <article className="panel">
            <div className="panel-head">
              <h2>Đề xuất tưới</h2>
              {can("rec.generate") && <button className="btn water" onClick={generate}>Tạo đề xuất từ số đo mới nhất</button>}
            </div>
            <GenerateResult result={genResult} onClose={() => setGenResult(null)} />
            {!rec ? <p className="muted">Không có đề xuất nào đang chờ.</p> : (
              <div className="rec-card">
                <div className="big">#{rec.rec_id} · {fmt(rec.volume_liters, 2)} L tối đa ({rec.duration_sec} giây)
                  <span className={"tag " + rec.status}>{STATUS[rec.status]}</span></div>
                <div className="scope">{rec.scope_note}</div>
                <div className="why">{rec.reason}</div>
                <div className="row">
                  {can("rec.apply") && (
                    <button className="btn water" disabled={!!job || !online}
                            onClick={() => run(() => api.apply(rec.rec_id), (x) => `Đã gửi lệnh tưới tới ${fmt(x.target, 0)}%, tối đa ${fmt(x.liters, 2)} L (${x.duration_sec} giây)`)}>
                      Áp dụng (bắt đầu tưới)
                    </button>
                  )}
                  {can("rec.override") && <button className="btn" onClick={() => setDialogRec(rec)}>Ghi đè / Từ chối…</button>}
                  {!online && <span className="muted">ESP32 chưa kết nối</span>}
                </div>
              </div>
            )}
          </article>

          <article className="panel">
            <h2>Diễn biến 60 lần đo gần nhất</h2>
            <MoistureChart rows={rows} stage={st} />
            <div className="legend">
              <span><i className="l-soil" />Độ ẩm đất</span>
              <span><i className="l-hum" />Độ ẩm không khí</span>
              <span><i className="l-band" />Vùng cần giữ</span>
            </div>
          </article>
        </div>

        <div>
          <article className="panel">
            <h2>Hạn mức nước hôm nay</h2>
            <div className="meter"><div className={qPct >= 85 ? "high" : ""} style={{ width: qPct + "%" }} /></div>
            <p className="meter-txt">{fmt(q.used, 2)} / {fmt(q.limit, 2)} lít · còn <b>{fmt(q.remaining, 2)}</b> lít</p>
            <p className="hint">Mỗi lần tưới tối đa {fmt(plant.max_liters_per_watering, 2)} L · máy bơm 60 giây = 2 lít
              (1 L = {secondsFor(1, flow)} giây).</p>
          </article>

          <PumpRequests can={can} notify={notify} deviceOk={online} busy={!!job} onChange={load} refreshKey={tick} />

          <article className="panel">
            <h2>Tưới tự động</h2>
            <label className="switch">
              <input type="checkbox" checked={!!plant.auto_mode} disabled={!can("auto.toggle")}
                     onChange={(e) => run(async () => { await api.setMode(e.target.checked); reloadPlant(); },
                                          e.target.checked ? "Đã bật tự động" : "Đã chuyển sang thủ công")} />
              <span>Tự động tưới theo đề xuất</span>
            </label>
            <p className="hint">Đất khô hơn ngưỡng thì hệ thống tự tạo đề xuất và tưới từng nhịp tới khi đạt mục tiêu.
              Sau mỗi lần tưới chờ 30 phút. Đề xuất đã ghi đè phải bấm Áp dụng bằng tay.
              {!can("auto.toggle") && " Chỉ Kỹ sư canh tác hoặc Quản trị được bật/tắt."}</p>
          </article>
        </div>
      </div>

      {dialogRec && (
        <OverrideDialog rec={dialogRec} plant={plant} onClose={() => setDialogRec(null)}
                        onDone={(m) => { notify(m); setDialogRec(null); load(); }} />
      )}
    </>
  );
}
