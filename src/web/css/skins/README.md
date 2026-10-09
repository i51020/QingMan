# 皮肤目录（§P0-3 L5）

本目录存放**皮肤变量覆盖文件**，一个皮肤一个 `.css`。当前为**机制预留**：尚无内置皮肤，
因此目录内只有本说明。

## 契约

| 项 | 约定 |
|---|---|
| 皮肤是什么 | **一组 `--qm-*` 变量的覆盖值**，不是一整套组件样式 |
| 文件位置 | `src/web/css/skins/<name>.css`，`<name>` 即 `localStorage['qm.skin']` 的值 |
| 装载方式 | `src/web/js/i18n/index.js` 的 `applySkin()`：按 `qm.skin` 动态注入 `<link id="skinLink">`。未选择皮肤时**不注入任何样式表**，行为与不使用皮肤完全一致 |
| 组件 CSS | **不得感知皮肤** —— 不写 `.skin-dark .btn`、`[data-qm-skin="dark"] .panel` 这类选择器，也不得出现 `data-qm-skin`。组件只消费变量，换肤靠覆盖变量完成（由 `tools/verify.py` 把关） |
| 变量来源 | 所有可覆盖变量必须先在 `src/web/css/tokens.css` 定义；皮肤文件只做**重新赋值**，不得引入新变量名 |
| 深浅主题 | 系统偏好（`prefers-color-scheme`）由 `tokens.css` 处理；皮肤用于**显式指定**一套配色，与系统偏好无关 |

## 写一个皮肤

```css
/* src/web/css/skins/<name>.css */
:root {
  --qm-bg: #eceff4;
  --qm-surface: #f6f8fb;
  /* …只需列出想改的变量，其余沿用 tokens.css */
}
```

## 激活（当前无 UI，属预留）

浏览器控制台执行一次即可持久生效：

```js
localStorage.setItem('qm.skin', '<name>');   // 清空则恢复默认
location.reload();
```

键名固定为 `qm.skin`，与语言偏好 `qm.lang` 一并由 §P0-3 L6 约定。
