/**
 * 青蔓 QingMan · English dictionary (en-US)
 *
 * Key set must stay identical to `zh-CN.js`; verify.py enforces alignment.
 * Placeholders use `{name}` and are substituted by `t(key, vars)`.
 */

export const LOCALE = 'en-US';

/** 语言自描述名（母语写法）。新增语言包时**必填** —— 后端据此生成语言清单。 */
export const NAME = 'English';

export const dict = {
  /* ---------- App & topbar ---------- */
  'app.title': 'QingMan',
  'app.nameZh': '青蔓',
  'app.nameEn': 'QingMan',

  'topbar.saveTip': 'Edits are auto-saved to data/editor.json',
  'topbar.save.idle': 'Unsaved',
  'topbar.save.pending': 'Unsaved',
  'topbar.save.saving': 'Saving…',
  'topbar.save.saved': 'Saved',
  'topbar.save.savedAt': 'Saved {at}',
  'topbar.save.error': 'Save failed',
  'topbar.backend.connecting': 'Connecting…',
  'topbar.backend.ready': 'Service ready',
  'topbar.backend.offline': 'Service unavailable',
  'topbar.help': 'Help',
  'topbar.helpTip': 'View the usage guide',
  'topbar.support': 'Support',
  'topbar.supportTip': 'Sponsor & support',
  'topbar.more': 'More',
  'topbar.backendTip': 'View service status & settings',
  'topbar.logoTip': 'Click to create a desktop shortcut',

  /* ---------- Top-bar popovers & dialogs (V0.0.40 · manual 10.2 #6 / #7 / #9) ---------- */
  'dlg.close': 'Close',
  'dlg.cancel': 'Cancel',
  'popMore.service': 'Service settings',
  'popMore.support': 'Support QingMan',
  'popMore.help': 'Usage guide',

  'svc.title': 'Service settings',
  'svc.intro': 'QingMan runs on this computer. It never connects to the internet.',
  'svc.status': 'Service status',
  'svc.state.connecting': 'Connecting…',
  'svc.state.ready': 'Connected',
  'svc.state.offline': 'Not connected',
  'svc.advanced': 'Technical details',
  'svc.addr': 'Service address',
  'svc.version': 'Service version',
  'svc.dataDir': 'Data folder',
  'svc.unknown': 'not available',
  'svc.test': 'Recheck',
  'svc.testing': 'Rechecking…',
  'svc.testOk': 'Connected. The service is available.',
  'svc.testFail': 'Connection failed: {message}',
  'svc.openTpl': 'Open template folder',
  'svc.openData': 'Open data folder',
  'svc.openOk': 'Asked the system to open: {dir}',
  'svc.openDisabled': 'Automatic opening is disabled (QM_NO_GUI_OPEN); go there manually: {dir}',
  'svc.openMissing': 'The folder does not exist yet — the service creates it on startup: {dir}',
  'svc.openUnavailable': 'The system cannot open it automatically; go there manually: {dir}',
  'svc.note': 'The service listens only on the loopback address (127.0.0.1), so other devices on the LAN cannot reach it. This page is served by that same service: once it stops, the page stops loading too — restart it by double-clicking the “QingMan” shortcut on your desktop.',
  'svc.backups': 'History…',

  /* --- History versions (backup restore · V0.0.51@r9) --- */
  'backups.title': 'History',
  'backups.intro': 'QingMan archives the previous version before every save. If something was changed or cleared by mistake, pick a version below to restore it — the current version is archived first, so a restore can itself be undone.',
  'backups.loading': 'Loading…',
  'backups.empty': 'No history yet. Change something and save, and the previous version will appear here.',
  'backups.colTime': 'Archived at',
  'backups.colSize': 'Size',
  'backups.colRoot': 'Root folder',
  'backups.archived': 'Archived',
  'backups.broken': 'File is corrupt',
  'backups.noRoot': '(unnamed)',
  'backups.restore': 'Restore this version',
  'backups.confirmTitle': 'Restore this version?',
  'backups.confirmBody': 'Your current editing content will be replaced by the version from {time} (root folder: {root}). The current on-disk version is archived first (restore it again to undo), but unsaved changes on screen will be lost.',
  'backups.confirmOk': 'Restore',
  'backups.restored': 'History version restored (root folder: {root}).',
  'backups.loadFail': 'Failed to read history: {message}',
  'backups.restoreFail': 'Restore failed: {message}',
  'backups.sizeB': '{n} B',
  'backups.sizeK': '{n} KB',
  'backups.sizeM': '{n} MB',

  /* ---------- Language & skin ---------- */
  'lang.label': 'Language',
  'lang.auto': 'Follow system',
  'lang.zhCN': '中文',
  'lang.enUS': 'English',

  'skin.label': 'Skin',
  'skin.1': 'Cream · Sakura Pink',
  'skin.2': 'Off-white · Pine Green',
  'skin.3': 'Soft Dark · Ice Blue',
  'skin.4': 'Warm White · Amber',
  'skin.5': 'Cream Yellow · Warm White',
  'skin.6': 'Moonlight Prologue · Pen Gray',
  'skin.7': 'Night Sky Ink Blue',
  'skin.8': 'Winter Sun',
  'skin.9': 'First Snow',
  'skin.10': 'White Moonlight',
  'skin.11': 'Vintage Paper Brown',
  'skin.12': 'Moonrock Freehand',
  'skin.13': 'Apple Silver · Blue',
  'skin.14': 'Black Gold · Silent Sea',
  'skin.15': 'Cream · Sunrise',
  'skin.16': 'Warm Gray · Amber',

  /* ---------- Left: template list ---------- */
  /* V0.0.53: `sidebar.title` ("Template Workspace") is gone -- that label left the main
     UI together with the center / right column titles (user decision). The column's
     name is now carried by the "Templates" sub-heading right below.
     Corrected in the same pass: the three help strings that used the label as a
     signpost (`help.quickStart.3` / `help.ops.sidebar` / `about.tplDirNote`) now point
     at a label that really exists (or at the column itself) -- a signpost aimed at a
     name that is no longer on screen is worse than no signpost. */
  /* V0.0.51@r12: `sidebar.noteLine1` (the line under the panel title) was removed --
     it restated `help.quickStart.3`, and explanatory prose lives on the help page. */

  /* Template list (V0.0.11) */
  'template.listTitle': 'Templates',
  'template.loading': 'Reading template library…',
  'template.unavailable': 'Template library unavailable: templates/ not found',
  'template.empty': 'No templates',
  'template.stats': '{dirs} dirs · {files} files',
  'template.loadConfirm': 'Load template "{name}"? The tree you are editing will be replaced (undoable).',
  'template.loaded': 'Loaded template "{name}"',
  'template.noteAdopted': ' (note adopted from {file})',
  'template.loadFailed': 'Failed to load template: {message}',

  /* New template (V0.0.41 · manual 9.2 #7 / 10.2 #4) */
  'template.new': 'New',
  'template.newTip': 'Create a template from scratch (blank or any template in the library as a starting point)',
  'template.newTitle': 'New template',
  'template.newNameLabel': 'Template name',
  'template.newNamePlaceholder': 'e.g. My project template',
  'template.newDescLabel': 'Description (optional)',
  'template.newDescPlaceholder': 'One line about what this template is for',
  'template.newBaseLabel': 'Starting point',
  'template.newBaseBlank': 'Blank (root only)',
  'template.newCreate': 'Create',

  /* Save as template (V0.0.13) */
  'template.saveAs': 'Save as template',
  'template.saveAsTip': 'Save the tree you are editing as a new template',
  'template.savePrompt': 'Template name',
  'template.nameEmpty': 'Template name cannot be empty',
  'template.saved': 'Saved template "{name}"',
  'template.overwritten': 'Overwrote template "{name}"',
  'template.overwriteConfirm': 'A template named "{name}" already exists. Overwriting moves the previous file to the recycle bin (templates/.trash, recoverable). Overwrite?',
  'template.saveFailed': 'Failed to save template: {message}',
  'template.rename': 'Rename',
  'template.renameTip': 'Rename this template (file name and display name)',
  'template.renamePrompt': 'Rename "{name}" to',
  'template.renamed': 'Renamed to "{name}"',
  'template.delete': 'Delete',
  'template.deleteTip': 'Delete this template (moved to templates/.trash, recoverable)',
  'template.deleteConfirm': 'Delete template "{name}"? It will be moved to the recycle bin (templates/.trash).',
  'template.deleted': 'Deleted template "{name}"',
  'template.opFailed': 'Template operation failed: {message}',

  /* Template folder binding (V0.0.38 / 6E) */
  'template.dirLabel': 'Template folder',
  'template.dirUnknown': '(not loaded)',
  'template.dirHintDefault': 'No external folder bound; using the built-in library (blank template only)',
  'template.dirHintInvalid': 'The bound folder is unusable: {reason}',
  'template.dirPick': 'Choose...',
  'template.dirPickTip': 'Choose a folder as the template library (system folder picker)',
  'template.dirPastePrompt': 'The system folder picker is unavailable here. Paste the absolute path of the template folder.',
  'template.dirBound': 'Template folder bound: {dir}',
  'template.dirEnvShadow': 'An environment variable overrides the binding; using: {dir}',
  'template.dirBindFailed': 'Failed to bind template folder: {message}',
  'template.refresh': 'Refresh',
  'template.refreshTip': 'Reload the template list',

  /* Template context menu, import & export (V0.0.38 / 6E) */
  /* V0.0.51@r11: accessible name + tooltip for the per-row ⋮ entry (same action list as the menu) */
  'template.more': 'More actions',
  'template.moreTip': 'Load / Rename / Duplicate / Export / Delete',
  'template.load': 'Load',
  'template.duplicate': 'Duplicate',
  'template.duplicatePrompt': 'Name for the duplicated template',
  'template.copySuffix': '{name} copy',
  'template.duplicated': 'Duplicated as "{name}"',
  'template.export': 'Export',
  'template.exportJson': 'Export as .json',
  'template.exportMd': 'Export as .md',
  'template.exported': 'Exported "{name}"',
  'template.exportFailed': 'Export failed: {message}',
  'template.layerBuiltin': 'Built-in',
  'template.layerUser': 'User',
  'template.import': 'Import',
  'template.importTip': 'Import a template from a .json / .md file',
  'template.imported': 'Imported template "{name}"',
  'template.importFailed': 'Import failed: {message}',
  'template.importOverwriteConfirm': 'A template named "{name}" already exists. Overwriting moves the previous file to the recycle bin (recoverable). Overwrite?',

  /* ---------- Backend error codes -> localized text ----------
   * Keys are fixed as `err.<code>`; placeholders must match
   * src/shared/error-codes.json entry by entry, enforced by the
   * "error-code localization closure" and "placeholder consistency"
   * guards in tools/verify.py. Unregistered codes fall back to the
   * backend text. The 5 entries containing {message} carry a Python
   * exception string that cannot be translated - mixed language there
   * is expected.
   */
  'err.segmentNotString': 'Directory name must be a string',
  'err.segmentEmpty': 'Directory name cannot be empty',
  'err.segmentTooLong': 'Directory name too long (limit 120 characters): {name}',
  'err.segmentDot': 'Directory name cannot be . or .. : {name}',
  'err.segmentIllegalChar': 'Directory name contains an illegal character: {name}',
  'err.segmentReserved': 'Directory name is a reserved system name: {name}',
  'err.segmentTrailing': 'Directory name cannot have leading/trailing spaces or end with a dot: {name}',
  'err.segmentInvalid': '"{name}" is not a valid directory name ({reason})',
  'err.treeMissing': 'Missing directory tree data: tree',
  'err.targetMissing': 'Missing target location: target',
  'err.targetInvalid': 'Target location is not a valid path: {target} ({reason})',
  'err.targetTooShallow': 'Target location must be at least two levels deep; a drive root is not allowed: {target}',
  'err.targetBlocked': 'Target location is inside a protected directory and was rejected: {target} ({reason})',
  'err.targetReserved': 'Target location points to QingMan itself or its parent and was rejected: {target} ({reason})',
  'err.tooManyNodes': 'Tree too large: {dirs} directories + {files} files = {total}, limit {limit}',
  'err.pathConflict': 'A file with the same name already exists at the target path; cannot create a directory: {path}',
  'err.pathConflictDir': 'A directory with the same name already exists at the target path; cannot create a file: {path}',
  'err.badJson': 'Request body is not a valid JSON object',
  'err.badPath': 'Invalid access path',
  'err.notFound': 'Endpoint does not exist: {path}',
  'err.bodyTooLarge': 'Request body too large, limit {limit} bytes',
  'err.ioError': 'Disk write failed: {message}',
  'err.internalError': 'Internal server error: {message}',
  'err.hostRejected': 'Request host is not allowed: {host}',
  'err.originRejected': 'Request origin is not allowed: {origin}',
  'err.missingGuardHeader': 'Missing guard request header {header}',
  'err.methodNotAllowed': 'Method not allowed: {method}',
  'err.editorRootMissing': 'Editor document is missing the root node',
  'err.editorRootNotDir': 'The root of the editor document must be a directory node',
  'err.editorNodeNotObject': 'Editor node must be an object: {path}',
  'err.editorNodeBadType': 'Editor node type must be dir or file: {path}',
  'err.editorNodeBadName': 'Editor node name must be a non-empty string: {path}',
  'err.editorNodeBadId': 'Editor node id must be a non-empty string: {path}',
  'err.editorNodeBadContent': 'Editor file node content must be a string: {path}',
  'err.editorNodeBadChildren': 'Editor directory node children must be an array: {path}',
  'err.editorIdDuplicated': 'Editor document has a duplicate id: {id} (first seen at {first}, again at {again})',
  'err.editorSiblingDuplicated': 'Duplicate node name at the same level: {name} ({path})',
  'err.editorTooLarge': 'Editor document too large, limit {limit} bytes (current {actual})',
  'err.editorTooManyNodes': 'Editor document has too many nodes, limit {limit}',
  'err.editorReadFailed': 'Failed to read the editor document: {message}',
  'err.editorCorrupt': 'Editor document is corrupt and cannot be parsed: {path}',
  'err.editorBackupNotFound': 'No such history version: {id}',
  'err.editorBackupCorrupt': 'History version is corrupt and cannot be restored: {name}',
  'err.shortcutTargetMissing': 'Startup file does not exist: {target}',
  'err.shortcutFailed': 'Failed to create the shortcut: {message}',
  'err.openDirBadTarget': 'Unknown folder target: {target}',
  'err.iconDataMissing': 'Missing icon data: data',
  'err.iconInvalid': 'Malformed icon file (PNG-in-ICO only)',
  'err.iconTooLarge': 'Icon too large, limit {limit} bytes (current {actual})',
  'err.iconWriteFailed': 'Failed to write icon (disk not writable or file in use)',
  'err.templateNotFound': 'Template not found: {name}',
  'err.templateBadJson': 'Malformed template file: {name}',
  'err.templateReadFailed': 'Failed to read template: {name} ({message})',
  'err.templateNameEmpty': 'Template name cannot be empty',
  'err.templateNameInvalid': 'Invalid template name: {name} (letters, digits, underscore and hyphen only)',
  'err.templateNameTooLong': 'Template name too long (max 60 characters): {name}',
  'err.templateTreeMissing': 'Missing directory tree data: tree',
  'err.templateTooManyNodes': 'Template too large: {dirs} dirs + {files} files = {total}, limit {limit}',
  'err.templateTooLarge': 'Template file too large, limit {limit} bytes (current {actual})',
  'err.templateExists': 'A template with the same name already exists: {name} (not overwritten, please rename and retry)',
  'err.templateWriteFailed': 'Failed to write template: {name} (disk not writable or file in use)',
  'err.templateDeleteFailed': 'Failed to delete template: {name} (file in use or recycle bin not writable)',
  'err.templateRenameFailed': 'Failed to rename template: {name} (file in use or name conflict)',
  'err.templateDirBlocked': 'Template directory not allowed: {dir} ({reason})',
  'err.templateDirNotWritable': 'Template directory not writable: {dir} ({message})',
  'err.templateBadMarkdown': 'Failed to parse template Markdown: {reason}',
  'err.templateSiblingDuplicated': 'Duplicate sibling node in template: {name} (case-insensitive)',
  'err.templateEmpty': 'Template content is empty: no nodes parsed',

  /* Error-code badge: a stable identifier for troubleshooting, shown alongside the localized text */
  'err.codeLabel': 'Error code: {code}',
  /* Not a backend code: raised by the frontend on HTTP-level failure, but shares the err.* prefix so it localizes the same way */
  'err.httpError': 'Request failed (HTTP {status})',
  'err.networkError': 'Cannot reach the backend service; make sure it is still running: {message}',

  /* ---------- Center: generation parameters ---------- */
  'gen.targetLabel': 'Target path',
  'gen.targetPlaceholder': 'e.g. E:\\MyProject (or click the icon on the right)',
  'gen.targetPick': 'Choose...',
  'gen.targetPickTip': 'Choose an existing folder as the target path (system folder picker)',
  'gen.targetPastePrompt': 'The system folder picker is unavailable here. Paste the absolute path of the target folder.',
  'gen.dryRun': 'Dry run only (do not write)',
  'gen.button': 'Generate',
  'gen.buttonTip': 'Generate: create the real folders at the target location',

  /* Collapsed summary line */
  'gen.summaryEmpty': 'No target path set',
  'gen.summaryTarget': 'Target {target}',
  'gen.summaryRoot': 'Root {root}',
  'gen.summaryNoRoot': 'No root folder',
  'gen.summaryDryRun': 'Dry run',
  'gen.summaryWrite': 'Write',
  'gen.summarySep': ' · ',

  /* ---------- Center: directory tree ---------- */
  /* V0.0.53: `tree.title` ("Tree Workspace") is gone -- same reason as the left column. */
  'tree.canvasLabel': 'Directory tree',
  'tree.addChild': 'New child',
  'tree.rename': 'Rename',
  'tree.delete': 'Delete',
  'tree.clearRoot': 'Clear…',
  'tree.clearRootConfirm': 'Clear the whole tree (root name "{name}" is kept)? You can undo this.',
  'tree.undo': 'Undo',
  'tree.redo': 'Redo',
  'tree.expandAll': 'Expand all',
  'tree.collapseAll': 'Collapse all',
  /* V0.0.50 · I group: toolbar went from text buttons to pure line icons;
     the short words above stay as accessible names, descriptions move to tooltips. */
  'tree.undoTip': 'Undo: revert the last edit (Ctrl+Z)',
  'tree.redoTip': 'Redo: reapply an undone edit (Ctrl+Y)',
  'tree.addChildTip': 'New child node: add a subfolder under the selected folder',
  'tree.renameTip': 'Rename: change the selected node name (F2)',
  'tree.deleteTip': 'Delete: remove the selected node and all its children (asks first)',
  'tree.expandAllTip': 'Expand all: open every level of the tree',
  'tree.collapseAllTip': 'Collapse all: close every level of the tree',
  'tree.newDirPrompt': 'New directory name',
  'tree.newDirDefault': 'New directory',
  'tree.renamePrompt': 'Rename',
  'tree.rootNoName': '(no root folder)',
  'tree.deleteConfirm': 'Delete "{name}" and all its children?',
  'tree.copyPath': 'Copy path',
  /* V0.0.43 · G group: three semantic toolbar groups (screen-reader label only) */
  'tree.groupEdit': 'Edit',
  'tree.groupView': 'View',
  'tree.groupOutput': 'Output',
  /* V0.0.50 · I group: "save as template" moved from the template panel into the band */
  'tree.groupSave': 'Save',
  /* V0.0.43 · F group: multi-select batch operations */
  'tree.batchInfo': '{n} selected',
  'tree.batchMoveHint': 'Drag one of them to move the whole set',
  'tree.batchDelete': 'Delete selected',
  'tree.batchCopy': 'Copy selected paths',
  'tree.batchClear': 'Clear selection',
  /* V0.0.50 · I group: batch bar loses its text too (icon language from the design
     doc, wording kept faithful to what this project actually does) */
  'tree.batchDeleteTip': 'Delete selected: remove the selected nodes and all their children (undoable)',
  'tree.batchCopyTip': 'Copy selected paths: copy every selected path to the clipboard',
  'tree.batchClearTip': 'Clear selection: leave multi-select mode',
  'tree.batchDeleteConfirm': 'Delete the {n} selected nodes and all their children? (undoable)',
  'tree.batchDeleteRoot': 'The selection includes the root node, which cannot be deleted',
  'tree.addMultiBlocked': 'A new child cannot be added while multiple nodes are selected - clear the selection first',
  'tree.renameMultiBlocked': 'Rename is unavailable while multiple nodes are selected - clear the selection first',

  /* ---------- Right: inspector (properties / source) ---------- */
  /* V0.0.53: `inspector.title` ("Property Workspace") is gone -- same reason; the
     properties <-> source segmented control keeps its top-right spot (.insp-head
     pins it right with justify-content: flex-end). */
  /* V0.0.43 · H group: properties <-> source dual mode */
  'inspector.modeLabel': 'Inspector view',
  'inspector.modeProp': 'Properties',
  'inspector.modeSrc': 'Source',
  'inspector.sourceEmpty': 'No node selected',
  /* V0.0.43 · F x H: inspector aggregates while multiple nodes are selected */
  'inspector.multiTitle': '{n} selected',
  'inspector.multiType': 'Multiple',
  'inspector.multiParents': 'Multiple locations',
  'inspector.multiNoteDisabled': 'Note editing is disabled while multiple nodes are selected',
  'inspector.name': 'Name',
  'inspector.type': 'Type',
  'inspector.typeDir': 'Directory',
  'inspector.typeFile': 'File',
  'inspector.path': 'Path',
  'inspector.depth': 'Depth',
  'inspector.dirs': 'Subdirectories',
  'inspector.files': 'Files',
  'inspector.resultTitle': 'Generation result',
  'inspector.resultEmpty': 'Not generated yet',
  'inspector.genFailed': 'Generation failed\n{code}: {message}',
  'inspector.noteTitle': 'Note',
  'inspector.notePlaceholder': 'Write a note for this node (plain text)…',
  'inspector.copy': 'Copy',
  'inspector.copyNameTip': 'Copy node name',
  'inspector.copyPathTip': 'Copy node path',
  'inspector.copyNote': 'Copy note',
  'inspector.copyNoteTip': 'Copy node note',

  /* ---------- Status bar ---------- */
  'status.ready': 'Ready',
  'status.readyWith': 'Ready · {nameZh} {app}',
  'status.count': 'Dirs {dirs} · Files {files}',
  'status.restored': 'Restored last edit',
  'status.restoredAt': 'Restored last edit ({at})',
  'status.addedDir': 'Added directory "{name}"',
  'status.renamed': 'Renamed to "{name}"',
  'status.deleted': 'Deleted "{name}"',
  'status.clearedRoot': 'Tree cleared',
  'status.moved': 'Moved "{name}" into "{to}"',
  /* V0.0.43 · F group: batch operation receipts */
  'status.batchDeleted': 'Deleted {n} nodes',
  'status.batchMoved': 'Moved {n} nodes into "{to}"',
  'status.dryRunning': 'Dry running…',
  'status.writing': 'Writing to disk…',
  'status.dryDone': 'Dry run done: {dirs} dirs · {files} files · {existed} existed',
  'status.genDone': 'Generation done: {dirs} dirs · {files} files · {existed} existed',
  'status.noteUpdated': 'Note of "{name}" updated',
  'status.genFailed': 'Generation failed: {message}',
  'status.backendOffHint': 'Backend offline, please launch via start.bat',

  /* ---------- Undo / redo ---------- */
  'status.undid': 'Undid',
  'status.redid': 'Redid',
  'toast.cannotUndo': 'Nothing to undo',
  'toast.cannotRedo': 'Nothing to redo',

  /* ---------- Desktop shortcut ---------- */
  'shortcut.title': 'Create desktop shortcut',
  'shortcut.confirm': 'Create a "QingMan" shortcut on the desktop?',
  'shortcut.done': 'Shortcut created',
  'shortcut.fileName': 'QingMan.lnk',
  'shortcut.downloaded': ' (downloaded)',
  'shortcut.failed': 'Shortcut failed: {message}',

  /* ---------- Toasts ---------- */
  'toast.selectDirFirst': 'Please select a directory node first',
  'toast.nameEmpty': 'Name cannot be empty',
  'toast.siblingExists': '"{name}" already exists in this directory',
  'toast.rootDeleteBlocked': 'Root node cannot be deleted',
  'toast.moveMissing': 'The node to move no longer exists',
  'toast.moveNotDir': 'Can only move into a directory node',
  'toast.moveCycle': 'Cannot move a directory into its own subdirectory',
  'toast.moveRoot': 'Root node cannot be moved',
  'toast.targetRequired': 'Please fill in the target path first',
  'toast.dryDone': 'Dry run complete, no disk changes',
  'toast.generatedTo': 'Generated to {root}',
  'toast.copied': 'Copied to clipboard',
  'toast.copyFailed': 'Copy failed (clipboard not granted)',
  'toast.batchCopied': 'Copied {n} paths',
  'toast.saveFailed': 'Save failed: {message}',
  'toast.dupIdBlocked': 'Duplicate ids detected ({ids}), save blocked',
  'toast.docDupId': 'Document contains duplicate ids: {ids}',
  'toast.restoreFailed': 'Failed to restore last edit: {message}',
  'toast.backendOff': 'Backend offline: {message}',
  'toast.serviceBack': 'The service is back. Reload the page (F5) to load your saved tree.',

  /* ---------- Sample document ---------- */
  'sample.root': 'QingMan Sample Project',
  'sample.materials': 'Materials',
  'sample.output': 'Output',
  'sample.raw': 'Raw',
  'sample.tidied': 'Tidied',
  'sample.readme': 'README.md',
  'sample.readmeContent': '# README\n\nThis directory skeleton was generated by QingMan.\n',

  /* ---------- Module diagnostics ---------- */
  'list.separator': ', ',
  'api.nonJson': 'Backend returned non-JSON (HTTP {status})',
  'bus.handlerError': '[bus] handler for event {type} threw:',
  'doc.nodeNotObject': 'Invalid document node ({path}): expected object',
  'doc.nodeBadType': 'Invalid document node ({path}): type must be dir or file',
  'doc.nodeBadName': 'Invalid document node ({path}): name must be a non-empty string',
  'doc.nodeBadChildren': 'Invalid document node ({path}.children): expected array',

  /* ---------- Help page ---------- */
  'help.docTitle': 'QingMan · Usage',
  'help.titleTag': 'Usage',
  'help.navTitle': 'Contents',
  'help.back': 'Back to app',
  'help.backTip': 'Return to the main view (this tab stays open)',
  'help.footer': 'QingMan · Offline local app · version shown only on this page',

  /* Fallback version shown when the backend is offline. Must match project VERSION (enforced by verify.py). */
  'help.versionFallback': 'V0.2.0',
  'help.versionStale': '[Backend offline; value cached locally]',

  'about.version': 'Version',
  'about.backend': 'Backend',
  'about.backendOn': 'Connected',
  'about.backendOff': 'Offline',
  'about.app': 'App name',
  // V0.0.51@r6: the template folder moved from a hard-coded sidebar line into Help,
  // pulled live from the backend (follows any rebinding). The key deliberately avoids
  // the about.note removed in V0.0.41 -- that one was a "design discipline" footnote.
  'about.tplDir': 'Template library folder',
  'about.tplDirBuiltin': ' (built-in)',
  'about.tplDirUnknown': 'Backend not connected -- unavailable',
  'about.tplDirNote': 'Change the template library folder via the folder icon on the left "Template folder" row; it takes effect immediately. The built-in folder is used when unbound.',
  /* "Documentation" and the version-note line were removed per manual 10.2 #10 (V0.0.41):
     the former is a developer-doc entry (not user-facing), the latter is a design rule
     rather than text meant for users. about.docs / about.docsValue / about.note are gone
     from both locales together to keep 7b-3 (key parity) green. */

  'help.lead': 'QingMan is an offline directory-structure design tool: edit a directory tree visually, then generate real folders on disk with one click.',

  'help.templates.title': 'Templates',
  'help.templates.1': 'The app ships with a single blank template. The 16 business templates live in a separate template-pack zip and are downloaded only when you need them.',
  'help.templates.2': 'Unzip it into the template folder (by default the templates folder next to the app; open it from Service settings). Both .json and .md are accepted.',
  'help.templates.3': 'Back in the main window the list refreshes within seconds. Importing a template with an existing name asks before overwriting; the old file goes to the recycle folder.',
  'help.templates.4': 'Right-click a template to export: .json for re-import, .md for reading and version control. Both carry the same content.',
  'help.quickStart.title': 'Quick Start',
  'help.quickStart.1': 'Double-click start.bat in the project root to launch the local server',
  'help.quickStart.2': 'Browser opens automatically; a status dot in the ready colour at the top right means the service is up (click it for service status and settings)',
  'help.quickStart.3': 'Load a template from "Templates" in the left column, or edit the tree yourself in the center',
  'help.quickStart.4': 'Fill in the target path and keep "Dry run" checked for a test run',
  'help.quickStart.5': 'When satisfied, uncheck "Dry run" and click "Generate" to write to disk',

  'help.ops.title': 'Interface',
  'help.ops.topbar': 'Top bar — the brand mark and the "More" menu sit on the left; the two widgets on the right are icon-only. The inner one shows the auto-save state: a check means saved, a spinning arrow means saving, an x means the save failed (hover for the exact state and time, and screen readers read it too). The outer one is the service status button: the dot colour tells whether the service is ready, and clicking it opens service settings; the same wording also appears in the "More" menu',
  'help.ops.sidebar': 'Left column — "Templates" lists the templates in the current library; click to load. A ⋮ at the right end of each row opens exactly the same menu as right-clicking (Load / Rename / Duplicate / Export / Delete). The two icons beside the heading are "New" and "Import". The "Template folder" row below shows the current library location; its icons rebind and refresh it (effective immediately). To store the current tree as a new template use "Save as template" in the center toolbar: an existing name is not overwritten unless you confirm, and the old template moves to the trash and can be recovered',
  'help.ops.center': 'Center column — generation options and toolbar at the top, directory tree below',
  'help.ops.genBar': 'The parameter bar is always visible and cannot be collapsed: the summary line above (target · root · dry/write) is a pre-generation check; the target path and "dry run" below stay editable',
  'help.ops.inspector': 'Right column — switch between the "Properties / Source" views at the top; shows name, type, path, depth and stats for the selected node, plus the generation result',

  'help.tree.title': 'Tree operations',
  'help.tree.1': 'Click a node to select it; the property panel updates',
  'help.tree.2': '"New child" adds a subdirectory under the selected directory',
  'help.tree.3': '"Rename" edits the node name; the root node name IS the generated root folder name - rename it directly, or clear it to create no root folder',
  'help.tree.4': '"Delete" removes the selected node and its children (with confirmation)',
  'help.tree.5': '"Expand / Collapse" is a single toggle: it opens every level while anything is folded, and folds everything once it is all open - the icon and tooltip follow, so you can tell what a click will do',
  'help.tree.6': 'Drag a node onto a directory to move it there (cannot move into its own subdirectory)',
  'help.tree.7': 'Right-click a node to open a menu: New child / Rename / Delete / Copy path',
  'help.tree.8': 'Ctrl/Cmd-click to add nodes to the selection, Shift-click to select a contiguous run; Esc (or a plain click) clears it, Ctrl+A selects everything but the root. With several selected you can delete them as a group, copy their paths, or drag one of them to move the whole set',

  'help.kbd.title': 'Keyboard shortcuts',
  /* Shortcut table: each entry has two columns — "keys" and "what it does".
     Keys live under `<name>.keys`; the description keeps the `<name>` key itself.
     Equivalent bindings are separated by `|`; `/` means the same key differs by platform (Ctrl or Cmd). */
  'help.kbd.or': 'or',
  'help.kbd.save.keys': 'Ctrl / Cmd + S',
  'help.kbd.save': 'Save immediately (skip debounce)',
  'help.kbd.undo.keys': 'Ctrl / Cmd + Z',
  'help.kbd.undo': 'Undo the last edit',
  'help.kbd.redo.keys': 'Ctrl / Cmd + Y|Ctrl / Cmd + Shift + Z',
  'help.kbd.redo': 'Redo',
  'help.kbd.delete.keys': 'Delete',
  'help.kbd.delete': 'Delete the selected node (with confirmation, undoable)',
  'help.kbd.rename.keys': 'F2',
  'help.kbd.rename': 'Rename the selected node',
  'help.kbd.pending': 'Additional shortcuts will be finalized once the feature surface stabilizes.',

  'help.safety.title': 'Safety',
  'help.safety.1': 'The backend only listens on the local loopback address (127.0.0.1); other devices on the LAN cannot access it',
  'help.safety.2': 'The server validates Origin/Host and requires a write-protection header, blocking blind cross-site requests',
  'help.safety.3': 'No data is collected or uploaded; the tree and generation results stay on this machine',
  'help.safety.4': 'Dry run does not write to disk; real generation skips existing files, never overwrites, and never deletes existing content',
  'help.safety.5': 'Destructive actions such as deleting nodes require confirmation',

  'help.support.title': 'Support QingMan',
  'help.support.lead': 'QingMan is a free offline tool. If you find it useful, a voluntary tip helps keep it maintained.',
  'help.support.wechat': 'WeChat Tip',
  'help.support.qrAlt': 'WeChat tip QR code',
  'help.support.thanks': 'Thanks for your support — bug fixes are best-effort.',
  'help.support.goto': 'Tip & Support',
  'help.support.gotoTip': 'Open the support page (new tab)',

  'help.about.title': 'Version & About',
  'help.disclaimer.title': 'Disclaimer',
  'help.disclaimer.1': 'This software is provided free of charge, without warranty of any kind. Use at your own risk. Tips are voluntary goodwill support; they do not constitute a transaction and provide no additional services.',

  /* ---------- Support page (split in V0.0.18) ---------- */
  'support.titleTag': '· Support',
  'support.docTitle': 'Support · QingMan',
  'support.back': 'Back to Editor',
  'support.toHelp': 'User Guide',
  'support.lead': 'QingMan is a free offline tool. If you find it useful, a voluntary tip helps keep it maintained.',
  'support.note': 'QingMan is completely free and runs offline; tips are entirely voluntary. Thanks for every bit of support — bug fixes are best-effort.',
};

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
  { id: 'templates', title: 'help.templates.title', kind: 'ul', items: [
    'help.templates.1', 'help.templates.2', 'help.templates.3', 'help.templates.4',
  ] },
  { id: 'kbd', title: 'help.kbd.title', kind: 'kbd', note: 'help.kbd.pending', items: ['help.kbd.save', 'help.kbd.undo', 'help.kbd.redo', 'help.kbd.delete', 'help.kbd.rename'] },
  { id: 'safety', title: 'help.safety.title', kind: 'ul', items: [
    'help.safety.1', 'help.safety.2', 'help.safety.3', 'help.safety.4', 'help.safety.5',
  ] },
  { id: 'about', title: 'help.about.title', kind: 'about', note: 'about.tplDirNote', items: [] },
  { id: 'disclaimer', title: 'help.disclaimer.title', kind: 'ul', items: ['help.disclaimer.1'] },
];
