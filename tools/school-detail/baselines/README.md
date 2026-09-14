# 生成基线

## zxb_canonical.json

`generate_pages.py` 的**唯一可信基线**，用于复现 `school_detail/` 下的 133 个页面。

验证记录（2026-09-14）：用该基线重新生成 133 个页面，与线上 `school_detail/` **逐字节 100% 一致**。

```
ZXB_PARSED=tools/school-detail/baselines/zxb_canonical.json \
ZXB_OUT_DIR=<临时目录> \
ZEXIAO_JS=<临时文件> \
python tools/school-detail/generate_pages.py
```

基线已包含的历史修正：
- 录取分析补全（北京邮电大学 / 中国民航大学 / 北京科技大学 等）
- 招生计划：误抓科目代码的 6 格 → 暂无数据（江苏科技大学 999×4、广西科技大学 903×2）
- 招生计划：湖南科技大学按原文修正 → 18 / 19 / 暂无数据
- 数据富化：电子科技大学、西安理工大学复试分数线；青岛科技大学各科均分

⚠️ 重生成请只写到临时目录，比对通过后再覆盖 `school_detail/`。
