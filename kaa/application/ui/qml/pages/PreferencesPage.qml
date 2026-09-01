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

                FormCheckBox {
                    label: "错误上报时附带截图"
                    value: root._get("telemetry.upload_screenshot") === true
                    onUserToggled: function(checked) { root._set("telemetry.upload_screenshot", checked) }
                }

                FormCheckBox {
                    label: "匿名收集统计数据"
                    value: root._get("telemetry.statics") === true
                    onUserToggled: function(checked) { root._set("telemetry.statics", checked) }
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
                title: "更新"
                Layout.fillWidth: true

                FormComboBox {
                    label: "检查更新时机"
                    value: root._get("misc.check_update") || "startup"
                    options: [
                        { label: "从不", value: "never" },
                        { label: "启动时", value: "startup" }
                    ]
                    onUserSelected: function(v) { root._set("misc.check_update", v) }
                }

                FormCheckBox {
                    label: "自动安装更新"
                    value: root._get("misc.auto_install_update") === true
                    onUserToggled: function(checked) { root._set("misc.auto_install_update", checked) }
                }

                FormComboBox {
                    label: "更新通道"
                    value: root._get("misc.update_channel") || "release"
                    options: [
                        { label: "稳定版", value: "release" },
                        { label: "测试版", value: "beta" }
                    ]
                    onUserSelected: function(v) { root._set("misc.update_channel", v) }
                }
            }

            FormGroupBox {
                title: "游戏资源"
                Layout.fillWidth: true

                FormComboBox {
                    label: "资源检查时机"
                    value: root._get("misc.game_data_check") || "startup"
                    options: [
                        { label: "手动", value: "manual" },
                        { label: "每次启动", value: "startup" },
                        { label: "每天一次", value: "daily" },
                        { label: "每周一次", value: "weekly" }
                    ]
                    onUserSelected: function(v) { root._set("misc.game_data_check", v) }
                }

                FormCheckBox {
                    label: "自动安装游戏资源更新"
                    value: root._get("misc.game_data_auto_update") === true
                    onUserToggled: function(checked) { root._set("misc.game_data_auto_update", checked) }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Button {
                        text: "立即检查并更新"
                        enabled: GameDataCtrl.updateStatus === "idle" || GameDataCtrl.updateStatus === "failed"
                        onClicked: GameDataCtrl.triggerUpdate()
                    }

                    BusyIndicator {
                        running: GameDataCtrl.updateStatus === "checking" ||
                                 GameDataCtrl.updateStatus === "downloading" ||
                                 GameDataCtrl.updateStatus === "building"
                        visible: running
                        implicitWidth: 20
                        implicitHeight: 20
                    }

                    Label {
                        visible: !!GameDataCtrl.progressMessage
                        text: GameDataCtrl.progressMessage
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                }

                Label {
                    visible: GameDataCtrl.restartNeeded
                    text: "游戏数据更新已下载，重启应用后自动生效。"
                    color: palette.highlight
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
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
