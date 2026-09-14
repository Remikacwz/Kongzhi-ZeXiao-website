#!/usr/bin/env python3
"""为院校详情库的学校补齐「就业去向」页面。

⚠️ 默认只干跑。另见文件底部 KNOWN-ISSUES：当前 build() 在目标校缺少
   评估数据时不会清除模板里的 A+，也会补出模板独有的区块 —— 修好前请勿 --apply。

规则：
  1. 已存在且含真实数据（无「就业数据整理中」占位文案）的页面 → 跳过，绝不覆盖
  2. 缺失的页面 → 用同板块占位模板生成（写入校名/校徽/办学层次/控制学科评估）
  3. 已是占位页但信息不一致（改名/徽标变化）→ 刷新

用法：python tools/gen_job_pages.py [--dry-run]
"""
import argparse
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
TPL_NAME = '清华大学'                       # 占位模板（该页为"整理中"占位版）
TEMPLATE = ROOT / '就业相关' / '院校就业去向' / 'schools' / f'{TPL_NAME}.html'
OUT_DIR = ROOT / '就业相关' / '院校就业去向' / 'schools'
PLACEHOLDER = '就业数据整理中'
SKIP = {'index', 'route'}


def school_meta(name):
    """从院校详情库页里取 办学层次 + 控制学科评估。"""
    p = ROOT / 'school_detail' / f'{name}.html'
    if not p.exists():
        return None
    m = re.search(r'<div class="meta">([^<]*)</div>', p.read_text(encoding='utf-8'))
    if not m:
        return None
    parts = [x.strip() for x in m.group(1).split('·') if x.strip()]
    tier = parts[0] if parts else ''
    ev = ''
    for x in parts:
        if re.fullmatch(r'[A-C][+-]?|未上榜', x):
            ev = x
    return tier, ev


def build(name, tier, ev):
    s = TEMPLATE.read_text(encoding='utf-8')
    s = s.replace(TPL_NAME, name)
    if tier:
        s = re.sub(r'(<span class="badge"[^>]*>)985(<)', r'\g<1>' + re.escape(tier) + r'\2', s)
    if ev:
        s = s.replace('控制学科 A+', f'控制学科 {ev}')
        s = re.sub(r'(<span class="badge"[^>]*>)A\+?(<)', r'\g<1>' + re.escape(ev) + r'\2', s)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true',
                    help='真正写入文件；不加此参数时只做干跑，不修改任何文件')
    args = ap.parse_args()
    write = args.apply
    if not TEMPLATE.exists():
        raise SystemExit(f'模板缺失: {TEMPLATE}')

    schools = sorted(p.stem for p in (ROOT / 'school_detail').glob('*.html') if p.stem not in SKIP)
    created, refreshed, kept_real, same, no_meta = [], [], [], 0, []
    for n in schools:
        meta = school_meta(n)
        if not meta:
            no_meta.append(n)
            continue
        out = OUT_DIR / f'{n}.html'
        content = build(n, *meta)
        if out.exists():
            cur = out.read_text(encoding='utf-8')
            if PLACEHOLDER not in cur:
                kept_real.append(n)          # 有真实数据 → 绝不覆盖
                continue
            if cur == content:
                same += 1
                continue
            refreshed.append(n)
        else:
            created.append(n)
        if write:
            out.write_text(content, encoding='utf-8', newline='\n')

    mode = '写入模式' if write else '干跑模式（未修改任何文件，加 --apply 才写入）'
    print(f'模式: {mode}')
    print(f'模板: {TEMPLATE.name}')
    print(f'新建 {len(created)} 个: {"、".join(created[:8])}{"..." if len(created) > 8 else ""}')
    print(f'刷新占位页 {len(refreshed)} 个: {"、".join(refreshed[:8])}{"..." if len(refreshed) > 8 else ""}')
    print(f'跳过（有真实数据）{len(kept_real)} 个: {"、".join(kept_real[:8])}{"..." if len(kept_real) > 8 else ""}')
    print(f'跳过（已一致）{same} 个')
    if no_meta:
        print(f'无 meta 信息跳过 {len(no_meta)} 个: {"、".join(no_meta[:6])}')


if __name__ == '__main__':
    main()
