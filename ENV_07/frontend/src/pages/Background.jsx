import React, { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { applyBackground, backgrounds, BG_DEFAULTS } from "../backgrounds.js";

const SCOPES = [
  { key: "login", title: "Ảnh nền trang đăng nhập", hint: "Hiện khi chưa đăng nhập." },
  { key: "app", title: "Ảnh nền trong hệ thống", hint: "Hiện sau khi đăng nhập, cho mọi tài khoản." },
];

export default function Background({ notify, onSaved }) {
  const [cfg, setCfg] = useState(BG_DEFAULTS);
  const [server, setServer] = useState(BG_DEFAULTS);
  const [scope, setScope] = useState("login");

  useEffect(() => {
    api.getBackgrounds().then((b) => { setCfg(b); setServer(b); }).catch(() => {});
  }, []);

  useEffect(() => { applyBackground(cfg[scope]); }, [cfg, scope]);
  const serverRef = useRef(server);
  serverRef.current = server;
  useEffect(() => () => applyBackground(serverRef.current.app), []);

  const cur = cfg[scope];
  const changed = JSON.stringify(cur) !== JSON.stringify(server[scope]);
  const set = (patch) => setCfg({ ...cfg, [scope]: { ...cur, ...patch } });

  const save = async () => {
    try {
      await api.setBackground(scope, cur);
      const next = { ...server, [scope]: cur };
      setServer(next);
      onSaved && onSaved(next);
      notify(scope === "login" ? "Đã lưu ảnh nền trang đăng nhập" : "Đã lưu ảnh nền trong hệ thống");
    } catch (e) { notify(e.message, true); }
  };

  return (
    <article className="panel">
      <h2>Ảnh nền</h2>
      <p className="hint">Chỉ Quản trị được đổi. Thêm ảnh: chép file .jpg / .png / .webp vào thư mục
        <code>frontend/src/images</code>. Đang xem trước trực tiếp trên trang này.</p>

      <div className="unit-switch">
        {SCOPES.map((s) => (
          <button key={s.key} className={scope === s.key ? "on" : ""} onClick={() => setScope(s.key)}>{s.title}</button>
        ))}
      </div>
      <p className="hint">{SCOPES.find((s) => s.key === scope).hint} Đang dùng: <b>{server[scope].name}</b></p>

      <div className="bg-grid">
        {backgrounds.map((b) => (
          <button key={b.name} className={b.name === cur.name ? "on" : ""} onClick={() => set({ name: b.name })}>
            <img src={b.url} alt="" />
            <span>{b.name}</span>
          </button>
        ))}
      </div>
      <div className="row">
        <label>Độ tối lớp phủ{" "}
          <input type="range" min="0" max="85" value={cur.dim} onChange={(e) => set({ dim: Number(e.target.value) })} />
        </label>
        <button className="btn" onClick={() => set(BG_DEFAULTS[scope])}>Về mặc định</button>
        <button className="btn water" onClick={save} disabled={!changed}>{changed ? "Lưu" : "Đã lưu"}</button>
      </div>
    </article>
  );
}
