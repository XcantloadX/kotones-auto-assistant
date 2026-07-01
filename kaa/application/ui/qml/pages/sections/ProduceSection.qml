import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components/controls"
import "../../components/form"

// 培育设置：当前使用哪个方案等
Item {
    id: root
    property var settingsCtrl
    signal modified()

    property var solutions: []

    readonly property var _produce: settingsCtrl?.config?.profile?.tasks?.produce ?? {}

    function loadSolutions() {
        if (settingsCtrl) solutions = JSON.parse(settingsCtrl.produceSolutionsJson())
    }

    Component.onCompleted: loadSolutions()
    Connections {
        target: settingsCtrl
        function onConfigChanged() { loadSolutions() }
    }

    // 方案页创建/删除方案后刷新方案列表
    Connections {
        target: typeof TabManager !== "undefined" ? TabManager.activeProduceController : null
        function onSolutionsChanged() { loadSolutions() }
    }

    FormBinder {
        id: pb
        data: root._produce
        onCommitted: function(key, value) {
            var c = JSON.parse(JSON.stringify(settingsCtrl.config))
            c.profile.tasks.produce[key] = value
            settingsCtrl.commitConfig(JSON.stringify(c))
            modified()
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
