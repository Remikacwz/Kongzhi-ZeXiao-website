# 群二维码卡片生成流程

统一版式（944×1164）：纯白底 + 二维码 766×766 @ (89,127) + 两行居中文字。

## 参数（template.json）
- 二维码：version 5（37×37 模块）、纠错 M、模块 20px、无边框、纯黑白
- 校徽：居中，占二维码 22%，白色衬底 12px
- 第一行：学校名，微软雅黑 46 加粗，y=990
- 第二行：群名，微软雅黑 34 常规，y=1076

## 日常用法
```bash
# 1. 新增/修改学校：编辑 groups.csv（school,group_name,qr_payload）
#    需要校徽就放 tools/qr_cards/logos/<学校>.png（168×168，可选）
# 2. 生成
python tools/qr_cards/build.py
# 3. 校验（需要 pip install zxing-cpp qrcode pillow）
python tools/qr_cards/build.py --verify
# 4. 输出在 tools/qr_cards/out/，复制到 专业课选择/images/27考研群/
```

## 重要说明
- **二维码数据必须来自 QQ 客户端导出的原始二维码**（群号无法生成二维码；payload 是 QQ 签发的入群 token）
- 想改版式（尺寸/字号/留白）只改 template.json，全部重跑即可，不会出现"样式漂移"
- 未放 logos/<学校>.png 时不嵌校徽（纯二维码），仍与版式一致
