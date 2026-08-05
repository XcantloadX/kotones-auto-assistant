import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../components/form"

PageContainer {
    id: root
    title: "偏好"

    titleRightContent: Rectangle {
        visible: root.dirty
        color: "#FFEBE9"
        border.color: "#DC3545"
        radius: 4
        implicitHeight: 32
        width: unsavedLabel.implicitWidth + 16

        Label {
            id: unsavedLabel
            text: "有未保存改动"
            color: "#DC3545"
            font.bold: true
            anchors.centerIn: parent
        }
    }

    headerActions: Button {
        text: "保存"
        highlighted: true
        enabled: root.dirty
        onClicked: root.save()
    }

    required property var prefsCtrl
    property var config: ({})
    property bool dirty: false

    function _get(path) {
        var parts = path.split('.')
        var obj = root.config
        for (var i = 0; i < parts.length; i++) {
            if (obj === undefined || obj === null) return undefined
            obj = obj[parts[i]]
        }
        return obj
    }

    function _set(path, value) {
        root.prefsCtrl.setField(path, value)
    }

    function save() {
        root.prefsCtrl.save()
    }

    function hasUnsavedChanges() {
        return root.prefsCtrl.isDirty()
    }

    function discardChanges() {
        root.prefsCtrl.discard()
    }

    function saveChanges() {
        root.prefsCtrl.save()
    }

    function loadConfig() {
        root.config = root.prefsCtrl.config
        root.dirty = root.prefsCtrl.isDirty()
    }

    Component.onCompleted: loadConfig()

    Connections {
        target: root.prefsCtrl
        function onConfigChanged() { root.loadConfig() }
        function onDirtyChanged(d) { root.dirty = d }
        function onOperationSucceeded(msg) { Notice.show("success", msg) }
        function onOperationFailed(msg) { Notice.show("error", msg) }
    }

    ScrollView {
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 16

            FormGroupBox {
                title: "数据收集"
                Layout.fillWidth: true

                FormCheckBox {
                    label: "自动发送匿名错误报告"
                    value: root._get("telemetry.sentry") === true
                    onUserToggled: function(checked) { root._set("telemetry.sentry", checked) }
                }
            }

            FormGroupBox {
                title: "界面"
                Layout.fillWidth: true

                FormComboBox {
                    label: "窗口背景样式"
                    value: root._get("interface.window_style") || ""
                    options: [
                        { label: "自动", value: "" },
                        { label: "Mica（仅 Win 11）", value: "mica" },
                        { label: "模糊背景", value: "blur" },
                        { label: "亚克力（Win 10 1803+）", value: "acrylic" },
                        { label: "纯色背景", value: "solid" },
                    ]
                    onUserSelected: function(v) { root._set("interface.window_style", v) }
                }

                FormComboBox {
                    label: "色彩方案"
                    value: root._get("interface.color_scheme") || "auto"
                    options: [
                        { label: "跟随系统", value: "auto" },
                        { label: "浅色", value: "light" },
                        { label: "深色", value: "dark" },
                    ]
                    onUserSelected: function(v) { root._set("interface.color_scheme", v) }
                }

                FormComboBox {
                    label: "启动时打开"
                    value: root._get("interface.startup_page") || "last_opened"
                    options: [
                        { label: "总览页面", value: "overview" },
                        { label: "上次打开的配置", value: "last_opened" },
                    ]
                    onUserSelected: function(v) { root._set("interface.startup_page", v) }
                }

                FormComboBox {
                    label: "主题色"
                    value: root._get("interface.theme_color") || ""
                    options: [
                        { label: "跟随系统", value: "" },
                        { label: "蓝色（#0078D4）", value: "#0078d4" },
                        { label: "红色（#E81123）", value: "#e81123" },
                        { label: "绿色（#107C10）", value: "#107c10" },
                        { label: "橙色（#FF8C00）", value: "#ff8c00" },
                        { label: "紫色（#5C2D91）", value: "#5c2d91" },
                        { label: "青色（#00B7C3）", value: "#00b7c3" },
                        { label: "靛蓝（#6B69D6）", value: "#6b69d6" },
                        { label: "石墨灰（#4A5459）", value: "#4a5459" },
                    ]
                    onUserSelected: function(v) { root._set("interface.theme_color", v || null) }
                }
            }

            FormGroupBox {
                title: "通知"
                Layout.fillWidth: true

                FormCheckBox {
                    label: "系统通知"
                    value: root._get("notify.system") === true
                    onUserToggled: function(checked) { root._set("notify.system", checked) }
                }

                FormCheckBox {
                    label: "推送通知"
                    value: root._get("notify.push.enabled") === true
                    onUserToggled: function(checked) { root._set("notify.push.enabled", checked) }
                }

                FormComboBox {
                    label: "推送类型"
                    visible: root._get("notify.push.enabled") === true
                    value: root._get("notify.push.type") || "custom"
                    options: [
                        { label: "自定义命令", value: "custom" },
                        { label: "Discord Webhook", value: "discord" },
                    ]
                    onUserSelected: function(v) {
                        root._set("notify.push.type", v)
                        if (v === "discord") {
                            root._set("notify.push.command", "")
                        } else {
                            root._set("notify.push.webhook_url", "")
                        }
                    }
                }

                FormTextField {
                    label: "自定义命令"
                    placeholder: "任务完成后执行的命令"
                    visible: root._get("notify.push.enabled") === true && root._get("notify.push.type") === "custom"
                    value: root._get("notify.push.command") || ""
                    onUserEdited: function(v) { root._set("notify.push.command", v) }
                }

                FormTextField {
                    label: "Webhook URL"
                    placeholder: "https://discord.com/api/webhooks/..."
                    visible: root._get("notify.push.enabled") === true && root._get("notify.push.type") === "discord"
                    value: root._get("notify.push.webhook_url") || ""
                    onUserEdited: function(v) { root._set("notify.push.webhook_url", v) }
                }
            }

            FormGroupBox {
                title: "快捷键"
                Layout.fillWidth: true

                HotkeyField {
                    label: "启动脚本"
                    value: root._get("hotkeys.start") || ""
                    onUserCommitted: { root._set("hotkeys.start", newValue) }
                }

                HotkeyField {
                    label: "停止脚本"
                    value: root._get("hotkeys.stop") || ""
                    onUserCommitted: { root._set("hotkeys.stop", newValue) }
                }
            }
        }
    }
}
