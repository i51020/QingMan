/**
 * 青蔓 QingMan · 中文取词表（zh-CN）
 *
 * 本文件是**帮助页正文的唯一数据源** —— 内容与页面骨架分离：
 *   help.html  只放空壳与 data-i18n 键名，一个中文都不写
 *   help.js    只负责查表与渲染，一个中文也不写
 *   本文件     全部文案与分节结构
 *
 * 改文案、调分节顺序、增删条目，都只动这一个文件。
 * 后续新增 `en-US.js` 并在 help.js 切换导入即可双语（见 docs/项目约定.md §P0-3）。
 *
 * 键名规范：`<模块>.<元素>.<语义>`，与 §P0-3 L2 一致。
 */

export const LOCALE = 'zh-CN';

/** 页面外壳与动态字段的文案。 */
export const dict = {
  'app.nameZh': '青蔓',
  'app.nameEn': 'QingMan',

  'help.docTitle': '青蔓 QingMan · 使用说明',
  'help.titleTag': '使用说明',
  'help.navTitle': '目录',
  'help.back': '返回主界面',
  'help.backTip': '回到主界面（本页保持打开，不打断正在编辑的目录树）',
  'help.footer': '青蔓 QingMan · 本地离线运行 · 版本号仅在本页展示',

  'help.versionFallback': 'V0.0.1',
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
    'help.ops.sidebar', 'help.ops.center', 'help.ops.inspector',
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
