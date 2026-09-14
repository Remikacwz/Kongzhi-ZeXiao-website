"""群二维码模块（qr_group）：上传后的封面规范化钩子。

由 content_admin.create_module / update_module 在算完 values 后调用：
    values = normalize_cover(session, school_name, values, created_by)
行为：
  · 非 qr_group 类型 → 原样返回（不影响其它模块）
  · 封面不是本地上传资源（外部链接/历史数据）→ 原样返回
  · 是 qr_group 且为本地上传图 → 用 qr_card 渲染统一标准卡，存成新媒体资源，替换 cover_url
  · qr_card 依赖缺失（服务器未装 zxing-cpp/qrcode/pillow）→ 静默降级为原行为
"""
import pathlib

_DEGRADED = False


def resolve_school_name(session, school_id):
    """用学校 ID 查学校名（失败返回空串，不抛异常）。"""
    try:
        import content_admin as ca
        for item in ca.list_schools(session):
            if str(item.get('id')) == str(school_id):
                return str(item.get('name') or '')
    except Exception:
        pass
    return ''


def normalize_cover(session, school_id, values, existing=None):
    global _DEGRADED
    if _DEGRADED:
        return values
    if str(values.get('type')) != 'qr_group':
        return values
    sid = school_id or (existing or {}).get('school_id') or values.get('school_id')
    school_name = resolve_school_name(session, sid) if sid else ''
    if not school_name:
        return values   # 拿不到学校名 → 不规范化，保持原行为
    url = str(values.get('cover_url') or '')
    if not url.startswith('/uploads/content/'):
        return values
    try:
        import content_admin as ca
        import qr_card
    except Exception:
        _DEGRADED = True
        return values
    source = pathlib.Path(ca.UPLOAD_DIR) / url.rsplit('/', 1)[-1]
    if not source.exists():
        return values
    try:
        card_bytes = qr_card.render_card(source.read_bytes(), school_name or '', str(values.get('title') or ''))
    except qr_card.QrCardError as exc:
        raise ValueError(exc.message) from exc
    asset = ca.save_image_bytes(card_bytes, 'qr', None)
    values['cover_url'] = asset['url']
    return values
