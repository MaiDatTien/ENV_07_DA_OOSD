import React, { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { fmtDate, ROLE } from "../utils.js";

const ROLE_ORDER = ["ADMIN", "MANAGER", "FARMER", "VIEWER"];

export default function Accounts({ notify, can, me }) {
  const [rows, setRows] = useState([]);
  const [tree, setTree] = useState([]);
  const [f, setF] = useState({ username: "", full_name: "", password: "", role: "FARMER" });
  const manage = can("user.manage");

  const load = useCallback(() => {
    api.roles().then((r) => setTree(r.tree)).catch(() => {});
    if (manage) api.users().then(setRows).catch((e) => notify(e.message, true));
  }, [manage, notify]);
  useEffect(() => { load(); }, [load]);

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    try {
      await api.addUser(f);
      notify("Đã tạo tài khoản " + f.username);
      setF({ username: "", full_name: "", password: "", role: "FARMER" });
      load();
    } catch (ex) { notify(ex.message, true); }
  };
  const [editing, setEditing] = useState(null);
  const startEdit = (u) => setEditing({ UserId: u.UserId, Username: u.Username, full_name: u.FullName, role: u.Role, new_password: "" });
  const saveEdit = async (e) => {
    e.preventDefault();
    try {
      await api.updateUser(editing.UserId, { full_name: editing.full_name, role: editing.role,
                                              new_password: editing.new_password || null });
      notify(`Đã lưu tài khoản ${editing.Username}`);
      setEditing(null);
      load();
    } catch (ex) { notify(ex.message, true); }
  };

  const remove = async (u) => {
    if (!window.confirm(`Xóa tài khoản ${u.Username}?\nNếu tài khoản đã có thao tác trong nhật ký thì sẽ bị KHÓA thay vì xóa hẳn.`)) return;
    try { const r = await api.deleteUser(u.UserId); notify(r.message); load(); }
    catch (ex) { notify(ex.message, true); }
  };
  const activate = async (u) => {
    try { await api.activateUser(u.UserId); notify(`Đã mở khóa ${u.Username}`); load(); }
    catch (ex) { notify(ex.message, true); }
  };

  return (
    <>
      <article className="panel">
        <h2>{manage ? "Cây phân quyền" : "Quyền của bạn"}</h2>
        <p className="hint">
          {manage ? "Mỗi nhánh là một vai trò, bấm vào tên vai trò để thu gọn hoặc mở ra."
                  : <>Bạn đăng nhập với vai trò <b>{ROLE[me.role]}</b> và được làm những việc sau.</>}
        </p>
        <ul className="tree">
          {tree.map((b) => (
            <li key={b.role} className={b.role === me.role ? "mine" : ""}>
              <details open>
                <summary>
                  <span className="t-role">{b.name}</span>
                  <span className="t-count">{b.groups.reduce((a, g) => a + g.items.length, 0)} quyền</span>
                  {b.role === me.role && <span className="t-me">bạn</span>}
                </summary>
                <ul>
                  {b.groups.map((g) => (
                    <li key={g.group}>
                      <span className="t-group">{g.group}</span>
                      <ul>{g.items.map((it) => <li key={it}>{it}</li>)}</ul>
                    </li>
                  ))}
                </ul>
              </details>
            </li>
          ))}
        </ul>
      </article>

      {manage && (
        <div className="grid2 even">
          <article className="panel">
            <h2>Danh sách tài khoản</h2>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Tên đăng nhập</th><th>Họ tên</th><th>Vai trò</th><th>Trạng thái</th><th>Ngày tạo</th><th /></tr></thead>
                <tbody>
                  {rows.map((u) => (
                    <tr key={u.UserId} className={u.IsActive ? "" : "locked-row"}>
                      <td>{u.Username}{u.UserId === me.user_id && <span className="t-me me-badge">bạn</span>}</td>
                      <td>{u.FullName}</td>
                      <td>{ROLE[u.Role]}</td>
                      <td>{u.IsActive ? "Hoạt động" : "Đã khóa"}</td>
                      <td>{fmtDate(u.CreatedAt)}</td>
                      <td className="actions">
                        <button className="btn sm" onClick={() => startEdit(u)}>Sửa</button>{" "}
                        {u.IsActive
                          ? u.UserId !== me.user_id && <button className="btn sm" onClick={() => remove(u)}>Xóa</button>
                          : <button className="btn sm water" onClick={() => activate(u)}>Mở khóa</button>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="hint">Tài khoản đã có thao tác trong nhật ký (duyệt bơm, ghi đè, áp dụng đề xuất…) sẽ bị <b>khóa</b>{" "}
              thay vì xóa hẳn, để giữ lưu vết. Tài khoản bị khóa không đăng nhập được.</p>
          </article>
          <div>
          {editing && (
            <article className="panel edit-panel">
              <h2>Sửa tài khoản: {editing.Username}</h2>
              <form className="form" onSubmit={saveEdit}>
                <label>Họ tên<input value={editing.full_name} onChange={(e) => setEditing({ ...editing, full_name: e.target.value })} required /></label>
                <label>Vai trò
                  <select value={editing.role} onChange={(e) => setEditing({ ...editing, role: e.target.value })}>
                    {ROLE_ORDER.map((r) => <option key={r} value={r}>{ROLE[r]}</option>)}
                  </select>
                </label>
                <label className="wide">Mật khẩu mới (để trống nếu không đổi)
                  <input type="password" value={editing.new_password} minLength={6} autoComplete="new-password"
                         onChange={(e) => setEditing({ ...editing, new_password: e.target.value })} /></label>
                <div className="row wide">
                  <button className="btn water">Lưu thay đổi</button>
                  <button type="button" className="btn" onClick={() => setEditing(null)}>Hủy</button>
                </div>
              </form>
            </article>
          )}
          <article className="panel">
            <h2>Thêm tài khoản</h2>
            <form className="form" onSubmit={submit}>
              <label>Tên đăng nhập<input value={f.username} onChange={set("username")} required minLength={3} /></label>
              <label>Họ tên<input value={f.full_name} onChange={set("full_name")} required /></label>
              <label>Mật khẩu<input type="password" value={f.password} onChange={set("password")} required minLength={6} /></label>
              <label>Vai trò
                <select value={f.role} onChange={set("role")}>
                  {ROLE_ORDER.map((r) => <option key={r} value={r}>{ROLE[r]}</option>)}
                </select>
              </label>
              <button className="btn water">Tạo tài khoản</button>
            </form>
          </article>
          </div>
        </div>
      )}
    </>
  );
}
