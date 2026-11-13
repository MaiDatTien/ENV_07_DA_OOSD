ROLES = {
    "ADMIN": "Quản trị hệ thống",
    "MANAGER": "Kỹ sư canh tác",
    "FARMER": "Nông dân vận hành",
    "VIEWER": "Người xem",
}

PERMISSIONS = {
    "view.all":      ("Theo dõi",          "Xem số đo, đề xuất, nhật ký bơm",                  {"ADMIN", "MANAGER", "FARMER", "VIEWER"}),
    "crop.edit":     ("Cây trồng & mùa vụ", "Thêm loại cây, nhập lịch giai đoạn",               {"ADMIN", "MANAGER"}),
    "planting.edit": ("Cây trồng & mùa vụ", "Bắt đầu / kết thúc mùa vụ, đặt hạn mức nước",      {"ADMIN", "MANAGER"}),
    "auto.toggle":   ("Tưới theo đề xuất",  "Bật / tắt tưới tự động",                           {"ADMIN", "MANAGER"}),
    "rec.generate":  ("Tưới theo đề xuất",  "Tạo đề xuất từ số đo",                             {"ADMIN", "MANAGER", "FARMER"}),
    "rec.apply":     ("Tưới theo đề xuất",  "Áp dụng đề xuất (bắt đầu tưới)",                   {"ADMIN", "MANAGER", "FARMER"}),
    "rec.override":  ("Tưới theo đề xuất",  "Ghi đè / từ chối đề xuất, bắt buộc lý do",         {"ADMIN", "MANAGER"}),
    "pump.request":  ("Bơm ngoài đề xuất",  "Gửi yêu cầu bơm tay (tối đa 2 lít), bắt buộc lý do", {"ADMIN", "MANAGER", "FARMER"}),
    "pump.approve":  ("Bơm ngoài đề xuất",  "Duyệt / từ chối yêu cầu bơm tay",                  {"ADMIN", "MANAGER"}),
    "pump.stop":     ("Bơm ngoài đề xuất",  "Dừng bơm ngay",                                    {"ADMIN", "MANAGER", "FARMER"}),
    "user.manage":   ("Tài khoản",          "Thêm, sửa, xóa / khóa tài khoản",                  {"ADMIN"}),
    "settings.edit": ("Hệ thống",           "Đổi ảnh nền giao diện cho mọi tài khoản",          {"ADMIN"}),
}


def permissions_of(role: str) -> list[str]:
    return [p for p, (_, _, roles) in PERMISSIONS.items() if role in roles]


def has(role: str, perm: str) -> bool:
    return role in PERMISSIONS.get(perm, ("", "", set()))[2]


def branch(role: str) -> dict:
    groups: dict[str, list[str]] = {}
    for _, (group, label, roles) in PERMISSIONS.items():
        if role in roles:
            groups.setdefault(group, []).append(label)
    return {"role": role, "name": ROLES[role],
            "groups": [{"group": g, "items": items} for g, items in groups.items()]}


def tree_for(role: str) -> list[dict]:
    if has(role, "user.manage"):
        return [branch(r) for r in ROLES]
    return [branch(role)]
