import React, { useEffect, useState } from "react";
import { api, session } from "../api.js";

export default function Login({ onLogin }) {
  const [health, setHealth] = useState(null);
  const [form, setForm] = useState({ username: "", password: "", full_name: "", password2: "" });
  const [showPw, setShowPw] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const check = () =>
    api.health().then(setHealth).catch((e) => setHealth({ error: e.message }));
  useEffect(() => { check(); }, []);

  const firstRun = health && health.database && health.has_user === false;
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      if (firstRun) {
        if (form.password !== form.password2) throw new Error("Hai mật khẩu không giống nhau");
        await api.register({ username: form.username, full_name: form.full_name, password: form.password });
      }
      const res = await api.login(form.username, form.password);
      session.set(res);
      onLogin(res.user);
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  };

  let status = "Đang kiểm tra backend…";
  if (health?.error) status = health.error;
  else if (health && !health.database) status = "Backend chạy nhưng chưa kết nối được SQL Server (sa / 123)";
  else if (health) status = "WELCOME";

  return (
    <main className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <div className="login-head">
          <span className="code">ENV-07</span>
          <h1>Sổ tưới tiết kiệm</h1>
          <p>{firstRun ? "Lần đầu sử dụng: tạo tài khoản quản trị" : "Quản lý nước tưới và lịch canh tác"}</p>
        </div>

        {firstRun && (
          <label>Họ tên
            <input value={form.full_name} onChange={set("full_name")} required />
          </label>
        )}
        <label>Tên đăng nhập
          <input value={form.username} onChange={set("username")} autoComplete="username" required autoFocus />
        </label>
        <label>Mật khẩu
          <input type={showPw ? "text" : "password"} value={form.password} onChange={set("password")}
                 autoComplete={firstRun ? "new-password" : "current-password"} required minLength={firstRun ? 6 : undefined} />
        </label>
        {firstRun && (
          <label>Nhập lại mật khẩu
            <input type={showPw ? "text" : "password"} value={form.password2} onChange={set("password2")} required />
          </label>
        )}
        <label className="inline">
          <input type="checkbox" checked={showPw} onChange={(e) => setShowPw(e.target.checked)} /> Hiện mật khẩu
        </label>

        <p className="err">{err}</p>
        <button className="btn water block" disabled={busy || !health?.database}>
          {busy ? "Đang xử lý…" : firstRun ? "Tạo tài khoản và đăng nhập" : "Đăng nhập"}
        </button>
        <p className="login-foot">
          {status}
          {(health?.error || (health && !health.database)) && (
            <> · <a href="#" onClick={(e) => { e.preventDefault(); setHealth(null); check(); }}>thử lại</a></>
          )}
        </p>
      </form>
    </main>
  );
}
