import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components/form"
import "../../dialogs"

// 杂项设置：闲置挂机 / 调试
Item {
    id: root
    property var settingsCtrl
    property var errors: ({})
    property var navigation: null

    readonly property var _idle:      settingsCtrl?.config?.profile?.idle     ?? {}
    readonly property var _trace:     settingsCtrl?.config?.profile?.trace    ?? {}
    readonly property var _profile:   settingsCtrl?.config?.profile           ?? {}

    function _commit(path, key, value) {
        settingsCtrl.setField(path ? path + "." + key : key, value)
    }

    FormBinder {
        id: idle
        data: root._idle
        prefix: "idle"
        errors: root.errors
        onCommitted: function(key, value) { root._commit("idle", key, value) }
    }
    FormBinder {
        id: trace
        data: root._trace
        prefix: "trace"
        errors: root.errors
        onCommitted: function(key, value) { root._commit("trace", key, value) }
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
                    onUserToggled: function(checked) { settingsCtrl.setField("keep_screenshots", checked) }
                }
                FieldRegistrar {
                    startParent: parent
                    field: "keep_screenshots"
                    label: "保留截图数据"
                }
                FormCheckBox {
                    field: "recommend_card_detection"
                    label: "跟踪推荐卡检测"
                }
                FormCheckBox {
                    field: "commu_event_buttons"
                    label: "跟踪 CommuEventButtons"
                }
                FormCheckBox {
                    field: "card_select"
                    label: "跟踪选卡识别"
                }

                RowLayout {
                    spacing: 8

                    Button {
                        text: "技能卡图鉴"
                        onClicked: {
                            if (root.navigation) {
                                root.navigation.requestGuardedAction("打开技能卡图鉴", function() {
                                    root.navigation.requestFullscreenMode("skillCardBrowser")
                                })
                            }
                        }
                    }

                    Button {
                        text: "Inspect 授業"
                        onClicked: schoolEventInspector.open()
                    }
                }
            }

            SchoolEventInspectorDialog {
                id: schoolEventInspector
                debugInspectorCtrl: DebugInspector
            }

        }
    }
}
