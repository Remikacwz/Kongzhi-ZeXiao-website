"""QQ 群二维码统一格式渲染（后端）。输入 QQ 群保存的原始二维码图片 + 学校名 + 群名，
输出 944×1164 标准卡片 PNG；版式参数来自 tools/qr_cards/template.json（单一来源）。"""
import io, json, pathlib
from PIL import Image, ImageDraw, ImageFont
import qrcode, zxingcpp

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE_PATH = BASE_DIR / 'tools' / 'qr_cards' / 'template.json'
MIN_QR_SIDE = 300
MAX_INPUT_BYTES = 10 * 1024 * 1024
ALLOWED_HOSTS = ('qm.qq.com', 'qq.com')
ECC = {'L': qrcode.constants.ERROR_CORRECT_L, 'M': qrcode.constants.ERROR_CORRECT_M,
       'Q': qrcode.constants.ERROR_CORRECT_Q, 'H': qrcode.constants.ERROR_CORRECT_H}
FONT_CANDIDATES = (
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc',
    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
    'C:/Windows/Fonts/msyhbd.ttc', 'C:/Windows/Fonts/msyh.ttc',
)
_fonts = {}

class QrCardError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message

def template():
    return json.loads(TEMPLATE_PATH.read_text(encoding='utf-8'))

def _font(size):
    if size not in _fonts:
        for path in FONT_CANDIDATES:
            if pathlib.Path(path).exists():
                _fonts[size] = ImageFont.truetype(path, size)
                break
        else:
            raise QrCardError('font_missing', '服务器缺少中文字体（请安装 fonts-noto-cjk）')
    return _fonts[size]

def _qr_bbox(pil):
    payload = None; box = None
    try:
        results = zxingcpp.read_barcodes(pil)
    except Exception:
        results = []
    if results:
        payload = results[0].text or None
        pos = getattr(results[0], 'position', None)
        if pos is not None:
            xs, ys = [], []
            for attr in ('top_left', 'top_right', 'bottom_right', 'bottom_left'):
                point = getattr(pos, attr, None)
                if point is not None:
                    xs.append(int(point.x)); ys.append(int(point.y))
            if xs:
                box = (min(xs), min(ys), max(max(xs) - min(xs), max(ys) - min(ys)))
    if box is None:
        gray = pil.convert('L'); width, height = gray.size
        xs, ys = [], []
        for y in range(0, min(height, int(height * 0.82)), 2):
            row = [x for x in range(0, width, 2) if gray.getpixel((x, y)) < 128]
            if row:
                ys.append(y); xs.extend((row[0], row[-1]))
        if xs:
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
            box = (x0, y0, max(x1 - x0, y1 - y0))
    return payload, box

def _looks_like_logo(pil):
    pixels = list(pil.convert('RGB').resize((64, 64)).getdata())
    total = len(pixels)
    colored = sum(1 for r, g, b in pixels if max(r, g, b) - min(r, g, b) > 28)
    dark = sum(1 for r, g, b in pixels if (r + g + b) / 3 < 100)
    return colored / total > 0.05 or dark / total > 0.45 or dark / total < 0.02

def render_card(image_bytes, school, group_name):
    if len(image_bytes) > MAX_INPUT_BYTES:
        raise QrCardError('too_large', '图片超过 10MB，请在 QQ 里重新保存')
    try:
        source = Image.open(io.BytesIO(image_bytes)); source.load()
    except Exception:
        raise QrCardError('invalid_image', '无法读取图片，请重新保存后上传')
    source = source.convert('RGB')
    if source.width < 100 or source.height < 100:
        raise QrCardError('invalid_image', '图片尺寸异常，请上传 QQ 群二维码原图')
    payload, box = _qr_bbox(source)
    if not payload:
        raise QrCardError('no_qr', '未识别到二维码，请上传 QQ 群二维码原图（完整、无裁切）')
    if box is None:
        raise QrCardError('no_qr', '未能定位二维码区域，请确认图片完整')
    if box[2] < MIN_QR_SIDE:
        raise QrCardError('too_small', '二维码太小（当前 %dpx，需 ≥%dpx），请用原图' % (box[2], MIN_QR_SIDE))
    host = payload.split('://', 1)[-1].split('/', 1)[0].lower()
    if not any(host == h or host.endswith('.' + h) for h in ALLOWED_HOSTS):
        raise QrCardError('not_qq', '这不是 QQ 群二维码（识别到：%s）' % payload[:60])
    conf = template(); canvas = conf['canvas']; qr_conf = conf['qr']
    x0, y0, side = box
    x0 = max(0, x0); y0 = max(0, y0)
    side = min(side, source.width - x0, source.height - y0)
    half = int(side * .11)
    logo = source.crop((x0 + side // 2 - half, y0 + side // 2 - half, x0 + side // 2 + half, y0 + side // 2 + half))
    code = qrcode.QRCode(version=qr_conf['version'], error_correction=ECC[qr_conf['error_correction']], border=qr_conf['border'])
    code.add_data(payload)
    try:
        code.make(fit=False)
    except Exception:
        raise QrCardError('encode_failed', '二维码生成失败，请联系管理员')
    module_px = qr_conf['size'] // code.modules_count
    rendered = code.make_image(fill_color=qr_conf['dark'], back_color=qr_conf['light']).convert('RGB')
    rendered = rendered.resize((code.modules_count * module_px, code.modules_count * module_px), Image.NEAREST)
    layer = Image.new('RGB', (qr_conf['size'], qr_conf['size']), qr_conf['light'])
    layer.paste(rendered, ((qr_conf['size'] - rendered.width) // 2, (qr_conf['size'] - rendered.height) // 2))
    logo = None
    for candidate in (BASE_DIR / '专业课选择' / 'images' / '校徽',
                      BASE_DIR / 'tools' / 'qr_cards' / 'logos'):
        for ext in ('.jpg', '.jpeg', '.png', '.webp'):
            path = candidate / (str(school).strip() + ext)
            if path.exists():
                try:
                    logo = Image.open(path).convert('RGB')
                except Exception:
                    logo = None
                if logo is not None:
                    break
        if logo is not None:
            break
    if logo is not None:
        badge_side = int(qr_conf['size'] * qr_conf['logo_ratio']); pad = qr_conf['logo_pad']
        badge = Image.new('RGB', (badge_side + pad * 2, badge_side + pad * 2), qr_conf['light'])
        badge.paste(logo.resize((badge_side, badge_side), Image.LANCZOS), (pad, pad))
        layer.paste(badge, ((qr_conf['size'] - badge.width) // 2, (qr_conf['size'] - badge.height) // 2))
    card = Image.new('RGB', (canvas['width'], canvas['height']), canvas['background'])
    card.paste(layer, (qr_conf['x'], qr_conf['y']))
    drawer = ImageDraw.Draw(card)
    for key, text in (('line1', school), ('line2', group_name)):
        line = conf[key]
        drawer.text((canvas['width'] // 2, line['y']), text, font=_font(line['size']), fill=line['color'], anchor='mm')
    buffer = io.BytesIO(); card.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()
