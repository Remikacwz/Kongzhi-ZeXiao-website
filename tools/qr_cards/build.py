"""统一群二维码卡片生成器。
用法:
  python tools/qr_cards/build.py                 # 生成全部（读 groups.csv）
  python tools/qr_cards/build.py --verify        # 生成并逐张解码校验
  python tools/qr_cards/build.py --only 上海大学   # 只生成一所
输出: tools/qr_cards/out/<学校>.png
新增学校: groups.csv 加一行 + logos/<学校>.png 放校徽 → 重跑本脚本。
"""
import json, pathlib, argparse, sys
from PIL import Image, ImageDraw, ImageFont
import qrcode

ROOT=pathlib.Path(__file__).resolve().parent
T=json.loads((ROOT/'template.json').read_text(encoding='utf-8'))
OUT=ROOT/'out'; OUT.mkdir(exist_ok=True)
ECC={'L':qrcode.constants.ERROR_CORRECT_L,'M':qrcode.constants.ERROR_CORRECT_M,
     'Q':qrcode.constants.ERROR_CORRECT_Q,'H':qrcode.constants.ERROR_CORRECT_H}

def font(path, size):
    root=pathlib.Path(r'C:\Windows\Fonts')
    p=root/path
    if not p.exists(): p=root/'msyh.ttc'
    return ImageFont.truetype(str(p), size)

def build(school, payload):
    c=T['canvas']; q=T['qr']
    qr=qrcode.QRCode(version=q['version'], error_correction=ECC[q['error_correction']], border=q['border'])
    qr.add_data(payload); qr.make(fit=False)
    mod=qr.modules_count; box=q['size']//mod
    img=qr.make_image(fill_color=q['dark'], back_color=q['light']).convert('RGB')
    img=img.resize((mod*box, mod*box), Image.NEAREST)
    qcanvas=Image.new('RGB', (q['size'], q['size']), q['light'])
    qcanvas.paste(img, ((q['size']-mod*box)//2,)*2)
    logo=ROOT/'logos'/(school+'.png')
    if logo.exists():
        s=int(q['size']*q['logo_ratio']); pad=q['logo_pad']
        lg=Image.open(logo).convert('RGB').resize((s,s), Image.LANCZOS)
        plate=Image.new('RGB', (s+pad*2, s+pad*2), q['light']); plate.paste(lg,(pad,pad))
        qcanvas.paste(plate, ((q['size']-plate.size[0])//2,)*2)
    card=Image.new('RGB', (c['width'], c['height']), c['background'])
    card.paste(qcanvas, (q['x'], q['y']))
    dr=ImageDraw.Draw(card)
    for key in ('line1','line2'):
        L=T[key]; txt=L['text'].replace('{school}', school)
        dr.text((c['width']//2, L['y']), txt, font=font(L['font'], L['size']), fill=L['color'], anchor='mm')
    op=OUT/(school+'.png'); card.save(op, optimize=True)
    return op

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--verify', action='store_true'); ap.add_argument('--only')
    a=ap.parse_args()
    rows=[]
    for line in (ROOT/'groups.csv').read_text(encoding='utf-8').splitlines()[1:]:
        if not line.strip(): continue
        parts=line.split(',',2); school, gname, payload = parts[0], parts[1], parts[2]
        if a.only and a.only!=school: continue
        rows.append(build(school, payload))
        print('生成', school=rows[-1].name if False else rows[-1].name)
    print('共 %d 张 → %s' % (len(rows), OUT))
    if a.verify:
        try: import zxingcpp
        except ImportError: print('未安装 zxing-cpp，跳过解码校验'); return
        bad=[]
        for line in (ROOT/'groups.csv').read_text(encoding='utf-8').splitlines()[1:]:
            if not line.strip(): continue
            school, gname, payload = line.split(',',2)
            if a.only and a.only!=school: continue
            p=OUT/(school+'.png')
            r=zxingcpp.read_barcodes(Image.open(p).convert('RGB'))
            got=r[0].text if r else None
            if got!=payload: bad.append(school)
        print('解码校验: %d/%d 通过 %s' % (len(rows)-len(bad), len(rows), '✅' if not bad else '⚠️ '+','.join(bad)))

if __name__=='__main__': main()
