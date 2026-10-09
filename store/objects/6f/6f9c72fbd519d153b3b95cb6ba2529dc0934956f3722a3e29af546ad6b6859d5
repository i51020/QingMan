/**
 * 青蔓 QingMan · 中文取词表（zh-CN）
 *
 * 本文件是**全部用户可见文案的唯一数据源** —— 内容与页面/模块分离：
 *   *.html          只放空壳与 `data-i18n` 键名，一个中文都不写
 *   *.js（UI 模块）  只查表取词，一个中文文案也不写
 *   本文件          全部文案与分节结构
 *
 * 改文案、调分节顺序、增删条目，都只动这一个文件。
 * 后续新增 `en-US.js` 并在 `i18n/index.js` 登记即可双语（见 docs/项目约定.md §P0-3）。
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
  'topbar.backendOn': '后端已连接',
  'topbar.backendOff': '后端未连接',
  'topbar.help': '帮助',
  'topbar.helpTip': '使用说明（新标签打开）',

  /* ---------- 左栏：模板库与自检 ---------- */
  'sidebar.title': '模板库',
  'sidebar.noteLine1': '当前为最小可运行骨架，模板库尚未接入。',
  'sidebar.noteLine2': '模板内容资产已就位：',
  'sidebar.checkTitle': '骨架自检',
  'check.modules': 'ES 模块化加载',
  'check.backend': '本地后端连通',
  'check.model': '目录树数据模型',
  'check.write': '真实落盘能力',

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

  /* ---------- 中栏：工具栏与目录树 ---------- */
  'tree.canvasLabel': '目录树',
  'tree.addChild': '新建子节点',
  'tree.rename': '重命名',
  'tree.delete': '删除',
  'tree.expandAll': '全部展开',
  'tree.collapseAll': '全部折叠',
  'tree.newDirPrompt': '新目录名称',
  'tree.newDirDefault': '新建目录',
  'tree.renamePrompt': '重命名',
  'tree.deleteConfirm': '确认删除「{name}」及其全部子节点？',

  /* ---------- 右栏：属性与生成结果 ---------- */
  'inspector.title': '属性',
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

  /* ---------- 状态栏 ---------- */
  'status.ready': '就绪',
  'status.readyWith': '就绪 · {nameZh} {app}',
  'status.count': '目录 {dirs} · 文件 {files}',
  'status.restored': '已恢复上次编辑内容',
  'status.restoredAt': '已恢复上次编辑内容（{at}）',
  'status.addedDir': '已新建目录「{name}」',
  'status.renamed': '已重命名为「{name}」',
  'status.deleted': '已删除「{name}」',
  'status.dryRunning': '演练中…',
  'status.writing': '正在写入磁盘…',
  'status.dryDone': '演练完成：目录 {dirs} · 文件 {files} · 已存在 {existed}',
  'status.genDone': '生成完成：目录 {dirs} · 文件 {files} · 已存在 {existed}',
  'status.genFailed': '生成失败：{message}',
  'status.backendOffHint': '后端未连接，请通过 start.bat 启动',

  /* ---------- 轻提示 ---------- */
  'toast.selectDirFirst': '请先选中一个目录节点',
  'toast.nameEmpty': '名称不能为空',
  'toast.siblingExists': '「{name}」已存在于该目录下',
  'toast.rootRenameBlocked': '根节点名称由「根文件夹名」决定，不在此处重命名',
  'toast.rootDeleteBlocked': '根节点不可删除',
  'toast.targetRequired': '请先填写目标位置',
  'toast.dryDone': '演练完成，未写入磁盘',
  'toast.generatedTo': '已生成到 {root}',
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

  'help.versionFallback': 'V0.0.5',
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
  'help.quickStart.3': '在左侧「模板库」选模板，或在中间直接编辑目录树',
  'help.quickStart.4': '填写「目标位置」，先保持「仅演练」勾选试跑一次',
  'help.quickStart.5': '确认结果无误后取消勾选，点「一键生成」真实落盘',

  'help.ops.title': '界面说明',
  'help.ops.sidebar': '左栏「模板库」——选择模板，下方为骨架自检清单',
  'help.ops.center': '中栏——顶部是生成参数与工具栏，主体是目录树',
  'help.ops.genBar': '参数区左上角可点开／收起：收起后只留一行摘要（目标位置 · 根名 · 演练或写盘），当前设定仍一眼可见',
  'help.ops.inspector': '右栏「属性」——选中节点的名称、类型、路径、深度与统计；下方显示生成结果',

  'help.tree.title': '目录树操作',
  'help.tree.1': '单击节点选中，右栏属性面板同步刷新',
  'help.tree.2': '「新建子节点」在选中的目录下增加一个子目录',
  'help.tree.3': '「重命名」修改节点名称；根节点名称由「根文件夹名」决定，不在此处改',
  'help.tree.4': '「删除」移除选中节点及其全部子节点（有二次确认）',
  'help.tree.5': '「全部展开 / 全部折叠」批量切换层级',

  'help.kbd.title': '快捷键',
  'help.kbd.pending': '功能面尚未稳定，键位约定待定，本表暂留空。',

  'help.safety.title': '安全说明',
  'help.safety.1': '后端仅监听本机回环地址（127.0.0.1），局域网内其他设备无法访问',
  'help.safety.2': '服务端做调用来源校验（Host 白名单 + Origin 严格同源 + 写操作防护头），阻断跨站页面盲发请求',
  'help.safety.3': '不收集任何数据、不上传任何信息；目录树与生成结果都只留在本机',
  'help.safety.4': '「仅演练」模式不写盘；真实生成时已存在的文件一律跳过、不覆盖，且全程不删除任何既有内容',
  'help.safety.5': '删除节点等破坏性操作均有二次确认',

  'help.about.title': '版本与关于',
  'help.disclaimer.title': '免责声明',
  'help.disclaimer.1': '本软件免费提供，不保证无缺陷，使用风险由使用者自行承担。',
};

/**
 * 帮助页分节结构。
 *   kind: 'ol' 有序列表 ／ 'ul' 无序列表 ／ 'note' 提示型单条 ／ 'about' 动态信息表
 *   title / items 一律是 dict 的键名，不是文案本身。
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
  ] },
  { id: 'kbd', title: 'help.kbd.title', kind: 'note', items: ['help.kbd.pending'] },
  { id: 'safety', title: 'help.safety.title', kind: 'ul', items: [
    'help.safety.1', 'help.safety.2', 'help.safety.3', 'help.safety.4', 'help.safety.5',
  ] },
  { id: 'about', title: 'help.about.title', kind: 'about', items: [] },
  { id: 'disclaimer', title: 'help.disclaimer.title', kind: 'ul', items: ['help.disclaimer.1'] },
];
