import QtQuick

Item {
    id: root
    visible: false

    required property var unsavedChangesDialog

    // 当前活跃 tab 的 controller（由 main.qml 绑定，tab 切换时自动更新）
    property var settingsCtrl: null
    property var produceCtrl: null

    property var pendingActionRunner: null
    property string pendingActionLabel: ""

    function isDirty() {
        var settingsDirty = root.settingsCtrl ? root.settingsCtrl.isDirty() : false
        var produceDirty  = root.produceCtrl  ? root.produceCtrl.isDirty()  : false
        return settingsDirty || produceDirty
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

    function saveAndContinuePendingAction() {
        if (root.settingsCtrl && root.settingsCtrl.isDirty()) {
            root.settingsCtrl.save()
        }
        if (root.produceCtrl && root.produceCtrl.isDirty()) {
            root.produceCtrl.save()
        }
        root.runPendingAction()
    }

    function discardAndContinuePendingAction() {
        if (root.settingsCtrl) {
            root.settingsCtrl.discard()
        }
        if (root.produceCtrl) {
            root.produceCtrl.discard()
        }
        root.runPendingAction()
    }
}
