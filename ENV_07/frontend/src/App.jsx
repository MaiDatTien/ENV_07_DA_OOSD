import React, { useCallback, useEffect, useRef, useState } from "react";
import { api, session, setUnauthorizedHandler } from "./api.js";
import { applyBackground, BG_DEFAULTS } from "./backgrounds.js";
import { ROLE } from "./utils.js";
import Login from "./pages/Login.jsx";
import Monitor from "./pages/Monitor.jsx";
import Recommendations from "./pages/Recommendations.jsx";
import CropsPlantings from "./pages/CropsPlantings.jsx";
import PumpLog from "./pages/PumpLog.jsx";
import Accounts from "./pages/Accounts.jsx";
import Background from "./pages/Background.jsx";

const TABS = [
  { id: "monitor", label: "Theo dõi" },
  { id: "recs", label: "Đề xuất tưới" },
  { id: "plant", label: "Cây trồng & mùa vụ" },
  { id: "log", label: "Nhật ký bơm" },
  { id: "accounts", label: "Tài khoản" },
  { id: "bg", label: "Ảnh nền", perm: "settings.edit" },
];

export default function App() {
  const [user, setUser] = useState(() => session.get()?.user || null);
  const [toast, setToast] = useState(null);
  const timer = useRef();

  const [bgs, setBgs] = useState(BG_DEFAULTS);

  useEffect(() => {
    api.getBackgrounds().then(setBgs).catch(() => {});
    setUnauthorizedHandler(() => setUser(null));
  }, []);

  useEffect(() => { applyBackground(user ? bgs.app : bgs.login); }, [user, bgs]);

  const notify = useCallback((msg, bad = false) => {
    setToast({ msg, bad });
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setToast(null), 4000);
  }, []);

  return (
    <>
      <div className="backdrop" />
      {user ? <Shell notify={notify} onLogout={() => setUser(null)} onBackgroundSaved={setBgs} />
            : <Login onLogin={(u) => setUser(u)} />}
      <div className={"toast" + (toast ? " show" : "") + (toast?.bad ? " bad" : "")}>{toast?.msg}</div>
    </>
  );
}

function Shell({ notify, onLogout, onBackgroundSaved }) {
  const [me, setMe] = useState(null);
  const [tab, setTab] = useState("monitor");
  const [plant, setPlant] = useState(undefined);
  const [dbOk, setDbOk] = useState(true);

  const reloadPlant = useCallback(async () => {
    try {
      const p = await api.plant();
      setPlant(p);
      if (!p) setTab("plant");
    } catch (e) { notify(e.message, true); }
  }, [notify]);

  useEffect(() => {
    api.me().then(setMe).catch(() => {});
    reloadPlant();
    api.health().then((h) => setDbOk(h.database)).catch(() => setDbOk(false));
  }, [reloadPlant]);

  const logout = async () => {
    try { await api.logout(); } catch { }
    session.clear();
    onLogout();
  };

  if (!me) return <p className="pad">Đang tải…</p>;

  const can = (perm) => me.permissions.includes(perm);
  const props = { notify, can, plant, reloadPlant, me };

  return (
    <>
      <header className="topbar">
        <div className="brand">
          <span className="code">ENV-07</span>
          <span className="title">Sổ tưới tiết kiệm</span>
        </div>
        {plant && <div className="plant-chip">Mùa vụ: {plant.name} · ngày {plant.day}</div>}
        <div className={"conn " + (dbOk ? "ok" : "bad")}>
          <i />
          <span>{dbOk ? "SQL Server đã kết nối" : "Lỗi SQL Server"}</span>
        </div>
        <div className="who">
          <span>{me.full_name}</span>
          <small>{ROLE[me.role]}</small>
          <button className="btn-out" onClick={logout}>Đăng xuất</button>
        </div>
      </header>

      <nav className="tabs">
        {TABS.filter((t) => !t.perm || can(t.perm)).map((t) => (
          <button key={t.id} className={tab === t.id ? "on" : ""} onClick={() => setTab(t.id)}>{t.label}</button>
        ))}
      </nav>

      <main>
        {plant === null && ["monitor", "recs", "log"].includes(tab) ? (
          <article className="panel notice">
            <h2>Chưa có mùa vụ nào đang chạy</h2>
            <p>Vào tab <b>Cây trồng &amp; mùa vụ</b>: thêm loại cây và lịch giai đoạn, rồi bắt đầu mùa vụ
              (chọn cây, ngày trồng, hạn mức nước).</p>
            {can("planting.edit")
              ? <button className="btn water" onClick={() => setTab("plant")}>Khai báo ngay</button>
              : <p className="muted">Cần tài khoản Kỹ sư canh tác hoặc Quản trị để khai báo.</p>}
          </article>
        ) : (
          <>
            {tab === "monitor" && plant && <Monitor {...props} />}
            {tab === "recs" && plant && <Recommendations {...props} />}
            {tab === "plant" && <CropsPlantings {...props} />}
            {tab === "log" && plant && <PumpLog {...props} />}
            {tab === "accounts" && <Accounts {...props} />}
            {tab === "bg" && can("settings.edit") && <Background notify={notify} onSaved={onBackgroundSaved} />}
          </>
        )}
      </main>
    </>
  );
}
