"""学校 QQ 群二维码（独立功能）：上传图片 → 自动生成统一格式 → 只改院校展示位。
独立存储表 school_qr_codes，与内容模块(school_content_modules)完全无关。"""
from __future__ import annotations
import base64
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

CARD_W, CARD_H = 944, 1164


def _ensure_table(conn) -> None:
    conn.execute('CREATE TABLE IF NOT EXISTS school_qr_codes ('
                 'school_id INTEGER PRIMARY KEY, cover_url TEXT NOT NULL, '
                 'updated_by INTEGER, updated_at TEXT NOT NULL)')


def upload_school_qr(session: dict, body: dict) -> dict:
    import content_admin as ca
    import qr_card
    school_id = int(body.get('school_id') or 0)
    if not school_id:
        raise ValueError('缺少 school_id')
    encoded = str(body.get('base64') or '')
    if ',' in encoded:
        encoded = encoded.split(',', 1)[1]
    try:
        data = base64.b64decode(encoded, validate=True)
    except Exception:
        raise ValueError('图片数据无效，请重新选择图片')
    if not data:
        raise ValueError('请选择要上传的二维码图片')
    if len(data) > ca.MAX_IMAGE_BYTES:
        raise ValueError('图片超过 %d MB，请压缩后再上传' % (ca.MAX_IMAGE_BYTES // (1024 * 1024)))
    if not ca._image_kind(data):
        raise ValueError('只能上传 PNG / JPG / WEBP 图片')
    with ca._connect() as conn:
        if not ca._can_manage_school(conn, session, school_id):
            raise PermissionError('没有该院校的管理权限')
        row = conn.execute('SELECT name FROM schools WHERE id=?', (school_id,)).fetchone()
        if not row:
            raise ValueError('院校不存在')
        school_name = str(row['name'] if hasattr(row, 'keys') else row[0])
    try:
        card_bytes = qr_card.render_card(data, school_name, '控制考研交流群')
    except qr_card.QrCardError as exc:
        raise ValueError(exc.message) from exc
    asset = ca.save_image_bytes(card_bytes, 'qr', session.get('user_id'))
    with ca._LOCK, ca._connect() as conn:
        _ensure_table(conn)
        conn.execute('INSERT INTO school_qr_codes(school_id,cover_url,updated_by,updated_at) VALUES(?,?,?,?) '
                     'ON CONFLICT(school_id) DO UPDATE SET cover_url=excluded.cover_url, '
                     'updated_by=excluded.updated_by, updated_at=excluded.updated_at',
                     (school_id, asset['url'], session.get('user_id'), ca._now()))
    return {'school': school_name, 'cover_url': asset['url'], 'size': [CARD_W, CARD_H]}


def get_school_qr(session: dict, school_id: int) -> dict:
    import content_admin as ca
    with ca._connect() as conn:
        if not ca._can_manage_school(conn, session, int(school_id)):
            raise PermissionError('没有该院校的管理权限')
        _ensure_table(conn)
        row = conn.execute('SELECT cover_url FROM school_qr_codes WHERE school_id=?', (int(school_id),)).fetchone()
    url = str(row['cover_url'] if hasattr(row, 'keys') else row[0]) if row else ''
    return {'cover_url': url or '', 'has_qr': bool(url)}


def school_qr_by_name(school_name: str) -> dict:
    import content_admin as ca
    name = str(school_name or '').strip()
    if not name:
        return {'cover_url': '', 'has_qr': False}
    try:
        with ca._connect() as conn:
            _ensure_table(conn)
            row = conn.execute('SELECT q.cover_url FROM school_qr_codes q JOIN schools s ON s.id=q.school_id '
                               'WHERE s.name=? LIMIT 1', (name,)).fetchone()
        url = str(row[0] or '') if row else ''
    except Exception:
        url = ''
    return {'cover_url': url, 'has_qr': bool(url)}
