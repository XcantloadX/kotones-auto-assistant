import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components/controls"
import "../../components/form"

// 杂项设置：idle / debug / shared 设置
Item {
    id: root
    property var settingsCtrl
    signal modified()

    readonly property var _idle:      settingsCtrl?.config?.profile?.idle     ?? {}
    readonly property var _trace:     settingsCtrl?.config?.profile?.trace    ?? {}
    readonly property var _shared:    settingsCtrl?.config?.shared?.misc      ?? {}
    readonly property var _telemetry: settingsCtrl?.config?.shared?.telemetry ?? {}
    readonly property var _profile:   settingsCtrl?.config?.profile           ?? {}

    function _commit(path, key, value) {
        var c = JSON.parse(JSON.stringify(settingsCtrl.config))
        var ref = path.split(".").reduce(function(o, k) { return o[k] }, c)
        ref[key] = value
        settingsCtrl.commitConfig(JSON.stringify(c))
        modified()
    }

    FormBinder {
        id: idle
        data: root._idle
        onCommitted: root._commit("profile.idle", key, value)
    }
    FormBinder {
        id: trace
        data: root._trace
        onCommitted: root._commit("profile.trace", key, value)
    }
    FormBinder {
        id: shared
        data: root._shared
        onCommitted: root._commit("shared.misc", key, value)
    }
    FormBinder {
        id: telemetry
        data: root._telemetry
        onCommitted: root._commit("shared.telemetry", key, value)
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            anchors.margins: 16
            spacing: 12

            // ── 闲置挂机 ────────────────────────────────────
            FormGroupBox {
                title: "闲置挂机"
                binder: idle

                FormCheckBox {
                    field: "enabled"
                    label: "启用闲置挂机"
                }
                FormSpinBox {
                    field: "idle_seconds"
                    label: "闲置秒数"
                    from: 1
                    to: 3600
                }
                FormCheckBox {
                    field: "minimize_on_pause"
                    label: "按键暂停时最小化窗口"
                }
            }

            // ── 调试 ────────────────────────────────────────
            // 第一个字段无 field: 属性，自动回退到显式 value/onValueChanged
            FormGroupBox {
                title: "调试"
                binder: trace

                Label {
                    text: "仅供调试使用。正常运行时务必关闭下面所有的选项。"
                    color: "#DC3545"
                    font.bold: true
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }
                FormCheckBox {
                    label: "保留截图数据"
                    value: root._profile.keep_screenshots ?? false
                    onUserToggled: function(checked) { root._commit("profile", "keep_screenshots", checked) }
                }
                FormCheckBox {
                    field: "recommend_card_detection"
                    label: "跟踪推荐卡检测"
                }
            }

            // ── 全局设置 (shared) ───────────────────────────
            FormGroupBox {
                title: "全局设置"
                binder: shared

                FormSegmentedButton {
                    field: "check_update"
                    label: "检查更新时机"
                    options: [
                        { label: "从不", value: "never" },
                        { label: "启动时", value: "startup" }
                    ]
                }
                FormCheckBox {
                    field: "auto_install_update"
                    label: "自动安装更新"
                }
                FormSegmentedButton {
                    field: "update_channel"
                    label: "更新通道"
                    options: [
                        { label: "稳定版", value: "release" },
                        { label: "测试版", value: "beta" }
                    ]
                }
                FormSegmentedButton {
                    field: "log_level"
                    label: "日志等级"
                    options: [
                        { label: "普通", value: "debug" },
                        { label: "详细", value: "verbose" }
                    ]
                }
                FormSegmentedButton {
                    field: "game_data_check"
                    label: "游戏资源检查时机"
                    options: [
                        { label: "手动", value: "manual" },
                        { label: "每次启动", value: "startup" },
                        { label: "每天一次", value: "daily" },
                        { label: "每周一次", value: "weekly" }
                    ]
                }
                FormCheckBox {
                    field: "game_data_auto_update"
                    label: "自动安装游戏资源更新"
                }

                Label {
                    text: "匿名数据收集"
                    font.weight: Font.DemiBold
                    Layout.fillWidth: true
                }

                Label {
                    text: "目前收集的数据包含：\n- 发生错误时的错误类型和堆栈信息\n\n<b>收集的数据将仅用于分析和改进 kaa。你可以随时在下面启用或禁用数据收集</b>。"
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                    color: palette.placeholderText
                    textFormat: Text.RichText
                }

                // telemetry 来自不同 binder，显式覆盖
                FormCheckBox {
                    binder: telemetry
                    field: "sentry"
                    label: "自动发送匿名错误报告"
                }

                Button {
                    text: "立即检查游戏资源"
                    onClicked: if (settingsCtrl) settingsCtrl.checkGameDataAsync()
                }

                TextArea {
                    id: gameDataOutput
                    Layout.fillWidth: true
                    Layout.preferredHeight: 120
                    readOnly: true
                    visible: text.length > 0
                    wrapMode: TextArea.Wrap
                }

                Connections {
                    target: settingsCtrl
                    function onGameDataProgress(text) { gameDataOutput.text += text + "\n" }
                    function onGameDataDone() { gameDataOutput.text += "完成\n" }
                }
            }
        }
    }
}
