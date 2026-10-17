/**
 * 青蔓 QingMan · 简体中文语言包（zh-CN）
 *
 * 语言包契约（V0.0.44 · 动态语言包）—— 三个具名导出：
 *   LOCALE        语言标签（BCP 47），必须与**文件名**一致
 *   NAME          自描述名（**母语写法**），直接展示在语言选择器中，不随界面语言翻译
 *   dict / helpSections  界面文案与帮助分节结构
 *
 * 新增语言：把满足同一契约的 `<tag>.js` 放进 `src/web/locales/` 即可 ——
 * 后端 `/api/locales.js` 自动枚举，语言选择器自动出现该档，无需改任何代码。
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
  'svc.intro': '青蔓由本机的一个本地服务驱动：目录树校验、生成落盘、编辑态保存都经由它。',
  'svc.status': '服务状态',
  'svc.state.connecting': '连接中…',
  'svc.state.ready': '已连接',
  'svc.state.offline': '未连接',
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
  'svc.note': '服务只监听本机回环地址（127.0.0.1），局域网内其他设备无法访问。本页面也由这个服务提供 —— 服务停止后页面会一并打不开，此时请双击桌面上的「青蔓 QingMan」快捷方式重新启动。',
  'svc.backups': '历史版本…',

  /* --- 历史版本（备份取回 · V0.0.51@r9）--- */
  'backups.title': '历史版本',
  'backups.intro': '青蔓每次保存前都会把上一版留档。若误改、误清，可从下面挑一版恢复 —— 恢复前的当前版也会先留档，所以恢复本身也能再撤回。',
  'backups.loading': '正在读取…',
  'backups.empty': '暂无历史版本。改动一次并保存后，这里就会出现上一版。',
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
  'template.stats': '{dirs} 目录 · {files} 文件',
  'template.loadConfirm': '载入模板「{name}」？当前编辑的目录树将被替换（可用撤销恢复）。',
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
  'template.renamePrompt': '把「{name}」重命名为',
  'template.renamed': '已重命名为「{name}」',
  'template.delete': '删除',
  'template.deleteTip': '删除这套模板（移入 templates/.trash，可人工找回）',
  'template.deleteConfirm': '确认删除模板「{name}」？将移入回收站（templates/.trash）。',
  'template.deleted': '已删除模板「{name}」',
  'template.opFailed': '模板操作失败：{message}',

  /* 模板目录绑定（V0.0.38 · 6E） */
  'template.dirLabel': '模板目录',
  'template.dirUnknown': '（未读取）',
  'template.dirHintDefault': '未绑定外部目录，当前使用内置模板库（仅空白模板）',
  'template.dirHintInvalid': '当前绑定的目录不可用：{reason}',
  'template.dirPick': '选择…',
  'template.dirPickTip': '选择一个目录作为模板库（本机原生目录选择框）',
  'template.dirPastePrompt': '本机无法打开目录选择框，请粘贴模板目录的绝对路径',
  'template.dirBound': '已绑定模板目录：{dir}',
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
  'template.copySuffix': '{name} 副本',
  'template.duplicated': '已复制为「{name}」',
  'template.export': '导出',
  'template.exported': '已导出「{name}」',
  'template.exportFailed': '导出失败：{message}',
  'template.layerBuiltin': '内置',
  'template.layerUser': '用户',
  'template.import': '导入',
  'template.importTip': '从 .json / .md 文件导入一套模板',
  'template.imported': '已导入模板「{name}」',
  'template.importFailed': '导入失败：{message}',
  'template.importOverwriteConfirm': '同名模板「{name}」已存在。覆盖后原模板将移入回收站（可找回）。确认覆盖？',

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
  'gen.targetPastePrompt': '本机无法打开目录选择框，请粘贴目标位置的绝对路径',
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
  'help.versionFallback': 'V0.0.54',
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
  { id: 'kbd', title: 'help.kbd.title', kind: 'kbd', note: 'help.kbd.pending', items: ['help.kbd.save', 'help.kbd.undo', 'help.kbd.redo', 'help.kbd.delete', 'help.kbd.rename'] },
  { id: 'safety', title: 'help.safety.title', kind: 'ul', items: [
    'help.safety.1', 'help.safety.2', 'help.safety.3', 'help.safety.4', 'help.safety.5',
  ] },
  { id: 'about', title: 'help.about.title', kind: 'about', note: 'about.tplDirNote', items: [] },
  { id: 'disclaimer', title: 'help.disclaimer.title', kind: 'ul', items: ['help.disclaimer.1'] },
];
