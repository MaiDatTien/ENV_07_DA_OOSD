import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { secondsFor } from "../utils.js";

const emptyStage = () => ({ name: "", duration_days: "", moisture_min: "", moisture_max: "" });
const emptyInfo = { name: "", planted_date: "", daily_quota_liters: "", max_liters_per_watering: "" };
const PUMP_FLOW = 2;

export default function PlantSetup({ plant, reloadPlant, notify, can }) {
  const [info, setInfo] = useState(emptyInfo);
  const [stages, setStages] = useState([emptyStage()]);
  const ro = !can("plant.edit");

  useEffect(() => {
    if (!plant) return;
    setInfo({
      name: plant.name,
      planted_date: String(plant.planted_date).slice(0, 10),
      daily_quota_liters: plant.daily_quota_liters,
      max_liters_per_watering: plant.max_liters_per_watering,
    });
    setStages(plant.stages.length ? plant.stages.map((s) => ({
      name: s.name, duration_days: s.duration_days, moisture_min: s.moisture_min, moisture_max: s.moisture_max,
    })) : [emptyStage()]);
  }, [plant]);

  const setI = (k) => (e) => setInfo({ ...info, [k]: e.target.value });
  const setS = (i, k) => (e) => setStages(stages.map((s, j) => (j === i ? { ...s, [k]: e.target.value } : s)));

  const flow = plant?.pump_flow_lpm || PUMP_FLOW;
  const sec = (liters) => (flow > 0 && Number(liters) > 0 ? `= ${secondsFor(Number(liters), flow)} giây bơm` : "");

  const savePlant = async (e) => {
    e.preventDefault();
    try {
      await api.savePlant({
        name: info.name,
        planted_date: info.planted_date,
        daily_quota_liters: Number(info.daily_quota_liters),
        max_liters_per_watering: Number(info.max_liters_per_watering),
      });
      notify("Đã lưu thông tin cây");
      reloadPlant();
    } catch (ex) { notify(ex.message, true); }
  };

  const saveStages = async (e) => {
    e.preventDefault();
    try {
      await api.saveStages(stages.map((s) => ({
        name: s.name, duration_days: Number(s.duration_days),
        moisture_min: Number(s.moisture_min), moisture_max: Number(s.moisture_max),
      })));
      notify("Đã lưu lịch canh tác");
      reloadPlant();
    } catch (ex) { notify(ex.message, true); }
  };

  const totalDays = stages.reduce((a, s) => a + (Number(s.duration_days) || 0), 0);

  return (
    <div className="grid2 even">
      <article className="panel">
        <h2>Thông tin cây trồng</h2>
        {ro && <p className="hint">Chỉ Kỹ sư canh tác hoặc Quản trị được sửa mục này.</p>}
        <form className="form" onSubmit={savePlant}>
          <label className="wide">Tên cây
            <input value={info.name} onChange={setI("name")} required disabled={ro} />
          </label>
          <label className="wide">Ngày trồng
            <input type="date" value={info.planted_date} onChange={setI("planted_date")} required disabled={ro} />
          </label>
          <label>Hạn mức nước (lít / ngày)
            <input type="number" step="0.1" min="0" value={info.daily_quota_liters} onChange={setI("daily_quota_liters")} required disabled={ro} />
            <small className="conv">{sec(info.daily_quota_liters)}</small>
          </label>
          <label>Tối đa mỗi lần tưới (lít)
            <input type="number" step="0.05" min="0.05" value={info.max_liters_per_watering} onChange={setI("max_liters_per_watering")} required disabled={ro} />
            <small className="conv">{sec(info.max_liters_per_watering)}</small>
          </label>
          <div className="wide pump-info">
            <b>Máy bơm:</b> chỉ bật / tắt, cố định <b>60 giây = {flow} lít</b> (1 lít = {secondsFor(1, flow)} giây).
            Hệ thống đổi số lít bạn nhập ra số giây bơm.
          </div>
          {!ro && <button className="btn water">Lưu thông tin cây</button>}
        </form>

        <h3>Hệ thống tưới thế nào</h3>
        <ol className="howto">
          <li>Đất khô hơn mức <b>thấp nhất</b> của giai đoạn → hệ thống đề xuất tưới.</li>
          <li>Tưới từng nhịp: bơm 5 giây (≈ {(5 / 60 * flow).toFixed(2)} lít), chờ 20 giây cho nước thấm, đo lại đất.</li>
          <li>Đất đạt giữa khoảng thấp nhất – cao nhất → <b>dừng</b>. Không bao giờ vượt <b>tối đa mỗi lần tưới</b>{" "}
            và <b>hạn mức trong ngày</b>.</li>
        </ol>
      </article>

      <article className="panel">
        <h2>Lịch canh tác (giai đoạn sinh trưởng)</h2>
        {!plant ? (
          <p className="muted">Lưu thông tin cây trước, sau đó nhập các giai đoạn ở đây.</p>
        ) : (
          <form onSubmit={saveStages}>
            <p className="hint">Các giai đoạn nối tiếp nhau tính từ ngày trồng. Đất khô hơn mức <b>thấp nhất</b> thì
              hệ thống đề xuất tưới, tưới tới giữa khoảng thấp nhất và cao nhất thì dừng.</p>
            <div className="table-wrap">
              <table className="stage-table">
                <thead><tr>
                  <th>#</th><th>Tên giai đoạn</th><th className="num">Số ngày</th>
                  <th className="num">Ẩm thấp nhất %</th><th className="num">Ẩm cao nhất %</th><th />
                </tr></thead>
                <tbody>
                  {stages.map((s, i) => (
                    <tr key={i} className={plant.current_stage && plant.current_stage.order === i + 1 ? "current" : ""}>
                      <td>{i + 1}</td>
                      <td><input value={s.name} onChange={setS(i, "name")} required disabled={ro} /></td>
                      <td><input type="number" min="1" value={s.duration_days} onChange={setS(i, "duration_days")} required disabled={ro} /></td>
                      <td><input type="number" min="0" max="100" step="0.5" value={s.moisture_min} onChange={setS(i, "moisture_min")} required disabled={ro} /></td>
                      <td><input type="number" min="0" max="100" step="0.5" value={s.moisture_max} onChange={setS(i, "moisture_max")} required disabled={ro} /></td>
                      <td>{!ro && stages.length > 1 && (
                        <button type="button" className="btn sm" onClick={() => setStages(stages.filter((_, j) => j !== i))}>Xóa</button>
                      )}</td>
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
            <p className="hint">Tổng {totalDays} ngày.
              {plant.current_stage && <> Hôm nay (ngày {plant.day}) đang ở giai đoạn <b>{plant.current_stage.name}</b>.</>}</p>
            {!ro && (
              <div className="row">
                <button type="button" className="btn" onClick={() => setStages([...stages, emptyStage()])}>+ Thêm giai đoạn</button>
                <button className="btn water">Lưu lịch canh tác</button>
              </div>
            )}
          </form>
        )}
      </article>
    </div>
  );
}
