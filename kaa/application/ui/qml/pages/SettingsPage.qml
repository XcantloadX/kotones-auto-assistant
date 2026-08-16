import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "sections"

PageContainer {
    id: root
    title: "设置"

    titleRightContent: RowLayout {
        spacing: 8
        Rectangle {
            visible: root.scriptRunning
            color: "#FEF3C7"
            border.color: "#F59E0B"
            radius: 4
            implicitHeight: 32
            width: runningLabel.implicitWidth + 16

            Label {
                id: runningLabel
                text: "运行中"
                color: "#B45309"
                font.bold: true
                anchors.centerIn: parent
            }
        }
        Rectangle {
            visible: root.dirty
            color: "#FFEBE9"
            border.color: "#DC3545"
            radius: 4
            implicitHeight: 32
            width: unsavedLabel.implicitWidth + 16

            Label {
                id: unsavedLabel
                text: "未保存的更改"
                color: "#DC3545"
                font.bold: true
                anchors.centerIn: parent
            }
        }
    }

    headerActions: Button {
        text: "保存"
        highlighted: true
        enabled: !root.scriptRunning && root.dirty
        onClicked: root.save()
    }

    required property var settingsCtrl
    property var runCtrl: null
    readonly property bool scriptRunning: runCtrl ? (runCtrl.running || runCtrl.isStopping) : false
    property bool dirty: false
    property var validationIssues: []
    // 完整 dot path → {severity, message}，分发给各 section 供字段内联展示
    property var errors: ({})

    // 由 validationIssues 构建完整路径 → {severity, message} 的映射
    function errorMap() {
        var m = {}
        for (var i = 0; i < validationIssues.length; ++i) {
            var it = validationIssues[i]
            if (it && it.field) m[it.field] = { severity: it.severity, message: it.message }
        }
        return m
    }

    // 校验当前草稿（base+dirty 合并），刷新 validationIssues 与 errors（供字段内联展示）
    function refreshValidation() {
        validationIssues = []
        errors = {}
        if (!settingsCtrl) return
        try {
            validationIssues = JSON.parse(settingsCtrl.validateJson()) || []
        } catch (err) {
            validationIssues = []
        }
        errors = root.errorMap()
    }

    // 是否存在 error 级校验问题
    function hasValidationErrors() {
        for (var i = 0; i < validationIssues.length; ++i) {
            if (validationIssues[i].severity === "error") return true
        }
        return false
    }

    function save() {
        if (!settingsCtrl) return
        refreshValidation()
        if (root.hasValidationErrors()) {
            Notice.show("error", "存在配置错误，请修正后再保存。")
            return
        }
        settingsCtrl.save()
    }

    Component.onCompleted: refreshValidation()

    Connections {
        target: settingsCtrl
        function onDirtyChanged(isDirty) { root.dirty = isDirty; root.refreshValidation() }
        function onConfigChanged()     { root.refreshValidation() }
        function onOperationSucceeded(msg) { Notice.show("success", msg) }
        function onOperationFailed(msg) { Notice.show("error", msg) }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── TabBar ────────────────────────────────────
        TabBar {
            id: settingsTabs
            Layout.fillWidth: true
            TabButton { text: "基本" }
            TabButton { text: "日常" }
            TabButton { text: "培育" }
            TabButton { text: "杂项" }
        }

        // ── StackLayout ───────────────────────────────
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: settingsTabs.currentIndex

            EmulatorSection {
                settingsCtrl: root.settingsCtrl
                errors: root.errors
            }
            DailySection {
                settingsCtrl: root.settingsCtrl
                errors: root.errors
            }
            ProduceSection {
                settingsCtrl: root.settingsCtrl
                errors: root.errors
            }
            MiscSection {
                settingsCtrl: root.settingsCtrl
                errors: root.errors
            }
        }
    }
}
