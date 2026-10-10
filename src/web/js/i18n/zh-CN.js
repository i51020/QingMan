/**
 * 青蔓 QingMan · 中文取词表（zh-CN）
 *
 * 本文件是**全部用户可见文案的唯一数据源** —— 内容与页面/模块分离：
 *   *.html          只放空壳与 `data-i18n` 键名，一个中文都不写
 *   *.js（UI 模块）  只查表取词，一个中文文案也不写
 *   本文件          全部文案与分节结构
 *
 * 改文案、调分节顺序、增删条目，都只动这一个文件。
 * 英文版本见 `en-US.js`，键集必须与本文件完全一致（由 verify.py 静态对齐）。
 *
 * 键名规范：`<模块>.<元素>.<语义>`（§P0-3 L2）。
 * 占位符用 `{name}` 形式，由 `t(key, vars)` 替换。
 */

export const LOCALE = 'zh-CN';

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
  'topbar.helpTip': '使用说明（新标签打开）',
  'topbar.support': '支持',
  'topbar.supportTip': '赞赏与支持',
  'topbar.logoTip': '点击生成桌面快捷方式',

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

  /* ---------- 左栏：模板工作区 ---------- */
  'sidebar.title': '模板工作区',
  'sidebar.noteLine1': '选一套模板一键载入，或在中间自行编辑目录树。',
  'sidebar.noteLine2': '模板库位置：',

  /* 模板列表（V0.0.11） */
  'template.listTitle': '模板列表',
  'template.loading': '正在读取模板库…',
  'template.unavailable': '模板库不可用：未找到 templates/ 目录',
  'template.empty': '暂无模板',
  'template.stats': '{dirs} 目录 · {files} 文件',
  'template.loadConfirm': '载入模板「{name}」？当前编辑的目录树将被替换（可用撤销恢复）。',
  'template.loaded': '已载入模板「{name}」',
  'template.noteAdopted': '（说明取自 {file}）',
  'template.loadFailed': '模板载入失败：{message}',

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
  'template.renamePrompt': '把「{name}」重命名为',
  'template.renamed': '已重命名为「{name}」',
  'template.delete': '删除',
  'template.deleteTip': '删除这套模板（移入 templates/.trash，可人工找回）',
  'template.deleteConfirm': '确认删除模板「{name}」？将移入回收站（templates/.trash）。',
  'template.deleted': '已删除模板「{name}」',
  'template.opFailed': '模板操作失败：{message}',

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
  'err.shortcutTargetMissing': '启动文件不存在：{target}',
  'err.shortcutFailed': '快捷方式生成失败：{message}',
  'err.iconDataMissing': '缺少图标数据 data',
  'err.iconInvalid': '图标文件结构非法（仅接受 PNG-in-ICO）',
  'err.iconTooLarge': '图标过大，上限 {limit} 字节（当前 {actual}）',
  'err.iconWriteFailed': '图标写入失败（磁盘不可写或文件被占用）',
  'err.templateNotFound': '模板不存在：{name}',
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

  /* 错误码徽标：技术排查用的稳定标识，与本地化文案并列展示 */
  'err.codeLabel': '错误码：{code}',
  /* 非后端错误码：HTTP 层失败时前端自行造的码，同样走 err.* 前缀以便本地化 */
  'err.httpError': '请求失败（HTTP {status}）',

  /* ---------- 中栏：生成参数 ---------- */
  'gen.rootLabel': '根文件夹名',
  'gen.rootPlaceholder': '留空则直接写入目标位置',
  'gen.targetLabel': '目标位置',
  'gen.targetPlaceholder': '例如：E:\\我的项目',
  'gen.dryRun': '仅演练（不写盘）',
  'gen.button': '一键生成',

  /* 折叠摘要行（参数区收起后常驻显示当前设定） */
  'gen.summaryEmpty': '未设置目标位置',
  'gen.summaryTarget': '目标 {target}',
  'gen.summaryRoot': '根名 {root}',
  'gen.summaryDryRun': '演练中',
  'gen.summaryWrite': '写盘',
  'gen.summarySep': ' · ',
  'gen.toggleExpand': '展开生成参数',
  'gen.toggleCollapse': '收起生成参数',

  /* ---------- 中栏：目录树工作区 ---------- */
  'tree.title': '目录树工作区',
  'tree.canvasLabel': '目录树',
  'tree.addChild': '新建子节点',
  'tree.rename': '重命名',
  'tree.delete': '删除',
  'tree.undo': '撤销',
  'tree.redo': '重做',
  'tree.expandAll': '全部展开',
  'tree.collapseAll': '全部折叠',
  'tree.newDirPrompt': '新目录名称',
  'tree.newDirDefault': '新建目录',
  'tree.renamePrompt': '重命名',
  'tree.deleteConfirm': '确认删除「{name}」及其全部子节点？',
  'tree.copyPath': '复制路径',

  /* ---------- 右栏：属性工作区 ---------- */
  'inspector.title': '属性工作区',
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
  'status.moved': '已移动「{name}」至「{to}」',
  'status.dryRunning': '演练中…',
  'status.writing': '正在写入磁盘…',
  'status.dryDone': '演练完成：目录 {dirs} · 文件 {files} · 已存在 {existed}',
  'status.genDone': '生成完成：目录 {dirs} · 文件 {files} · 已存在 {existed}',
  'status.noteUpdated': '已更新「{name}」的说明',
  'status.genFailed': '生成失败：{message}',
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
  'toast.rootRenameBlocked': '根节点名称由「根文件夹名」决定，不在此处重命名',
  'toast.rootDeleteBlocked': '根节点不可删除',
  'toast.moveMissing': '要移动的节点已不存在',
  'toast.moveNotDir': '只能移动到目录节点下',
  'toast.moveCycle': '不能把目录移到它自己的子目录下',
  'toast.moveRoot': '根节点不可移动',
  'toast.targetRequired': '请先填写目标位置',
  'toast.dryDone': '演练完成，未写入磁盘',
  'toast.generatedTo': '已生成到 {root}',
  'toast.copied': '已复制到剪贴板',
  'toast.copyFailed': '复制失败（浏览器未授权剪贴板）',
  'toast.saveFailed': '保存失败：{message}',
  'toast.dupIdBlocked': '检测到重复 id（{ids}），已阻止保存',
  'toast.docDupId': '文档存在重复 id：{ids}',
  'toast.restoreFailed': '读取上次编辑内容失败：{message}',
  'toast.backendOff': '后端未连接：{message}',

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
  'help.versionFallback': 'V0.0.26',
  'help.versionStale': '【后端未连接，此为本机记录值】',

  'about.version': '版本号',
  'about.backend': '后端',
  'about.backendOn': '已连接',
  'about.backendOff': '未连接',
  'about.app': '应用名称',
  'about.docs': '文档入口',
  'about.docsValue': 'docs/项目手册.md · docs/项目约定.md · docs/任务进度.md · CHANGELOG.md',
  'about.note': '版本号只在帮助页展示，主界面不再显示，以免干扰日常操作。',

  'help.lead': '青蔓 QingMan 是一个本地离线运行的目录结构设计工具：可视化编辑目录树，一键在磁盘上生成真实目录。',

  'help.quickStart.title': '快速开始',
  'help.quickStart.1': '双击项目根目录的 start.bat 启动本地服务',
  'help.quickStart.2': '浏览器自动打开，确认顶栏显示「后端已连接」',
  'help.quickStart.3': '在左侧「模板工作区」选一套模板直接载入，或在中间自行编辑目录树',
  'help.quickStart.4': '填写「目标位置」，先保持「仅演练」勾选试跑一次',
  'help.quickStart.5': '确认结果无误后取消勾选，点「一键生成」真实落盘',

  'help.ops.title': '界面说明',
  'help.ops.sidebar': '左栏「模板工作区」——列出 templates/ 下的模板，点击即载入；标题右侧的「另存为模板」把当前目录树存成一套新模板（**同名不会被覆盖**）；下方为骨架自检清单',
  'help.ops.center': '中栏「目录树工作区」——顶部是生成参数与工具栏，主体是目录树',
  'help.ops.genBar': '参数区左上角可点开／收起：收起后只留一行摘要（目标位置 · 根名 · 演练或写盘），当前设定仍一眼可见',
  'help.ops.inspector': '右栏「属性工作区」——选中节点的名称、类型、路径、深度与统计；下方显示生成结果',

  'help.tree.title': '目录树操作',
  'help.tree.1': '单击节点选中，右栏属性面板同步刷新',
  'help.tree.2': '「新建子节点」在选中的目录下增加一个子目录',
  'help.tree.3': '「重命名」修改节点名称；根节点名称由「根文件夹名」决定，不在此处改',
  'help.tree.4': '「删除」移除选中节点及其全部子节点（有二次确认）',
  'help.tree.5': '「全部展开 / 全部折叠」批量切换层级',
  'help.tree.6': '拖拽节点到某个目录上，可把它移动到该目录下（不能移到自己的子目录里）',
  'help.tree.7': '在节点上单击右键可弹出菜单：新建子节点 / 重命名 / 删除 / 复制路径',

  'help.kbd.title': '快捷键',
  'help.kbd.save': 'Ctrl / Cmd + S — 立即保存（跳过防抖，不等自动保存）',
  'help.kbd.undo': 'Ctrl / Cmd + Z — 撤销上一步编辑',
  'help.kbd.redo': 'Ctrl / Cmd + Y 或 Ctrl / Cmd + Shift + Z — 重做',
  'help.kbd.delete': 'Delete — 删除选中节点（有二次确认，可撤销）',
  'help.kbd.rename': 'F2 — 重命名选中节点',
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
  'help.disclaimer.1': '本软件免费提供，不保证无缺陷，使用风险由使用者自行承担。',

  /* ---------- 支持页（V0.0.18 拆分） ---------- */
  'support.titleTag': '· 支持',
  'support.docTitle': '支持 · 青蔓 QingMan',
  'support.back': '返回编辑器',
  'support.toHelp': '使用说明',
  'support.lead': '青蔓是本地离线免费工具。如果你觉得它有帮助，欢迎自愿投喂支持持续维护。',
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
    'help.ops.sidebar', 'help.ops.center', 'help.ops.genBar', 'help.ops.inspector',
  ] },
  { id: 'tree', title: 'help.tree.title', kind: 'ul', items: [
    'help.tree.1', 'help.tree.2', 'help.tree.3', 'help.tree.4', 'help.tree.5',
    'help.tree.6', 'help.tree.7',
  ] },
  { id: 'kbd', title: 'help.kbd.title', kind: 'note', items: ['help.kbd.save', 'help.kbd.undo', 'help.kbd.redo', 'help.kbd.delete', 'help.kbd.rename', 'help.kbd.pending'] },
  { id: 'safety', title: 'help.safety.title', kind: 'ul', items: [
    'help.safety.1', 'help.safety.2', 'help.safety.3', 'help.safety.4', 'help.safety.5',
  ] },
  { id: 'about', title: 'help.about.title', kind: 'about', items: [] },
  { id: 'disclaimer', title: 'help.disclaimer.title', kind: 'ul', items: ['help.disclaimer.1'] },
];
