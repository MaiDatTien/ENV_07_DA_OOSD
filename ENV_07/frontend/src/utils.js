export const fmt = (v, d = 1) => (v === null || v === undefined ? "--" : Number(v).toFixed(d));

export const fmtTime = (s) =>
  s ? new Date(s).toLocaleString("vi-VN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" }) : "--";

export const fmtDate = (s) => (s ? new Date(s).toLocaleDateString("vi-VN") : "--");

export const STATUS = {
  PROPOSED: "Chờ xử lý",
  OVERRIDDEN: "Đã ghi đè",
  APPLIED: "Đã áp dụng",
  REJECTED: "Từ chối",
  EXPIRED: "Hết hạn",
};

export const SOURCE = { MANUAL: "Bơm tay", AUTO: "Tự động", RECOMMENDATION: "Theo đề xuất" };

export const ROLE = {
  ADMIN: "Quản trị hệ thống",
  MANAGER: "Kỹ sư canh tác",
  FARMER: "Nông dân vận hành",
  VIEWER: "Người xem",
};

export const secondsFor = (liters, flow) => (flow > 0 ? Math.round((liters / flow) * 60) : 0);
export const litersFor = (seconds, flow) => Math.round((seconds / 60) * flow * 100) / 100;

export const REQ_STATUS = { PENDING: "Chờ duyệt", APPROVED: "Đã duyệt", REJECTED: "Từ chối", CANCELLED: "Đã hủy" };
export const PUMP_FLOW = 2;
export const MANUAL_MAX_LITERS = 2;

export const MAX_LITERS_PER_WATERING = 10;
export const MAX_DAILY_LITERS = 1000;
export const MAX_STAGE_DAYS = 3650;

export const blockSign = (e) => {
  if (["-", "+", "e", "E"].includes(e.key)) e.preventDefault();
};

export const blockSignDot = (e) => {
  if (["-", "+", "e", "E", ".", ","].includes(e.key)) e.preventDefault();
};

export const clampMax = (v, max) => {
  if (v === "" || v === null || v === undefined) return "";
  const n = Number(String(v).replace(",", "."));
  if (Number.isNaN(n)) return "";
  if (n < 0) return "0";
  if (max !== undefined && n > max) return String(max);
  return v;
};

export const todayStr = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
