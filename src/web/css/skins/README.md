# 皮肤目录（§P0-3 L5）

存放**皮肤变量覆盖文件**，一个皮肤一个 `.css`。当前内置 **15 款**（`s01-cream-pink` … `s15-cream-sunrise`），
注册表在 `src/web/js/i18n/skins.js`（`cid` → 文件 / 取词键 / 明暗 / `swatch`）。

## 契约

| 项 | 约定 |
|---|---|
| 皮肤是什么 | **一组 `--qm-*` 变量的覆盖值**，不是一整套组件样式 |
| 文件位置 | `src/web/css/skins/<name>.css`，`<name>` 即 `localStorage['qm.skin']` 的值 |
| 装载方式 | `i18n/index.js` 的 `applySkin()`：按 `qm.skin` 动态注入 `<link id="skinLink">`；未选皮肤则不注入任何样式表 |
| 组件 CSS | **不得感知皮肤**（不写 `.skin-dark .btn`、`[data-qm-skin=…]`），只消费变量；由 `tools/verify.py` 把关 |
| 变量来源 | 变量须先在 `tokens.css` 定义；皮肤文件只做**重新赋值**，不得引入新变量名 |
| 深浅主题 | 系统偏好由 `tokens.css` 处理；皮肤用于**显式指定**一套配色 |

## 可访问性契约（WCAG AA，V0.0.39 起）

皮肤变量还须满足**对比度下限**：**16 组配对**（13 文本 AA **4.5** + 3 非文本 AA **3.0**）
由 `verify.py` **7d-4** 逐款校验（**17 基座 × 16 配对**）。⚠️ **勿拿「墨色」当底色** ——
`--qm-accent-ink` 是**前景**语义，当 `background` 会与 `--qm-on-accent` 撞车；悬停底用 `--qm-btn-bg-hi`。
**完整配对表与三项连带见 `docs/皮肤可访问性契约.md`**。

## 写一个皮肤

```css
:root { --qm-bg: #eceff4; --qm-surface: #f6f8fb; /* 只列想改的，其余沿用 tokens.css */ }
```
控制台 `localStorage.setItem('qm.skin', '<name>')` 后刷新即生效（清空恢复默认）；键名固定 `qm.skin`，
与 `qm.lang` 一并由 §P0-3 L6 约定。
