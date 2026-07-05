import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components/controls"
import "../../components/form"

// 培育设置：方案下拉使用共享 solutionsModel 判定空状态，
// options 列表通过 JSON 桥接（FormComboBox 尚未支持直接绑定 model）
Item {
    id: root
    property var settingsCtrl

    readonly property var produceCtrl: typeof TabManager !== "undefined" ? TabManager.activeProduceController : null
    readonly property var _produce: settingsCtrl?.config?.profile?.tasks?.produce ?? {}

    property var solutions: []

    function _commit(path, key, value) {
        if (path.startsWith("shared.")) {
            settingsCtrl.sharedCtrl.setField(path.substring(7) + "." + key, value)
        } else {
            settingsCtrl.setField(path ? path + "." + key : key, value)
        }
    }

    function loadSolutions() {
        if (settingsCtrl) solutions = JSON.parse(settingsCtrl.produceSolutionsJson())
    }

    Component.onCompleted: loadSolutions()

    // 当 model 变化时刷新
    Connections {
        target: produceCtrl
        function onSolutionsChanged() { loadSolutions() }
    }

    FormBinder {
        id: pb
        data: root._produce
        onCommitted: function(key, value) {
            root._commit("tasks.produce", key, value)
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            anchors.margins: 16
            spacing: 12

            FormGroupBox {
                title: "培育"
                binder: pb

                FormCheckBox {
                    field: "enabled"
                    label: "启用培育"
                }

                FormComboBox {
                    field: "selected_solution_id"
                    label: "培育方案"
                    options: root.solutions.map(function(s) {
                        return { label: s.text, value: s.id }
                    })
                    enabled: root.solutions.length > 0
                }

                FormNotice {
                    visible: root.solutions.length === 0
                    style: "info"
                    content: "你需要先创建一个培育方案才能使用培育功能。"
                }

                Button {
                    Layout.fillWidth: true
                    visible: root.solutions.length === 0
                    text: "前往方案页创建"
                    highlighted: true
                    onClicked: {
                        if (typeof TabManager !== "undefined" && TabManager.requestCapturePage)
                            TabManager.requestCapturePage(3)
                    }
                }

                FormSpinBox {
                    field: "produce_count"
                    label: "培育次数"
                    from: 1
                    to: 999
                }
                FormSpinBox {
                    field: "produce_timeout_cd"
                    label: "推荐卡检测用时上限"
                    from: 20
                    to: 3600
                }
                FormSpinBox {
                    field: "interrupt_timeout"
                    label: "检测超时时间"
                    from: 20
                    to: 3600
                }

                FormSegmentedButton {
                    field: "enable_fever_month"
                    label: "培育前开启活动模式"
                    help: "某些活动期间，在选择培育模式/难度页面的切换活动开关"
                    options: [
                        { label: "不操作", value: "ignore" },
                        { label: "自动启用", value: "on" },
                        { label: "自动禁用", value: "off" }
                    ]
                }

                FormSegmentedButton {
                    field: "produce_engine"
                    label: "培育引擎"
                    options: [
                        { label: "新版·实验性", value: "new" },
                        { label: "旧版", value: "legacy" }
                    ]
                }

                Label {
                    visible: root.solutions.length > 0
                    text: "培育方案的详细编辑请前往「方案」页面"
                    color: palette.placeholderText
                    font.pixelSize: 12
                }
            }
        }
    }
}
