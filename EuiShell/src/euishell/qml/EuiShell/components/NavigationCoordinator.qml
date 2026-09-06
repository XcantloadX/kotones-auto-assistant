import QtQuick

Item {
    id: root
    visible: false

    required property var unsavedChangesDialog
    signal fullscreenModeRequested(string mode)

    // 当前活跃 tab 的脏检查守卫（由 main.qml 绑定，tab 切换时自动更新）
    property var tabGuards: []

    property var pendingActionRunner: null
    property string pendingActionLabel: ""

    // 全部守卫 = tab 级 + 全局级（globalGuards 为 Shell 注入的上下文属性）
    function _allGuards() {
        var global = (typeof globalGuards !== "undefined" && globalGuards) ? globalGuards : []
        return root.tabGuards.concat(global)
    }

    function isDirty() {
        var guards = root._allGuards()
        for (var i = 0; i < guards.length; i++) {
            if (guards[i] && guards[i].isDirty && guards[i].isDirty())
                return true
        }
        return false
    }

    function clearPendingGuardedAction() {
        root.pendingActionRunner = null
        root.pendingActionLabel = ""
    }

    function runPendingAction() {
        var runner = root.pendingActionRunner
        root.clearPendingGuardedAction()
        if (typeof runner === "function") {
            runner()
        }
    }

    function requestGuardedAction(label, runner) {
        if (typeof runner !== "function") {
            return
        }
        if (!root.isDirty()) {
            runner()
            return
        }
        root.pendingActionRunner = runner
        root.pendingActionLabel = label || "继续此操作"
        root.unsavedChangesDialog.actionLabel = root.pendingActionLabel
        root.unsavedChangesDialog.open()
    }

    function requestFullscreenMode(mode) {
        root.fullscreenModeRequested(mode)
    }

    function saveAndContinuePendingAction() {
        var guards = root._allGuards()
        for (var i = 0; i < guards.length; i++) {
            if (guards[i] && guards[i].isDirty && guards[i].isDirty()) {
                guards[i].save()
            }
        }
        root.runPendingAction()
    }

    function discardAndContinuePendingAction() {
        var guards = root._allGuards()
        for (var i = 0; i < guards.length; i++) {
            if (guards[i] && guards[i].discard) {
                guards[i].discard()
            }
        }
        root.runPendingAction()
    }
}
