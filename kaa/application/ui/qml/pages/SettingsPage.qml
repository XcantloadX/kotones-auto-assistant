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
        objectName: "settingsSaveButton"
        text: "保存"
        highlighted: true
        enabled: !root.scriptRunning && root.dirty
        onClicked: root.save()
    }

    required property var settingsCtrl
    property var runCtrl: null
    property var navigation: null
    readonly property bool scriptRunning: runCtrl ? (runCtrl.running || runCtrl.isStopping) : false
    property bool dirty: false
    property var validationIssues: []
    // 完整 dot path → {severity, message}，分发给各 section 供字段内联展示
    property var errors: ({})
    // 自动注册的 field → label 映射（由各 Form* 通过 FieldRegistrar 上报）
    property var fieldLabelMap: ({})

    function registerField(path, label) {
        if (!path || !label) return
        var m = fieldLabelMap
        m[path] = label
        fieldLabelMap = m
    }
    function unregisterField(path) {
        if (!path) return
        var m = fieldLabelMap
        if (m[path] !== undefined) {
            delete m[path]
            fieldLabelMap = m
        }
    }
    function labelFor(field) {
        if (!field) return ""
        return fieldLabelMap[field] || field
    }

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
            validationErrorDialog.open()
            return
        }
        // commit 兜底：若 Python 侧仍校验失败，刷新后同样弹模态框
        if (!settingsCtrl.save()) {
            refreshValidation()
            if (root.hasValidationErrors()) validationErrorDialog.open()
        }
    }

    Component.onCompleted: refreshValidation()

    Dialog {
        id: validationErrorDialog
        title: "配置校验未通过"
        modal: true
        anchors.centerIn: Overlay.overlay
        width: Math.min(520, root.width - 40)
        standardButtons: Dialog.Ok
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        contentItem: ColumnLayout {
            spacing: 10
            width: parent.width

            Label {
                text: "以下字段存在问题，请修正后再保存："
                wrapMode: Text.Wrap
                Layout.fillWidth: true
                font.bold: true
            }

            ColumnLayout {
                spacing: 6
                Layout.fillWidth: true
                Repeater {
                    model: root.validationIssues.filter(function(it){ return it && it.severity === "error" })
                    delegate: RowLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        Label { text: "•"; font.bold: true; Layout.alignment: Qt.AlignTop }
                        Label {
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            text: {
                                var it = modelData
                                var lbl = root.labelFor(it.field)
                                // 若 label 与 field 相同（未注册或原始 path），仅展示 message 避免重复
                                if (it.field && lbl !== it.field) return lbl + " — " + it.message
                                if (it.field) return lbl + " — " + it.message
                                return it.message
                            }
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: settingsCtrl
        function onDirtyChanged(isDirty) { root.dirty = isDirty; root.refreshValidation() }
        function onConfigChanged()     { root.refreshValidation() }
        function onOperationSucceeded(msg) { Notice.show("success", msg) }
        function onOperationFailed(msg) {
            // 校验失败已由 save() 的模态框展示，避免 toast 重复
            if (root.hasValidationErrors()) return
            Notice.show("error", msg)
        }
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
                navigation: root.navigation
            }
        }
    }
}
