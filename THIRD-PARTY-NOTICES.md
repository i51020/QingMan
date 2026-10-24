# 第三方组件与许可说明 · Third-Party Notices

本项目自身采用 **MIT 许可证**，见仓库根目录 [`LICENSE`](LICENSE)。

本文只说明**分发二进制发布包时**需要一并保留的第三方许可。源码仓库本身不含下文这些组件
（`runtime/` 只在打包时生成），因此**只有「便携发布包」（`QingMan-<版本>-portable.zip`）需要**。

## 便携发布包内随附的运行时

| 组件 | 版本 | 许可证 | 包内许可文件位置 |
|---|---|---|---|
| CPython（Python 解释器 + 标准库 + tkinter） | 3.14.8 | PSF License 2.0 | `runtime/LICENSE.txt` |
| Tcl/Tk（tkinter 依赖） | 9.0 | BSD 风格（Tcl/Tk license） | `runtime/tcl/tk9.0/demos/license.terms` |

**打包口径**（见 `tools/package_release.py` 头部注释）：只对标准 CPython 安装目录做**文件裁剪**
（去掉 `Doc/` `include/` `libs/` `Scripts/` 与 `Lib/` 下的测试、`site-packages` 等），
**不做二进制修补、不捆绑任何第三方 Python 包**。故它仍然是标准 CPython，其许可条款原样适用，
许可文本随包保留，未做任何移除。

## 其它资源

- 界面皮肤（`src/web/css/skins/`）、图标与 logo（`src/web/assets/`）、赞赏二维码
  （`src/web/assets/sponsor-wechat.png`）均为本项目自有，随本项目 MIT 许可一并提供。
- 未使用任何第三方前端框架或 CDN 资源：页面为原生 HTML/CSS/ES Module，离线可用。

## 如果你要再分发

1. 保留根目录 `LICENSE`（本项目 MIT 的版权声明）；
2. 若分发的是便携包，**保留 `runtime/` 下上述许可文件**，不要删除；
3. 不要用「青蔓 / QingMan」的名称暗示你的分支是官方版本（许可证授权的是代码，不含名称与商标）。
