/**
 * 青蔓 QingMan · 简体中文语言包（zh-CN）
 *
 * 语言包契约（V0.0.44 · 动态语言包）—— 三个具名导出：
 *   LOCALE        语言标签（BCP 47），必须与**文件名**一致
 *   NAME          自描述名（**母语写法**），直接展示在语言选择器中，不随界面语言翻译
 *   dict / helpSections  界面文案与帮助分节结构
 *
 * 新增语言：把满足同一契约的 `<tag>.js` 放进项目根 `locales/` 即可 ——
 * 后端 `/api/locales.js` 自动枚举，语言选择器自动出现该档，无需改任何代码。
 * （V0.3.0：语言包已从 `src/web/locales/` 迁出，不再计入 `src/` 体积预算。）
 *
 * 内容与页面/模块分离：
 *   *.html          只放空壳与 `data-i18n` 键名，一个中文都不写
 *   *.js（UI 模块）  只查表取词，一个中文文案也不写
 *   本文件          全部文案与分节结构
 *
 * 出厂语言之间键集必须完全一致（由 verify.py 静态对齐）。
 * 键名规范：`<模块>.<元素>.<语义>`（§P0-3 L2）。
 * 占位符用 `{name}` 形式，由 `t(key, vars)` 替换。
 */

export const LOCALE = 'zh-CN';

/** 语言自描述名（母语写法）。新增语言包时**必填** —— 后端据此生成语言清单。 */
export const NAME = '简体中文';

/** 界面文案（主界面 + 帮助页 + 模块内部透出给用户的报错）。 */
export const dict = {
  /* ---------- 应用与顶栏 ---------- */
  'app.title': '青蔓 QingMan',
  'app.nameZh': '青蔓',
  'app.nameEn': 'QingMan',

  'topbar.saveTip': '编辑内容自动保存到项目内的 data/editor.json',
  'topbar.save.idle': '未保存',
  'topbar.save.pending': '未保存',
  'topbar.save.saving': '保存中…',
  'topbar.save.saved': '已保存',
  'topbar.save.savedAt': '已保存 {at}',
  'topbar.save.error': '保存失败',
  'topbar.backend.connecting': '连接中…',
  'topbar.backend.ready': '服务就绪',
  'topbar.backend.offline': '服务不可用',
  'topbar.help': '帮助',
  'topbar.helpTip': '查看使用说明',
  'topbar.support': '支持',
  'topbar.supportTip': '赞赏与支持',
  'topbar.more': '更多',
  'topbar.backendTip': '查看服务状态与设置',
  'topbar.logoTip': '点击生成桌面快捷方式',

  /* ---------- 顶栏浮层与弹窗（V0.0.40 · 手册 10.2 节 #6 / #7 / #9） ---------- */
  'dlg.close': '关闭',
  'dlg.cancel': '取消',
  'popMore.service': '服务设置',
  'popMore.support': '支持青蔓',
  'popMore.help': '使用说明',

  'svc.title': '服务设置',
  'svc.intro': '青蔓在你这台电脑上运行，不联网、不上传。',
  'svc.status': '服务状态',
  'svc.state.connecting': '连接中…',
  'svc.state.ready': '已连接',
  'svc.state.offline': '未连接',
  'svc.advanced': '技术信息',
  'svc.addr': '服务地址',
  'svc.version': '服务版本',
  'svc.dataDir': '数据目录',
  'svc.unknown': '未取到',
  'svc.test': '重新检测',
  'svc.testing': '正在检测…',
  'svc.testOk': '连接正常，服务可用。',
  'svc.testFail': '连接失败：{message}',
  'svc.openTpl': '打开模板库目录',
  'svc.openData': '打开数据目录',
  'svc.openOk': '已请求系统打开：{dir}',
  'svc.openDisabled': '自动打开已被关断（QM_NO_GUI_OPEN），请手动前往：{dir}',
  'svc.openMissing': '目录尚不存在，服务运行后会自动创建：{dir}',
  'svc.openUnavailable': '系统无法自动打开，请手动前往：{dir}',
  'svc.note': '如果页面突然打不开，说明后台已停止：双击桌面上的「青蔓 QingMan」快捷方式重新启动即可。',
  'svc.backups': '历史版本…',

  /* --- 历史版本（备份取回 · V0.0.51@r9）--- */
  'backups.title': '历史版本',
  'backups.intro': '每次保存前都会留一版。挑一版恢复即可，恢复前的当前版也会留档，可再撤回。',
  'backups.loading': '正在读取…',
  'backups.empty': '还没有历史版本 —— 改动并保存一次后，这里就会出现上一版。',
  'backups.colTime': '留档时间',
  'backups.colSize': '大小',
  'backups.colRoot': '根文件夹',
  'backups.archived': '已归档',
  'backups.broken': '文件已损坏',
  'backups.noRoot': '（未命名）',
  'backups.restore': '恢复这一版',
  'backups.confirmTitle': '确认恢复？',
  'backups.confirmBody': '将用「{time}」的版本（根文件夹：{root}）替换当前的编辑内容。磁盘上当前这一版会先自动留档（可再次恢复撤回），但屏幕上尚未保存的改动会丢失。',
  'backups.confirmOk': '恢复',
  'backups.restored': '已恢复历史版本（根文件夹：{root}）。',
  'backups.loadFail': '读取历史版本失败：{message}',
  'backups.restoreFail': '恢复失败：{message}',
  'backups.sizeB': '{n} B',
  'backups.sizeK': '{n} KB',
  'backups.sizeM': '{n} MB',

  /* ---------- 语言与皮肤 ---------- */
  'lang.label': '语言',
  'lang.auto': '跟随系统',
  'lang.zhCN': '中文',
  'lang.enUS': 'English',

  'skin.label': '皮肤',
  'skin.1': '奶白·樱粉',
  'skin.2': '米白·松绿',
  'skin.3': '柔暗·冰蓝',
  'skin.4': '暖白·暖橙',
  'skin.5': '奶黄·暖白',
  'skin.6': '月光序章·钢笔灰',
  'skin.7': '夜空墨蓝',
  'skin.8': '冬日暖阳',
  'skin.9': '初雪',
  'skin.10': '白月光',
  'skin.11': '旧书纸棕',
  'skin.12': '月岩写意',
  'skin.13': '苹果银·蓝',
  'skin.14': '黑金·寂海',
  'skin.15': '奶黄·晨曦',
  'skin.16': '暖灰·琥珀',

  /* ---------- 左栏：模板列表 ---------- */
  /* V0.0.53：`sidebar.title`（「模板工作区」）已删 —— 该标题连同中 / 右两栏的标题
     一起退出主界面（用户裁定）。这一栏的名字现由下方的「模板列表」小标题承担。
     同批订正：帮助页里拿这个标签指路的三句（`help.quickStart.3` / `help.ops.sidebar` /
     `about.tplDirNote`）改为按**真实存在的标签或方位**指，否则指路话指向屏幕上没有的名字。 */
  /* V0.0.51@r12：原 `sidebar.noteLine1`（面板标题下的解说句）已删 —— 它讲的就是
     `help.quickStart.3` 的同一件事，解说文案归帮助页、不占主界面。别在这里加回来。 */

  /* 模板列表（V0.0.11） */
  'template.listTitle': '模板列表',
  'template.loading': '正在读取模板库…',
  'template.unavailable': '模板库不可用：未找到 templates/ 目录',
  'template.empty': '暂无模板',
  /* V0.4.0：解析失败的模板不再"消失"，而是列在这里说明原因。
     单条：`模板「{file}」未能读取（{reason}）`；多条汇总见下一条。 */
  'template.skippedOne': '有 1 个模板文件未能读取：{file}（{reason}）',
  'template.skippedMany': '有 {count} 个模板文件未能读取：{files}（详见悬停提示）',
  'template.needReauthHint': '模板目录的读取授权已过期（浏览器重启或刷新后常会这样），请重新授权后即可看到模板。',
  /* V0.4.5：一键重新授权（仅在线版有这条通道，见 templates.js renderDirUnavailable） */
  'template.reauth': '重新授权',
  'template.reauthFailed': '重新授权失败：{message}（可改用「选择目录」重选该文件夹）',
  'template.skippedTip': '这些文件不会被载入。常见原因：.md 模板的代码围栏未闭合、缩进不是每级 2 个空格、或 .json 不是合法 JSON。',
  'template.stats': '{dirs} 目录 · {files} 文件',
  'template.loadConfirm': '载入模板「{name}」（文件 {file}）？当前编辑的目录树将被替换（可用撤销恢复）。',
  'template.loaded': '已载入模板「{name}」',
  'template.noteAdopted': '（说明取自 {file}）',
  'template.loadFailed': '模板载入失败：{message}',

  /* 新建模板（V0.0.41 · 手册 9.2 节 #7 / 10.2 节 #4） */
  'template.new': '新建',
  'template.newTip': '从零创建一套模板（可选空白或库中任一模板作起点）',
  'template.newTitle': '新建模板',
  'template.newNameLabel': '模板名称',
  'template.newNamePlaceholder': '例如：我的项目模板',
  'template.newDescLabel': '说明（选填）',
  'template.newDescPlaceholder': '一句话描述这套模板的用途',
  'template.newBaseLabel': '起点',
  'template.newBaseBlank': '空白（仅根节点）',
  'template.newCreate': '创建',

  /* 另存为模板（V0.0.13） */
  'template.saveAs': '另存为模板',
  'template.saveAsTip': '把正在编辑的目录树保存成一套新模板',
  'template.savePrompt': '模板名称',
  'template.nameEmpty': '模板名称不能为空',
  'template.saved': '已保存模板「{name}」',
  'template.overwritten': '已覆盖模板「{name}」',
  'template.overwriteConfirm': '同名模板「{name}」已存在。覆盖后原模板将移入回收站（templates/.trash，可人工找回）。确认覆盖？',
  'template.saveFailed': '模板保存失败：{message}',
  'template.rename': '重命名',
  'template.renameTip': '重命名这套模板（改文件名与显示名）',
  'template.renamePrompt': '把「{name}」（文件 {file}）重命名为',
  'template.renamed': '已重命名为「{name}」',
  'template.delete': '删除',
  'template.deleteTip': '删除这套模板（移入 templates/.trash，可人工找回）',
  'template.deleteConfirm': '确认删除模板「{name}」（文件 {file}）？将移入回收站（templates/.trash）。',
  'template.deleted': '已删除模板「{name}」（{file}）',
  'template.opFailed': '模板操作失败：{message}',

  /* 模板目录绑定（V0.0.38 · 6E） */
  'template.dirLabel': '模板目录',
  'template.dirUnknown': '（未读取）',
  'template.dirHintDefault': '内置模板库 · 仅空白模板',
  'template.dirHintInvalid': '当前绑定的目录不可用：{reason}',
  'template.dirPick': '选择…',
  'template.dirPickTip': '选择一个目录作为模板库（本机原生目录选择框）',
  'template.dirPastePrompt': '系统选择框打不开（{reason}）：请在「模板目录」框里直接输入路径，按回车生效',
  /* V0.3.7：降级分四路 —— 服务没连上 / 被 env 关断 / 真·能力缺失，处置方式完全不同，
     此前压成同一句话让用户无从判断该修什么。 */
  'template.dirPickerOffline': '没连上本机服务，无法打开系统选择框。请先启动青蔓本机服务，或在「模板目录」框里直接输入路径。',
  'template.dirPickerDisabled': '系统选择框已被环境变量 QM_NO_GUI_PICK 关断：请在「模板目录」框里直接输入路径，按回车生效。',
  'template.dirReasonUnknown': '原因未知',
  'template.dirBound': '已绑定模板目录：{dir}',
  'template.dirAlreadyInUse': '当前已在用这个模板目录，无需更改：{dir}',
  'template.dirResetToBuiltin': '已切回内置模板库（包内 templates/），原来的绑定已取消',
  'template.dirEnvShadow': '环境变量已覆盖目录绑定，实际使用：{dir}',
  'template.dirBindFailed': '模板目录绑定失败：{message}',
  'template.refresh': '刷新',
  'template.refreshTip': '重新读取模板列表',

  /* 模板右键菜单 + 导入导出（V0.0.38 · 6E） */
  /* V0.0.51@r11：模板行 ⋮ 常驻入口的可访问名 + tooltip（动作清单与右键**完全同源**） */
  'template.more': '更多操作',
  'template.moreTip': '载入 / 重命名 / 复制 / 导出 / 删除',
  'template.load': '载入',
  'template.duplicate': '复制为副本',
  'template.duplicatePrompt': '为新模板命名（副本）',
  'template.copySuffix': '{name}_副本',
  'template.duplicated': '已复制为「{name}」',
  'template.export': '导出',
  'template.exportJson': '导出为 .json',
  'template.exportMd': '导出为 .md',
  'template.exported': '已导出「{name}」',
  'template.exportFailed': '导出失败：{message}',
  'template.layerBuiltin': '内置',
  'template.layerUser': '用户',
  'template.import': '导入',
  'template.importTip': '从 .json / .md 文件导入模板（可一次选多个）',
  'template.imported': '已导入模板「{name}」',
  'template.importFailed': '导入失败：{message}',
  'template.importOverwriteConfirm': '同名模板「{name}」已存在。覆盖后原模板将移入回收站（可找回）。确认覆盖？',
  'template.importBatchOverwriteConfirm': '有 {n} 套模板与现有同名。覆盖后原模板将移入回收站（可找回）。确认全部覆盖？',
  'template.importBatchResult': '批量导入完成：成功 {ok} 套 · 跳过同名 {skip} 套 · 失败 {fail} 套',

  /* ---------- 后端错误码 → 本地化文案 ----------
   * 键名固定为 `err.<code>`，占位符必须与 src/shared/error-codes.json 逐条一致，
   * 由 tools/verify.py 的「错误码本地化闭包」与「占位符一致性」两道守卫把关。
   * 未登记的码回退后端原文（与既有行为一致）。
   * 含 {message} 的 5 条，其值来自 Python 异常原文，无法翻译 —— 英文界面下混排属预期。
   */
  'err.segmentNotString': '目录名必须是字符串',
  'err.segmentEmpty': '目录名不能为空',
  'err.segmentTooLong': '目录名过长（上限 120 字符）：{name}',
  'err.segmentDot': '目录名不能是 . 或 .. ：{name}',
  'err.segmentIllegalChar': '目录名含非法字符：{name}',
  'err.segmentReserved': '目录名是系统保留名：{name}',
  'err.segmentTrailing': '目录名不能有首尾空白或以点结尾：{name}',
  'err.segmentInvalid': '「{name}」不是合法目录名（{reason}）',
  'err.treeMissing': '缺少目录树数据 tree',
  'err.targetMissing': '缺少目标位置 target',
  'err.targetInvalid': '目标位置不是合法路径：{target}（{reason}）',
  'err.targetTooShallow': '目标位置至少需两级目录，不能是盘符根：{target}',
  'err.targetBlocked': '目标位置位于受保护目录内，已拒绝：{target}（{reason}）',
  'err.targetReserved': '目标位置指向青蔓自身或其上级目录，已拒绝：{target}（{reason}）',
  'err.tooManyNodes': '目录规模超限：目录 {dirs} + 文件 {files} = {total}，上限 {limit}',
  'err.pathConflict': '目标路径已存在同名文件，无法建为目录：{path}',
  'err.pathConflictDir': '目标路径已存在同名目录，无法建为文件：{path}',
  'err.targetDirExists': '目标位置下已存在同名文件夹：{dir}（其中有 {count} 项）。为避免污染已停止；确认要合并时可再次生成并选择「继续合并」——合并只会补建缺失的目录与文件，不覆盖、不删除任何既有内容',
  'err.treeSiblingDuplicated': '同层存在仅大小写不同的节点：{name} 与 {first}（{path}）—— 大小写不敏感的文件系统会把它们合并成同一个，已拒绝以免污染同名目录',
  'err.badJson': '请求体不是合法 JSON 对象',
  'err.badPath': '访问路径不合法',
  'err.notFound': '接口不存在：{path}',
  'err.bodyTooLarge': '请求体过大，上限 {limit} 字节',
  'err.ioError': '磁盘写入失败：{message}',
  'err.internalError': '服务内部错误：{message}',
  'err.hostRejected': '调用来源主机不被允许：{host}',
  'err.originRejected': '调用来源不被允许：{origin}',
  'err.missingGuardHeader': '缺少防护请求头 {header}',
  'err.methodNotAllowed': '请求方法不被允许：{method}',
  'err.editorRootMissing': '编辑态文档缺少 root 节点',
  'err.editorRootNotDir': '编辑态文档的 root 必须是目录节点',
  'err.editorNodeNotObject': '编辑态节点必须是对象：{path}',
  'err.editorNodeBadType': '编辑态节点 type 必须为 dir 或 file：{path}',
  'err.editorNodeBadName': '编辑态节点 name 必须为非空字符串：{path}',
  'err.editorNodeBadId': '编辑态节点 id 必须为非空字符串：{path}',
  'err.editorNodeBadContent': '编辑态文件节点 content 必须是字符串：{path}',
  'err.editorNodeBadChildren': '编辑态目录节点 children 必须是数组：{path}',
  'err.editorIdDuplicated': '编辑态文档存在重复 id：{id}（先出现在 {first}，再次出现在 {again}）',
  'err.editorSiblingDuplicated': '同一层存在重名节点：{name}（{path}）',
  'err.editorTooLarge': '编辑态文档过大，上限 {limit} 字节（当前 {actual}）',
  'err.editorTooManyNodes': '编辑态文档节点过多，上限 {limit} 个',
  'err.editorReadFailed': '读取编辑态文档失败：{message}',
  'err.editorCorrupt': '编辑态文档已损坏，无法解析：{path}',
  'err.editorBackupNotFound': '找不到该历史版本：{id}',
  'err.editorBackupCorrupt': '历史版本已损坏，无法恢复：{name}',
  'err.shortcutTargetMissing': '启动文件不存在：{target}',
  'err.shortcutFailed': '快捷方式生成失败：{message}',
  'err.openDirBadTarget': '未知的目录标识：{target}',
  'err.iconDataMissing': '缺少图标数据 data',
  'err.iconInvalid': '图标文件结构非法（仅接受 PNG-in-ICO）',
  'err.iconTooLarge': '图标过大，上限 {limit} 字节（当前 {actual}）',
  'err.iconWriteFailed': '图标写入失败（磁盘不可写或文件被占用）',
  'err.templateNotFound': '模板不存在：{name}',
  'err.demoDirMissing': '绑定的模板目录已不存在（可能被删除、改名或移动）。请点「选择目录」重新指定，或用「刷新」重试。',
  'err.templateBadJson': '模板文件结构非法：{name}',
  'err.templateReadFailed': '读取模板失败：{name}（{message}）',
  'err.templateNameEmpty': '模板名不能为空',
  'err.templateNameInvalid': '模板名不合法：{name}（仅允许中英文、数字、下划线、连字符）',
  'err.templateNameTooLong': '模板名过长（上限 60 字符）：{name}',
  'err.templateTreeMissing': '缺少目录树数据 tree',
  'err.templateTooManyNodes': '模板规模超限：目录 {dirs} + 文件 {files} = {total}，上限 {limit}',
  'err.templateTooLarge': '模板过大，上限 {limit} 字节（当前 {actual}）',
  'err.templateExists': '同名模板已存在：{name}（不会覆盖，请改名后重试）',
  'err.templateWriteFailed': '模板写入失败：{name}（磁盘不可写或文件被占用）',
  'err.templateDeleteFailed': '删除模板失败：{name}（文件被占用或回收站不可写）',
  'err.templateRenameFailed': '重命名模板失败：{name}（文件被占用或名称冲突）',
  'err.templateDirBlocked': '模板目录不被允许：{dir}（{reason}）',
  'err.templateDirNotWritable': '模板目录不可写：{dir}（{message}）',
  'err.templateBadMarkdown': '模板 Markdown 解析失败：{reason}',
  'err.templateSiblingDuplicated': '模板内同层出现重名节点：{name}（大小写不敏感）',
  'err.templateEmpty': '模板内容为空：未解析出任何节点',

  /* 错误码徽标：技术排查用的稳定标识，与本地化文案并列展示 */
  'err.codeLabel': '错误码：{code}',
  /* 非后端错误码：HTTP 层失败时前端自行造的码，同样走 err.* 前缀以便本地化 */
  'err.httpError': '请求失败（HTTP {status}）',
  'err.networkError': '无法连接后端服务，请确认服务仍在运行：{message}',

  /* ---------- 中栏：生成参数 ---------- */
  'gen.targetLabel': '目标位置',
  'gen.targetPlaceholder': '例如：E:\\我的项目（或点右侧图标选择）',
  'gen.targetPick': '选择…',
  'gen.targetPickTip': '选择一个已存在的目录作为目标位置（本机原生目录选择框）',
  'gen.targetPastePrompt': '系统选择框打不开：请在「目标位置」框里直接输入路径',
  'gen.dryRun': '仅演练（不写盘）',
  'gen.button': '一键生成',
  'gen.buttonTip': '一键生成：按当前目录树在目标位置创建真实目录',

  /* 折叠摘要行（参数区收起后常驻显示当前设定） */
  'gen.summaryEmpty': '未设置目标位置',
  'gen.summaryTarget': '目标 {target}',
  'gen.summaryRoot': '根名 {root}',
  'gen.summaryNoRoot': '不建根',
  'gen.summaryDryRun': '演练中',
  'gen.summaryWrite': '写盘',
  'gen.summarySep': ' · ',

  /* ---------- 中栏：目录树 ---------- */
  /* V0.0.53：`tree.title`（「目录树工作区」）已删 —— 同上，标题退出主界面。 */
  'tree.canvasLabel': '目录树',
  'tree.addChild': '新建子节点',
  'tree.rename': '重命名',
  'tree.delete': '删除',
  'tree.clearRoot': '清空…',
  'tree.clearRootConfirm': '清空整棵目录树的内容（根名「{name}」重置为空）？此操作可撤销。',
  'tree.undo': '撤销',
  'tree.redo': '重做',
  'tree.expandAll': '全部展开',
  'tree.collapseAll': '全部折叠',
  /* V0.0.50 · I 组：工具栏由文字按钮改为纯线性图标，
     可访问名继续用上面这批短词，功能描述统一移入悬停 tooltip。 */
  'tree.undoTip': '撤销：回退上一步编辑（Ctrl+Z）',
  'tree.redoTip': '重做：恢复被撤销的编辑（Ctrl+Y）',
  'tree.addChildTip': '新建子节点：在选中目录下添加一个子目录',
  'tree.renameTip': '重命名：修改选中节点名称（F2）',
  'tree.deleteTip': '删除：移除选中节点及其全部子节点（有二次确认）',
  'tree.expandAllTip': '全部展开：展开目录树所有层级',
  'tree.collapseAllTip': '全部折叠：折叠目录树所有层级',
  'tree.newDirPrompt': '新目录名称',
  'tree.newDirDefault': '新建目录',
  'tree.renamePrompt': '重命名',
  'tree.rootNoName': '（不建根）',
  'tree.emptyHint': '尚未添加子目录 · 点上方「新建子节点」添加第一个',
  'tree.deleteConfirm': '确认删除「{name}」及其全部子节点？',
  'tree.copyPath': '复制路径',
  /* V0.0.43 · G 组：工具栏三个语义组（读屏用，视觉上靠组间距 + 软竖线区分） */
  'tree.groupEdit': '编辑',
  'tree.groupView': '视图',
  'tree.groupOutput': '输出',
  /* V0.0.50 · I 组：「另存为模板」自模板区移入操作带，独立成组 */
  'tree.groupSave': '保存',
  /* V0.0.43 · F 组：多选批量 */
  'tree.batchInfo': '已选 {n} 项',
  'tree.batchMoveHint': '拖动其中一项可整组移动',
  'tree.batchDelete': '删除选中',
  'tree.batchCopy': '复制选中路径',
  'tree.batchClear': '取消选择',
  /* V0.0.50 · I 组：批量条同样去文字（照设计稿的图标语言，但语义按本项目实况） */
  'tree.batchDeleteTip': '删除选中：移除选中节点及其全部子节点（可用撤销恢复）',
  'tree.batchCopyTip': '复制选中路径：把选中节点的路径批量复制到剪贴板',
  'tree.batchClearTip': '取消选择：退出多选状态',
  'tree.batchDeleteConfirm': '确认删除选中的 {n} 个节点及其全部子节点？（可用撤销恢复）',
  'tree.batchDeleteRoot': '选中的项里含根节点，根节点不可删除',
  'tree.addMultiBlocked': '多选状态下不可新建子节点，请先取消多选',
  'tree.renameMultiBlocked': '多选状态下不可重命名，请先取消多选',

  /* ---------- 右栏：检视器（属性 / 源码） ---------- */
  /* V0.0.53：`inspector.title`（「属性工作区」）已删 —— 同上；右上角那两颗
     「属性 ⇄ 源码」切换按钮留在原位（`.insp-head` 补 justify-content: flex-end 钉住）。 */
  /* V0.0.43 · H 组：属性 ⇄ 源码 双模式 */
  'inspector.modeLabel': '检视器视图',
  'inspector.modeProp': '属性',
  'inspector.modeSrc': '源码',
  'inspector.sourceEmpty': '未选中节点',
  /* V0.0.43 · F × H：多选时检视器进入聚合态 */
  'inspector.multiTitle': '{n} 项选中',
  'inspector.multiType': '多项',
  'inspector.multiParents': '多个位置',
  'inspector.multiNoteDisabled': '多选时不可编辑说明',
  'inspector.name': '名称',
  'inspector.type': '类型',
  'inspector.typeDir': '目录',
  'inspector.typeFile': '文件',
  'inspector.path': '路径',
  'inspector.depth': '深度',
  'inspector.dirs': '子目录',
  'inspector.files': '文件',
  'inspector.resultTitle': '生成结果',
  'inspector.resultEmpty': '尚未生成',
  'inspector.genFailed': '生成失败\n{code}：{message}',
  'inspector.noteTitle': '说明',
  'inspector.notePlaceholder': '为该节点写一段说明（纯文本）…',
  'inspector.copy': '复制',
  'inspector.copyNameTip': '复制节点名称',
  'inspector.copyPathTip': '复制节点路径',
  'inspector.copyNote': '复制说明',
  'inspector.copyNoteTip': '复制节点说明',

  /* ---------- 状态栏 ---------- */
  'status.ready': '就绪',
  'status.readyWith': '就绪 · {nameZh} {app}',
  'status.count': '目录 {dirs} · 文件 {files}',
  'status.restored': '已恢复上次编辑内容',
  'status.restoredAt': '已恢复上次编辑内容（{at}）',
  'status.addedDir': '已新建目录「{name}」',
  'status.renamed': '已重命名为「{name}」',
  'status.deleted': '已删除「{name}」',
  'status.clearedRoot': '已清空目录树 · 根名已重置为空',
  'status.moved': '已移动「{name}」至「{to}」',
  /* V0.0.43 · F 组：批量操作回执 */
  'status.batchDeleted': '已删除 {n} 个节点',
  'status.batchMoved': '已移动 {n} 个节点至「{to}」',
  'status.dryRunning': '演练中…',
  'status.writing': '正在写入磁盘…',
  'status.dryDone': '演练完成：目录 {dirs} · 文件 {files} · 已存在 {existed}',
  'status.genDone': '生成完成：目录 {dirs} · 文件 {files} · 已存在 {existed}',
  'status.noteUpdated': '已更新「{name}」的说明',
  'status.genFailed': '生成失败：{message}',
  'status.genCancelled': '已取消（目标位置下已有同名文件夹，未写入任何内容）',
  'status.backendOffHint': '后端未连接，请通过 start.bat 启动',

  /* ---------- 撤销 / 重做 ---------- */
  'status.undid': '已撤销',
  'status.redid': '已重做',
  'toast.cannotUndo': '没有可撤销的操作',
  'toast.cannotRedo': '没有可重做的操作',

  /* ---------- 桌面快捷方式 ---------- */
  'shortcut.title': '创建桌面快捷方式',
  'shortcut.confirm': '在桌面生成「青蔓 QingMan」快捷方式？',
  'shortcut.done': '快捷方式已生成',
  'shortcut.fileName': '青蔓 QingMan.lnk',
  'shortcut.downloaded': '（已下载）',
  'shortcut.failed': '快捷方式生成失败：{message}',

  /* ---------- 轻提示 ---------- */
  'toast.selectDirFirst': '请先选中一个目录节点',
  'toast.nameEmpty': '名称不能为空',
  'toast.siblingExists': '「{name}」已存在于该目录下',
  'toast.rootDeleteBlocked': '根节点不可删除',
  'toast.moveMissing': '要移动的节点已不存在',
  'toast.moveNotDir': '只能移动到目录节点下',
  'toast.moveCycle': '不能把目录移到它自己的子目录下',
  'toast.moveRoot': '根节点不可移动',
  'toast.targetRequired': '请先填写目标位置',
  'toast.dryDone': '演练完成，未写入磁盘',
  'toast.generatedTo': '已生成到 {root}',
  'toast.mergeConfirm': '目标位置下已存在同名文件夹：\n{dir}\n（其中有 {count} 项）\n\n继续只会在其中「补建缺失」的目录与文件，不会覆盖、不会删除任何既有内容。\n确认要继续合并吗？',
  'toast.copied': '已复制到剪贴板',
  'toast.copyFailed': '复制失败（浏览器未授权剪贴板）',
  'toast.batchCopied': '已复制 {n} 条路径',
  'toast.saveFailed': '保存失败：{message}',
  'toast.dupIdBlocked': '检测到重复 id（{ids}），已阻止保存',
  'toast.docDupId': '文档存在重复 id：{ids}',
  'toast.restoreFailed': '读取上次编辑内容失败：{message}',
  'toast.backendOff': '后端未连接：{message}',
  'toast.serviceBack': '服务已恢复。请刷新页面（F5）以载入已保存的目录树。',

  /* ---------- 默认示例文档（用户能直接看到的初始内容） ---------- */
  'sample.root': '青蔓示例项目',
  'sample.materials': '素材',
  'sample.output': '产出',
  'sample.raw': '原始素材',
  'sample.tidied': '已整理',
  'sample.readme': '说明.md',
  'sample.readmeContent': '# 说明\n\n本目录骨架由青蔓 QingMan 生成。\n',

  /* ---------- 模块内部（面向用户透出的报错 / 诊断） ---------- */
  'list.separator': '、',
  'api.nonJson': '后端返回非 JSON（HTTP {status}）',
  'bus.handlerError': '[bus] 事件 {type} 的处理函数抛错：',
  'doc.nodeNotObject': '文档节点非法（{path}）：应为对象',
  'doc.nodeBadType': '文档节点非法（{path}）：type 必须为 dir 或 file',
  'doc.nodeBadName': '文档节点非法（{path}）：name 必须为非空字符串',
  'doc.nodeBadChildren': '文档节点非法（{path}.children）：应为数组',

  /* ---------- 帮助页 ---------- */
  'help.docTitle': '青蔓 QingMan · 使用说明',
  'help.titleTag': '使用说明',
  'help.navTitle': '目录',
  'help.back': '返回主界面',
  'help.backTip': '回到主界面（本页保持打开，不打断正在编辑的目录树）',
  'help.footer': '青蔓 QingMan · 本地离线运行 · 版本号仅在本页展示',

  /* 后端离线时的兜底版本号。必须与项目根 VERSION 一致（由 verify.py 守卫，禁止写死后漂移）。 */
  'help.versionFallback': 'V0.4.7',
  'help.versionStale': '【后端未连接，此为本机记录值】',

  'about.version': '版本号',
  'about.backend': '后端',
  'about.backendOn': '已连接',
  'about.backendOff': '未连接',
  'about.app': '应用名称',
  // V0.0.51@r6：模板库位置由侧栏写死行移入帮助页，取后端实测值（随绑定变化）。
  // 键名刻意避开 V0.0.41 删除的 about.note —— 那条是「设计纪律」脚注，性质不同。
  'about.tplDir': '模板库位置',
  'about.tplDirBuiltin': '（内置）',
  'about.tplDirUnknown': '未连接后端，暂不可读',
  'about.tplDirNote': '模板库位置可在左栏「模板目录」那一行的文件夹图标处更改绑定，改完立即生效；未绑定时使用程序内置目录。',
  /* 「文档入口」与「版本号说明行」按手册 10.2 节 #10 删除（V0.0.41）—— 前者是开发文档
     入口（不开放给用户），后者是设计纪律而非给用户读的文字。故 about.docs /
     about.docsValue / about.note 三键一并退场（中英同步删，保 7b-3 键对齐）。 */

  'help.lead': '青蔓 QingMan 是一个本地离线运行的目录结构设计工具：可视化编辑目录树，一键在磁盘上生成真实目录。',

  'help.templates.title': '模板库',
  'help.templates.1': '程序只自带一张空白模板。业务模板（16 套）放在单独的模板包压缩包里，按需下载，不随程序附带。',
  'help.templates.2': '把压缩包解压到模板库目录即可（默认是程序目录下的 templates；可在「服务设置」里点图标打开该目录）。.json 与 .md 两种格式都认。',
  'help.templates.3': '解压后回到主界面，模板列表会在几秒内自动出现；导入同名模板时会询问是否覆盖，旧模板移入回收站、可找回。',
  'help.templates.4': '右键模板可导出：.json 便于再导入，.md 便于阅读与放进版本库，两种内容等价。',
  'help.shortcut.title': '创建桌面快捷方式',
  'help.shortcut.1': '左上角那个「青蔓 QingMan」标志本身就是按钮：点它，会在桌面生成一个启动快捷方式，以后双击桌面图标即可打开。',
  'help.shortcut.2': '生成前会先问一次「是否在桌面创建」。快捷方式的图标会跟着当前皮肤配色走，换肤后重新点一次即可更新。',
  'help.shortcut.3': '如果桌面不可写（公司受管电脑、只读桌面等），会改为下载一个 .lnk 文件，把它拖到桌面同样能用。',
  'help.shortcut.4': '快捷方式指向程序目录里的 start.bat。把程序目录移动、改名或换盘之后，旧图标会失效 —— 重新点一次标志生成即可。',
  'help.templates.5': '没绑定外部目录时，用的是程序内置的模板库，里面只有一张空白模板 —— 这是正常的，不是出错。想用更多模板，可把模板包解压进该目录，或点模板目录那一行的文件夹图标改绑到自己的目录。',
  'help.templates.6': '如果绑定行提示目录无效（不存在、在系统区、或指向程序自身），模板列表会退回内置库；按提示改绑一个普通文件夹即可。',
  'help.skin.title': '皮肤',
  'help.skin.1': '顶栏右侧的调色板按钮是皮肤选择器，共 16 款；皮肤只改配色，不改布局、字号与按钮位置，换肤不会改变操作方式。',
  'help.skin.2': '选过的皮肤会被记住，下次打开仍用它。若已生成桌面快捷方式，换肤后图标会随之更新（程序需保持运行）。',
  'help.skin.3': '皮肤文件放在 src/web/css/skins/ 下，每个文件是一组颜色变量；组件样式不感知皮肤，因此不会出现某款皮肤下按钮错位。',
  'help.skin.4': '想自己做一款皮肤：复制一份 s01 改颜色，再到 src/web/js/i18n/skins.js 注册一行即可（属于开发操作，普通使用不需要）。',
  'help.i18n.title': '语言',
  'help.i18n.1': '语言在「更多」菜单里切换，默认跟随系统；切换后立即生效，不需要刷新。',
  'help.i18n.2': '每门语言是 locales/ 下的一个语言包文件（如 zh-CN.js / en-US.js）；新增一门语言只需放入一个文件，无需改动程序。',
  'help.i18n.3': '语言包缺失或格式不合规时，界面会保持当前语言并继续可用，不会白屏。',
  'help.i18n.4': '帮助页与主界面使用同一套文案来源，切语言后两处同时变化，不会出现一处中文一处英文。',
  'help.online.title': '在线版与本地版',
  'help.online.1': '青蔓有两种形态，差别只在"写盘通道"。本机版：双击 start.bat，Python 直接写你填的路径。在线版：浏览器里打开，点「生成」后由你点选文件夹，同样写到你本机磁盘。',
  'help.online.2': '在线版的数据都在这个浏览器里：草稿、在线模板、以及最近 5 个历史版本（存在浏览器的私有文件系统）。换浏览器、换设备或换域名后就看不见了 —— 搬家请用「服务设置 → 导出备份」。',
  'help.online.3': '在线版写文件夹、绑定模板目录都需要 Edge 或 Chrome，并且由你当场点选授权（浏览器不给网页绝对路径，所以不能手填）。浏览器重启后可能要再确认一次。',
  'help.online.4': '模板目录可以直接绑定本机某个真实文件夹（点选一次即记住）；之后你在资源管理器里改了模板文件，列表会自动刷新。',
  'help.online.5': '在线版可用浏览器菜单的「安装应用」装到桌面或开始菜单，装好后能离线打开。共用电脑时请用隐私窗口，或走「服务设置 → 清空本机数据」。',
  'help.online.6': '在线版「目标位置」点「选择…」选一次就记住：生成时直接写进那个文件夹，不再重复弹框。浏览器不披露绝对路径，所以框里只显示文件夹名。要换位置再点一次「选择…」。',
  'help.online.7': '要桌面快捷方式：在「服务设置 → 在线版数据」点「安装到桌面」，浏览器会把它装成应用 —— 桌面与开始菜单各得一个图标，还能离线打开。网页本身写不了 .lnk。',
  'help.quickStart.title': '快速开始',
  'help.quickStart.1': '双击项目根目录的 start.bat 启动本地服务',
  'help.quickStart.2': '浏览器自动打开；顶栏右侧那颗状态点呈就绪色即表示服务正常（点它可查看服务状态与设置）',
  'help.quickStart.3': '在左栏「模板列表」里选一套模板直接载入，或在中栏自行编辑目录树',
  'help.quickStart.4': '填写「目标位置」，先保持「仅演练」勾选试跑一次',
  'help.quickStart.5': '确认结果无误后取消勾选，点「一键生成」真实落盘',

  'help.ops.title': '界面说明',
  'help.ops.topbar': '顶栏——左侧是品牌标记与「更多」菜单；右侧两枚都是图标。靠里那颗显示自动保存的状态：钩表示已保存、转圈表示正在保存、叉表示保存失败（鼠标悬停可看到具体状态与时间，读屏也能读出）。靠外那颗是服务状态圆钮：圆点颜色表示服务是否就绪，点它打开服务设置；同样的状态文字在「更多」菜单里也有一行',
  'help.ops.sidebar': '左栏——「模板列表」列出当前模板库中的模板，点击即载入；每行右端有一颗 ⋮，点它弹出与右键完全相同的菜单（载入 / 重命名 / 复制 / 导出 / 删除）。标题右侧两颗图标是「新建」与「导入」；下一行「模板目录」显示当前绑定的模板库位置，其右侧图标用于改绑与刷新（改完立即生效）。把当前目录树存成一套新模板，用中栏工具栏的「另存为模板」：同名模板默认不覆盖，确认后才覆盖，且旧模板移入回收站可找回',
  'help.ops.center': '中栏——顶部是生成参数与工具栏，主体是目录树',
  'help.ops.genBar': '参数区常驻一行，不折叠：上方摘要句（目标位置 · 根名 · 演练或写盘）供生成前核验，下方「目标位置」与「仅演练」两项随时可改',
  'help.ops.inspector': '右栏——顶部可切换「属性 / 源码」两种视图；显示选中节点的名称、类型、路径、深度与统计，以及生成结果',

  'help.tree.title': '目录树操作',
  'help.tree.1': '单击节点选中，右栏属性面板同步刷新',
  'help.tree.2': '「新建子节点」在选中的目录下增加一个子目录',
  'help.tree.3': '「重命名」修改节点名称；根节点名即生成的根文件夹名，可直接改名，清空则不建根文件夹',
  'help.tree.4': '「删除」移除选中节点及其全部子节点（有二次确认）',
  'help.tree.5': '「展开 / 折叠」是一颗切换按钮（不是两颗）：树里还有收起的层级就一键全部展开，已全部展开则一键全部收起；按钮的图标与悬停提示会跟着变，一眼可知这一下会做什么',
  'help.tree.6': '拖拽节点到某个目录上，可把它移动到该目录下（不能移到自己的子目录里）',
  'help.tree.7': '在节点上单击右键可弹出菜单：新建子节点 / 重命名 / 删除 / 复制路径',
  'help.tree.8': '按住 Ctrl / Cmd 单击可多选，Shift 单击选连续一段；Esc 或点空白处取消多选，Ctrl + A 选中除根以外的全部节点。多选后可整组删除、复制路径，或拖动其中一项整组移动',

  'help.kbd.title': '快捷键',
  /* 快捷键表：每条 = 「键位」+「说明」两栏。键位以 `<键名>.keys` 存放，说明沿用 `<键名>` 本身。
     同一操作有多个等价键位时，键位串内用 `|` 分隔（如重做）；`/` 表示同一按键的平台差异（Ctrl 或 Cmd）。
     渲染器（help.js / help-doc.js 的 buildKbd）据此生成「键帽 + 说明」两列表格，键位与说明分列对齐。 */
  'help.kbd.or': '或',
  'help.kbd.save.keys': 'Ctrl / Cmd + S',
  'help.kbd.save': '立即保存（跳过防抖，不等自动保存）',
  'help.kbd.undo.keys': 'Ctrl / Cmd + Z',
  'help.kbd.undo': '撤销上一步编辑',
  'help.kbd.redo.keys': 'Ctrl / Cmd + Y|Ctrl / Cmd + Shift + Z',
  'help.kbd.redo': '重做',
  'help.kbd.delete.keys': 'Delete',
  'help.kbd.delete': '删除选中节点（有二次确认，可撤销）',
  'help.kbd.rename.keys': 'F2',
  'help.kbd.rename': '重命名选中节点',
  'help.kbd.pending': '其余键位待功能面稳定后统一约定，届时同步本页与《项目手册》。',

  'help.safety.title': '安全说明',
  'help.safety.1': '后端仅监听本机回环地址（127.0.0.1），局域网内其他设备无法访问',
  'help.safety.2': '服务端做调用来源校验（Host 白名单 + Origin 严格同源 + 写操作防护头），阻断跨站页面盲发请求',
  'help.safety.3': '不收集任何数据、不上传任何信息；目录树与生成结果都只留在本机',
  'help.safety.4': '「仅演练」模式不写盘；真实生成时已存在的文件一律跳过、不覆盖，且全程不删除任何既有内容',
  'help.safety.5': '删除节点等破坏性操作均有二次确认',

  'help.support.title': '支持青蔓',
  'help.support.lead': '青蔓是本地离线免费工具。如果你觉得它有帮助，欢迎自愿投喂支持持续维护。',
  'help.support.wechat': '微信赞赏码',
  'help.support.qrAlt': '微信赞赏二维码',
  'help.support.thanks': '感谢支持，BUG 佛修。',
  'help.support.goto': '赞赏与支持',
  'help.support.gotoTip': '打开支持页（新标签）',

  'help.about.title': '版本与关于',
  'help.disclaimer.title': '免责声明',
  'help.disclaimer.1': '本软件免费提供，不保证无缺陷，使用风险由使用者自行承担。赞赏属于无偿心意支持，不构成交易，不提供任何额外服务。',

  /* ---------- 支持页（V0.0.18 拆分） ---------- */
  'support.titleTag': '· 支持',
  'support.docTitle': '支持 · 青蔓 QingMan',
  'support.back': '返回编辑器',
  'support.toHelp': '使用说明',
  'support.lead': '青蔓是本地离线免费工具。如果你觉得它有帮助，欢迎自愿投喂支持持续维护。',
  'support.note': '青蔓完全免费、离线运行，赞赏纯属自愿。感谢每一份支持，BUG 佛修。',
};

/**
 * 帮助页分节结构。
 *   kind: 'ol' 有序列表 ／ 'ul' 无序列表 ／ 'note' 提示型单条 ／ 'about' 动态信息表
 *   title / items 一律是 dict 的键名，不是文案本身。
 *   V0.0.18 起「支持」拆为独立页（support.html），此处不再含 support 分节；
 *   about 表内提供跳转链接。
 */
export const helpSections = [
  { id: 'quickStart', title: 'help.quickStart.title', kind: 'ol', items: [
    'help.quickStart.1', 'help.quickStart.2', 'help.quickStart.3',
    'help.quickStart.4', 'help.quickStart.5',
  ] },
  { id: 'ops', title: 'help.ops.title', kind: 'ul', items: [
    'help.ops.topbar', 'help.ops.sidebar', 'help.ops.center', 'help.ops.genBar', 'help.ops.inspector',
  ] },
  { id: 'tree', title: 'help.tree.title', kind: 'ul', items: [
    'help.tree.1', 'help.tree.2', 'help.tree.3', 'help.tree.4', 'help.tree.5',
    'help.tree.6', 'help.tree.7', 'help.tree.8',
  ] },
  { id: 'shortcut', title: 'help.shortcut.title', kind: 'ul', items: [
    'help.shortcut.1', 'help.shortcut.2', 'help.shortcut.3', 'help.shortcut.4',
  ] },
  { id: 'templates', title: 'help.templates.title', kind: 'ul', items: [
    'help.templates.1', 'help.templates.2', 'help.templates.3', 'help.templates.4',
    'help.templates.5', 'help.templates.6',
  ] },
  { id: 'skin', title: 'help.skin.title', kind: 'ul', items: [
    'help.skin.1', 'help.skin.2', 'help.skin.3', 'help.skin.4',
  ] },
  { id: 'i18n', title: 'help.i18n.title', kind: 'ul', items: [
    'help.i18n.1', 'help.i18n.2', 'help.i18n.3', 'help.i18n.4',
  ] },
  { id: 'online', title: 'help.online.title', kind: 'ul', items: [
    'help.online.1', 'help.online.2', 'help.online.3', 'help.online.4', 'help.online.5',
    'help.online.6', 'help.online.7',
  ] },
  { id: 'kbd', title: 'help.kbd.title', kind: 'kbd', note: 'help.kbd.pending', items: ['help.kbd.save', 'help.kbd.undo', 'help.kbd.redo', 'help.kbd.delete', 'help.kbd.rename'] },
  { id: 'safety', title: 'help.safety.title', kind: 'ul', items: [
    'help.safety.1', 'help.safety.2', 'help.safety.3', 'help.safety.4', 'help.safety.5',
  ] },
  { id: 'about', title: 'help.about.title', kind: 'about', note: 'about.tplDirNote', items: [] },
  { id: 'disclaimer', title: 'help.disclaimer.title', kind: 'ul', items: ['help.disclaimer.1'] },
];
