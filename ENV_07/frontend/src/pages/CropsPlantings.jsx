import React, { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { blockSign, blockSignDot, clampMax, fmt, fmtDate, MAX_DAILY_LITERS, MAX_LITERS_PER_WATERING, MAX_STAGE_DAYS,
  PUMP_FLOW, secondsFor, todayStr } from "../utils.js";

const emptyStage = () => ({ name: "", duration_days: "", moisture_min: "", moisture_max: "" });
const today = todayStr;

export default function CropsPlantings({ plant, reloadPlant, notify, can }) {
  const [crops, setCrops] = useState([]);
  const [plantings, setPlantings] = useState([]);
  const [selected, setSelected] = useState(null);
  const [stages, setStages] = useState([emptyStage()]);
  const [newCrop, setNewCrop] = useState({ name: "", description: "" });
  const [start, setStart] = useState({ crop_id: "", planted_date: today(), daily_quota_liters: "", max_liters_per_watering: "", note: "" });
  const [edit, setEdit] = useState(null);
  const canCrop = can("crop.edit");
  const canPlant = can("planting.edit");

  const load = useCallback(async () => {
    try {
      const [c, p] = await Promise.all([api.crops(), api.plantings()]);
      setCrops(c);
      setPlantings(p);
    } catch (e) { notify(e.message, true); }
  }, [notify]);
  useEffect(() => { load(); }, [load]);

  const crop = crops.find((c) => c.CropId === selected);
  useEffect(() => {
    if (!crop) return;
    setStages(crop.Stages.length ? crop.Stages.map((s) => ({
      name: s.Name, duration_days: s.DurationDays, moisture_min: s.MoistureMin, moisture_max: s.MoistureMax,
    })) : [emptyStage()]);
  }, [selected, crops]);

  const run = async (fn, msg, after) => {
    try { const r = await fn(); notify(msg); await load(); if (after) after(r); }
    catch (e) { notify(e.message, true); }
  };

  const LIMIT = { duration_days: MAX_STAGE_DAYS, moisture_min: 100, moisture_max: 100 };
  const setS = (i, k) => (e) => {
    const v = k === "name" ? e.target.value : clampMax(e.target.value, LIMIT[k]);
    setStages(stages.map((s, j) => (j === i ? { ...s, [k]: v } : s)));
  };
  const checkPlanting = (f) => {
    const q = Number(f.daily_quota_liters), m = Number(f.max_liters_per_watering);
    if (f.planted_date > todayStr()) return "Ngày trồng không được ở tương lai";
    if (!(m > 0)) return "Tối đa mỗi lần tưới phải lớn hơn 0";
    if (m > MAX_LITERS_PER_WATERING) return `Mỗi lần tưới tối đa ${MAX_LITERS_PER_WATERING} lít (300 giây bơm)`;
    if (m > q) return "Tối đa mỗi lần tưới không được lớn hơn hạn mức cả ngày";
    return "";
  };
  const checkStages = () => {
    for (let i = 0; i < stages.length; i++) {
      const s = stages[i], lo = Number(s.moisture_min), hi = Number(s.moisture_max);
      const label = s.name || `giai đoạn ${i + 1}`;
      if (!s.name.trim()) return `Giai đoạn ${i + 1} chưa có tên`;
      if (!(Number(s.duration_days) >= 1)) return `${label}: số ngày phải từ 1 trở lên`;
      if (lo < 0 || hi > 100) return `${label}: độ ẩm phải nằm trong 0 đến 100%`;
      if (lo >= hi) return `${label}: ẩm thấp nhất phải nhỏ hơn ẩm cao nhất`;
    }
    const names = stages.map((s) => s.name.trim().toLowerCase());
    if (new Set(names).size !== names.length) return "Tên các giai đoạn không được trùng nhau";
    return "";
  };
  const sec = (l) => (Number(l) > 0 ? `= ${secondsFor(Number(l), PUMP_FLOW)} giây bơm` : "");
  const totalDays = stages.reduce((a, s) => a + (Number(s.duration_days) || 0), 0);

  return (
    <div className="grid2 even">
      <div>
        <article className="panel">
          <h2>Mùa vụ đang chạy</h2>
          {!plant ? <p className="muted">Chưa có mùa vụ nào đang chạy.</p> : !edit ? (
            <>
              <dl className="kv">
                <dt>Loại cây</dt><dd>{plant.name}</dd>
                <dt>Ngày trồng</dt><dd>{fmtDate(plant.planted_date)} · ngày thứ {plant.day}</dd>
                <dt>Giai đoạn</dt><dd>{plant.current_stage ? plant.current_stage.name : "--"}</dd>
                <dt>Hạn mức</dt><dd>{fmt(plant.daily_quota_liters, 2)} lít / ngày</dd>
                <dt>Mỗi lần tưới</dt><dd>tối đa {fmt(plant.max_liters_per_watering, 2)} lít ({secondsFor(plant.max_liters_per_watering, PUMP_FLOW)} giây)</dd>
              </dl>
              {canPlant && (
                <div className="row">
                  <button className="btn" onClick={() => setEdit({
                    planted_date: String(plant.planted_date).slice(0, 10),
                    daily_quota_liters: plant.daily_quota_liters, max_liters_per_watering: plant.max_liters_per_watering,
                  })}>Sửa hạn mức / ngày trồng</button>
                  <button className="btn" onClick={() => window.confirm(`Kết thúc mùa vụ ${plant.name}?`) &&
                    run(api.finishPlanting, "Đã kết thúc mùa vụ", reloadPlant)}>Kết thúc mùa vụ</button>
                </div>
              )}
            </>
          ) : (
            <form className="form" onSubmit={(e) => {
              e.preventDefault();
              const bad = checkPlanting(edit);
              if (bad) { notify(bad, true); return; }
              run(() => api.updatePlanting({ planted_date: edit.planted_date,
                daily_quota_liters: Number(edit.daily_quota_liters), max_liters_per_watering: Number(edit.max_liters_per_watering) }),
                "Đã lưu mùa vụ", () => { setEdit(null); reloadPlant(); });
            }}>
              <label className="wide">Ngày trồng<input type="date" max={todayStr()} value={edit.planted_date} onChange={(e) => setEdit({ ...edit, planted_date: e.target.value })} required /></label>
              <label>Hạn mức (lít / ngày)
                <input type="number" step="0.1" min="0" max={MAX_DAILY_LITERS} value={edit.daily_quota_liters} onKeyDown={blockSign}
                  onChange={(e) => setEdit({ ...edit, daily_quota_liters: clampMax(e.target.value, MAX_DAILY_LITERS) })} required />
                <small className="conv">{sec(edit.daily_quota_liters)}</small></label>
              <label>Tối đa mỗi lần tưới (lít)
                <input type="number" step="0.05" min="0.05" max={MAX_LITERS_PER_WATERING} value={edit.max_liters_per_watering} onKeyDown={blockSign}
                  onChange={(e) => setEdit({ ...edit, max_liters_per_watering: clampMax(e.target.value, MAX_LITERS_PER_WATERING) })} required />
                <small className="conv">{sec(edit.max_liters_per_watering)}</small></label>
              <div className="row wide"><button className="btn water">Lưu</button><button type="button" className="btn" onClick={() => setEdit(null)}>Hủy</button></div>
            </form>
          )}
        </article>

        {canPlant && (
          <article className="panel">
            <h2>Bắt đầu mùa vụ mới</h2>
            <p className="hint">Chỉ có 1 máy bơm nên mỗi lúc chạy 1 mùa vụ. Bắt đầu mùa mới thì mùa đang chạy tự kết thúc
              và được giữ lại trong lịch sử.</p>
            <form className="form" onSubmit={(e) => {
              e.preventDefault();
              const bad = checkPlanting(start);
              if (bad) { notify(bad, true); return; }
              run(() => api.startPlanting({ ...start, crop_id: Number(start.crop_id),
                daily_quota_liters: Number(start.daily_quota_liters), max_liters_per_watering: Number(start.max_liters_per_watering) }),
                "Đã bắt đầu mùa vụ mới", reloadPlant);
            }}>
              <label>Loại cây
                <select value={start.crop_id} onChange={(e) => setStart({ ...start, crop_id: e.target.value })} required>
                  <option value="">-- chọn --</option>
                  {crops.map((c) => <option key={c.CropId} value={c.CropId} disabled={!c.Stages.length}>
                    {c.Name}{!c.Stages.length ? " (chưa có lịch)" : ""}</option>)}
                </select></label>
              <label>Ngày trồng<input type="date" max={todayStr()} value={start.planted_date} onChange={(e) => setStart({ ...start, planted_date: e.target.value })} required /></label>
              <label>Hạn mức (lít / ngày)
                <input type="number" step="0.1" min="0" max={MAX_DAILY_LITERS} value={start.daily_quota_liters} onKeyDown={blockSign}
                  onChange={(e) => setStart({ ...start, daily_quota_liters: clampMax(e.target.value, MAX_DAILY_LITERS) })} required />
                <small className="conv">{sec(start.daily_quota_liters)}</small></label>
              <label>Tối đa mỗi lần tưới (lít)
                <input type="number" step="0.05" min="0.05" max={MAX_LITERS_PER_WATERING} value={start.max_liters_per_watering} onKeyDown={blockSign}
                  onChange={(e) => setStart({ ...start, max_liters_per_watering: clampMax(e.target.value, MAX_LITERS_PER_WATERING) })} required />
                <small className="conv">{sec(start.max_liters_per_watering)}</small></label>
              <label className="wide">Ghi chú<input maxLength={300} value={start.note} onChange={(e) => setStart({ ...start, note: e.target.value })} /></label>
              <button className="btn water">Bắt đầu mùa vụ</button>
            </form>
            <div className="pump-info">Máy bơm chỉ bật / tắt, cố định <b>60 giây = 2 lít</b> (1 lít = 30 giây).</div>
          </article>
        )}

        <article className="panel">
          <h2>Lịch sử mùa vụ</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Cây</th><th>Ngày trồng</th><th>Kết thúc</th><th className="num">Đã tưới</th><th>Người tạo</th><th>Trạng thái</th></tr></thead>
              <tbody>
                {!plantings.length && <tr><td colSpan="6" className="muted">Chưa có mùa vụ.</td></tr>}
                {plantings.map((p) => (
                  <tr key={p.PlantingId} className={p.Status === "ACTIVE" ? "open-row" : ""}>
                    <td>{p.CropName}</td><td>{fmtDate(p.PlantedDate)}</td><td>{p.EndedAt ? fmtDate(p.EndedAt) : "--"}</td>
                    <td className="num">{fmt(p.TotalLiters, 2)} L</td><td>{p.CreatedByName || "--"}</td>
                    <td><span className={"tag " + (p.Status === "ACTIVE" ? "APPLIED" : "EXPIRED")}>{p.Status === "ACTIVE" ? "Đang chạy" : "Đã kết thúc"}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      </div>

      <div>
        <article className="panel">
          <h2>Loại cây</h2>
          <ul className="crop-list">
            {!crops.length && <li className="muted">Chưa có loại cây nào.</li>}
            {crops.map((c) => (
              <li key={c.CropId} className={c.CropId === selected ? "on" : ""} onClick={() => setSelected(c.CropId)}>
                <b>{c.Name}</b>
                <span className="muted"> · {c.Stages.length} giai đoạn · {c.Stages.reduce((a, s) => a + s.DurationDays, 0)} ngày
                  {plant && plant.crop_id === c.CropId && " · đang trồng"}</span>
              </li>
            ))}
          </ul>
          {canCrop && (
            <form className="row" onSubmit={(e) => {
              e.preventDefault();
              run(() => api.addCrop(newCrop), "Đã thêm loại cây", (r) => { setNewCrop({ name: "", description: "" }); setSelected(r.crop_id); });
            }}>
              <input placeholder="Tên loại cây mới" maxLength={100} value={newCrop.name} onChange={(e) => setNewCrop({ ...newCrop, name: e.target.value })} required />
              <input placeholder="Ghi chú (không bắt buộc)" maxLength={300} value={newCrop.description} onChange={(e) => setNewCrop({ ...newCrop, description: e.target.value })} />
              <button className="btn water">+ Thêm loại cây</button>
            </form>
          )}
        </article>

        {crop && (
          <article className="panel">
            <div className="panel-head">
              <h2>Lịch giai đoạn: {crop.Name}</h2>
              {canCrop && crop.PlantingCount === 0 && (
                <button className="btn sm" onClick={() => window.confirm(`Xóa loại cây ${crop.Name}?`) &&
                  run(() => api.deleteCrop(crop.CropId), "Đã xóa loại cây", () => setSelected(null))}>Xóa loại cây</button>
              )}
            </div>
            <p className="hint">Các giai đoạn nối tiếp nhau tính từ ngày trồng. Đất khô hơn mức <b>thấp nhất</b> thì đề xuất tưới,
              tưới tới giữa khoảng thấp nhất – cao nhất thì dừng.</p>
            <form onSubmit={(e) => {
              e.preventDefault();
              const bad = checkStages();
              if (bad) { notify(bad, true); return; }
              run(() => api.saveStages(crop.CropId, stages.map((s) => ({ name: s.name, duration_days: Number(s.duration_days),
                moisture_min: Number(s.moisture_min), moisture_max: Number(s.moisture_max) }))), "Đã lưu lịch giai đoạn", reloadPlant);
            }}>
              <div className="table-wrap">
                <table className="stage-table">
                  <thead><tr><th>#</th><th>Tên giai đoạn</th><th className="num">Số ngày</th><th className="num">Ẩm thấp nhất %</th><th className="num">Ẩm cao nhất %</th><th /></tr></thead>
                  <tbody>
                    {stages.map((s, i) => (
                      <tr key={i}>
                        <td>{i + 1}</td>
                        <td><input value={s.name} maxLength={100} onChange={setS(i, "name")} required disabled={!canCrop} /></td>
                        <td><input type="number" min="1" max={MAX_STAGE_DAYS} step="1" value={s.duration_days} onKeyDown={blockSignDot} onChange={setS(i, "duration_days")} required disabled={!canCrop} /></td>
                        <td><input type="number" min="0" max="100" step="0.5" value={s.moisture_min} onKeyDown={blockSign} onChange={setS(i, "moisture_min")} required disabled={!canCrop} /></td>
                        <td><input type="number" min="0" max="100" step="0.5" value={s.moisture_max} onKeyDown={blockSign} onChange={setS(i, "moisture_max")} required disabled={!canCrop} /></td>
                        <td>{canCrop && stages.length > 1 && <button type="button" className="btn sm" onClick={() => setStages(stages.filter((_, j) => j !== i))}>Xóa</button>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {totalDays > 0 && (
                <div className="timeline">
                  {stages.map((s, i) => Number(s.duration_days) > 0 && (
                    <div key={i} style={{ flex: Number(s.duration_days) }} title={s.name}>{s.name || `GĐ ${i + 1}`}</div>
                  ))}
                </div>
              )}
              <p className="hint">Tổng {totalDays} ngày.</p>
              {canCrop && (
                <div className="row">
                  <button type="button" className="btn" onClick={() => setStages([...stages, emptyStage()])}>+ Thêm giai đoạn</button>
                  <button className="btn water">Lưu lịch giai đoạn</button>
                </div>
              )}
            </form>
          </article>
        )}
      </div>
    </div>
  );
}
