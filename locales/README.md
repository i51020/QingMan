# 语言包目录（locales）

本目录是青蔓**唯一**的语言包来源。**新增一门语言 = 往本目录放一个 `.js` 文件**，
无需改动任何代码 —— 后端 `/api/locales.js` 会自动枚举，语言选择器自动多出一档。

## 语言包契约

文件必须是 ES Module，导出三项：

```js
/** 语言标签（BCP 47），**必须与文件名一致**（如 `fr-FR.js` → `'fr-FR'`）。 */
export const LOCALE = 'fr-FR';

/** 自描述名（母语写法）—— 直接展示在语言选择器里，不随界面语言翻译。 */
export const NAME = 'Français';

/** 界面文案字典：`'<模块>.<元素>.<语义>': '…'`。占位符用 `{name}`。 */
export const dict = { /* … */ };

/** 帮助页 / 帮助弹窗的分节结构（与出厂语言保持同一 section.id 顺序）。 */
export const helpSections = [ /* … */ ];
```

## 新增一门语言的步骤

1. 复制 `zh-CN.js` 或 `en-US.js` 为 `<tag>.js`（`<tag>` 为 BCP 47 标签，如 `ja-JP`）。
2. 改三处：`LOCALE` 改成新标签、`NAME` 改成该语言的母语名、`dict` 里逐条换成译文。
   `helpSections` 的 `title` / `items` 都是**键名**，若沿用出厂键集会自动取到对应译文；
   自建键集则需在 `dict` 里补齐，否则界面回显键名并打印 `[i18n] missing key`。
3. 刷新页面 —— 语言选择器里即出现该语言，选中即可切换。

> 出厂语言（`zh-CN` / `en-US`）在代码里是**静态内置**的：首屏同步可用，
> 且在直接用 `file://` 打开、后端不可用时仍能降级提供。其余语言按需**动态加载**。

## 校验

`python tools/verify.py` 会检查：① 每个语言包必须同时导出 `LOCALE` / `NAME` / `dict`；
② 出厂语言之间键集严格一致；③ `LOCALE` 与文件名一致。
