import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../components/controls"
import "../components/form"

// 培育方案管理：左侧方案列表 + 右侧编辑表单
PageContainer {
    id: root
    title: "培育方案"

    titleRightContent: RowLayout {
        spacing: 8
        Rectangle {
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
    }

    required property var produceCtrl

    // ── 数据 ──────────────────────────────────────────
    property var solutions: []
    property var currentSolution: null
    property bool dirty: false

    property var idolCards: []
    property var produceActions: []
    property var detectModes: []

    // 方案数据 binder：绑定 ProduceData 子对象（mode、idol、actions_order 等）
    FormBinder {
        id: sb
        data: root.currentSolution?.data ?? null
        onCommitted: function(key, value) {
            root.currentSolution.data[key] = value
            root.markDirty()
        }
    }

    // 方案顶层 binder：绑定 ProduceSolution 顶层（name、description 等）
    // name/description 不在 data 子对象里，需要独立的顶层 binder
    FormBinder {
        id: sb_top
        data: root.currentSolution ?? null
        onCommitted: function(key, value) {
            root.currentSolution[key] = value
            root.markDirty()
        }
    }

    // ── 初始化 ────────────────────────────────────────
    function loadStaticData() {
        if (!produceCtrl) return
        idolCards      = JSON.parse(produceCtrl.idolCardsJson())
        produceActions = JSON.parse(produceCtrl.produceActionsJson())
        detectModes    = JSON.parse(produceCtrl.detectModesJson())
    }

    function loadSolutions() {
        solutions = produceCtrl ? JSON.parse(produceCtrl.solutionsJson()) : []
    }

    function markClean() { dirty = false; if (produceCtrl) produceCtrl.markClean() }
    function markDirty() { dirty = true;  if (produceCtrl) produceCtrl.markDirty() }

    function selectSolution(id) {
        if (!produceCtrl || !id) { currentSolution = null; markClean(); return }
        var raw = produceCtrl.solutionJson(id)
        if (raw && raw !== '{}') { currentSolution = JSON.parse(raw); markClean() }
    }

    function save() {
        if (!produceCtrl || !currentSolution) return
        if (produceCtrl.saveSolution(JSON.stringify(currentSolution))) markClean()
    }

    function deleteSolution(id) {
        if (!produceCtrl || !id) return
        produceCtrl.deleteSolution(id)
        if (currentSolution && currentSolution.id === id) { currentSolution = null; markClean() }
    }

    function idolDisplayText(card) {
        if (!card) return ""
        return card.is_another && card.another_name
            ? card.name + " 「" + card.another_name + "」"
            : card.name
    }

    Component.onCompleted: { loadStaticData(); loadSolutions() }

    Connections {
        target: produceCtrl
        function onSolutionsChanged() { root.loadSolutions() }
        function onSaveRequested()    { root.save() }
        function onDiscardRequested() { root.selectSolution(root.currentSolution ? root.currentSolution.id : "") }
    }

    // ── 未保存确认对话框 ─────────────────────────────
    property string pendingSolutionId: ""

    Dialog {
        id: unsavedConfirmDialog
        title: "提示"
        modal: true
        anchors.centerIn: Overlay.overlay
        width: 360
        standardButtons: Dialog.NoButton

        ColumnLayout {
            spacing: 16
            width: parent.width

            Label {
                text: "有未保存的改动，是否保存？"
                wrapMode: Text.Wrap
                Layout.fillWidth: true
                Layout.topMargin: 8
            }

            RowLayout {
                spacing: 8
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignRight

                Button {
                    text: "继续编辑"
                    onClicked: {
                        root.pendingSolutionId = ""
                        unsavedConfirmDialog.close()
                    }
                }
                Button {
                    text: "丢弃"
                    onClicked: {
                        var id = root.pendingSolutionId
                        root.pendingSolutionId = ""
                        root.selectSolution(id)
                        unsavedConfirmDialog.close()
                    }
                }
                Button {
                    text: "保存"
                    highlighted: true
                    onClicked: {
                        var id = root.pendingSolutionId
                        root.pendingSolutionId = ""
                        root.save()
                        root.selectSolution(id)
                        unsavedConfirmDialog.close()
                    }
                }
            }
        }
    }

    // ── 偶像选择器 ─────────────────────────────────────
    IdolPickerDialog {
        id: idolPickerDialog
        idolCards: root.idolCards
        onIdolSelected: function(skinId) {
            sb.set("idol", skinId)
        }
        onOpened: {
            // 打开时同步当前已选中的 skin_id
            selectedSkinId = sb.get("idol", "")
            if (selectedSkinId) {
                for (var i = 0; i < root.idolCards.length; i++) {
                    if (root.idolCards[i].skin_id === selectedSkinId) {
                        selectedDisplayName = root.idolDisplayText(root.idolCards[i])
                        break
                    }
                }
            }
        }
    }

    // ── 对话框 ────────────────────────────────────────
    Dialog {
        id: createDialog
        title: "新建培育方案"
        modal: true; anchors.centerIn: parent; width: 320
        standardButtons: Dialog.Ok | Dialog.Cancel
        onOpened: { createNameField.text = "新培育方案"; createNameField.selectAll(); createNameField.forceActiveFocus() }
        onAccepted: {
            var name = createNameField.text.trim()
            if (!name || !produceCtrl) return
            var raw = produceCtrl.createSolution(name)
            if (raw && raw !== '{}') { root.currentSolution = JSON.parse(raw); root.markClean() }
        }
        ColumnLayout {
            spacing: 8; width: parent.width
            Label { text: "请输入方案名称：" }
            TextField { id: createNameField; Layout.fillWidth: true; Keys.onReturnPressed: createDialog.accept() }
        }
    }

    Dialog {
        id: duplicateDialog
        title: "复制培育方案"
        modal: true; anchors.centerIn: parent; width: 320
        standardButtons: Dialog.Ok | Dialog.Cancel
        property string sourceName: ""
        onOpened: { duplicateNameField.text = sourceName + " 副本"; duplicateNameField.selectAll(); duplicateNameField.forceActiveFocus() }
        onAccepted: {
            if (!produceCtrl || !root.currentSolution) return
            var raw = produceCtrl.duplicateSolution(root.currentSolution.id)
            if (raw && raw !== '{}') {
                var sol = JSON.parse(raw)
                var name = duplicateNameField.text.trim()
                if (name && name !== sol.name) { sol.name = name; produceCtrl.saveSolution(JSON.stringify(sol)) }
                root.currentSolution = sol; root.markClean()
            }
        }
        ColumnLayout {
            spacing: 8; width: parent.width
            Label { text: "请输入新方案名称：" }
            TextField { id: duplicateNameField; Layout.fillWidth: true; Keys.onReturnPressed: duplicateDialog.accept() }
        }
    }

    Dialog {
        id: deleteDialog
        title: "删除培育方案"
        modal: true; anchors.centerIn: parent; width: 320
        standardButtons: Dialog.Yes | Dialog.No
        property string targetId: ""
        property string targetName: ""
        Label {
            text: "确定要删除方案「" + deleteDialog.targetName + "」吗？此操作不可撤销。"
            wrapMode: Text.Wrap; width: parent.width
        }
        onAccepted: root.deleteSolution(targetId)
    }

    // ── 布局 ──────────────────────────────────────────

    Item {
        anchors.fill: parent
        visible: root.solutions.length === 0

        ColumnLayout {
            anchors.centerIn: parent
            spacing: 20; width: 320
            Text { text: "🎵"; font.pixelSize: 56; Layout.alignment: Qt.AlignHCenter }
            Label { text: "还没有培育方案"; font.pixelSize: 20; font.bold: true; Layout.alignment: Qt.AlignHCenter }
            Label {
                text: "新建一个方案，配置偶像、卡组和行动策略，\n然后在控制页启动自动培育。"
                font.pixelSize: 13; color: palette.placeholderText
                horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap
                Layout.alignment: Qt.AlignHCenter; Layout.fillWidth: true
            }
            Button {
                text: "+ 新建培育方案"; highlighted: true
                Layout.alignment: Qt.AlignHCenter; implicitWidth: 200; implicitHeight: 44
                onClicked: createDialog.open()
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 8
        visible: root.solutions.length > 0

        // ── 左侧：方案列表 ────────────────────────────
        ColumnLayout {
            Layout.preferredWidth: 220; Layout.maximumWidth: 220
            Layout.fillWidth: false; Layout.fillHeight: true
            spacing: 8

            Button { text: "新建培育"; highlighted: true; Layout.fillWidth: true; onClicked: createDialog.open() }

            ListView {
                id: solutionList
                Layout.fillWidth: true; Layout.fillHeight: true
                clip: true; model: root.solutions; spacing: 4

                delegate: ItemDelegate {
                    id: delegateItem
                    width: solutionList.width
                    highlighted: root.currentSolution && root.currentSolution.id === modelData.id

                    contentItem: RowLayout {
                        spacing: 4
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 2
                            Label {
                                text: modelData.name; font.bold: delegateItem.highlighted
                                Layout.fillWidth: true; elide: Text.ElideRight
                            }
                            Label {
                                text: modelData.description || ""; font.pixelSize: 11
                                color: palette.placeholderText; visible: text.length > 0
                                elide: Text.ElideRight; Layout.fillWidth: true
                            }
                        }
                        RowLayout {
                            spacing: 0
                            ToolButton {
                                text: "⧉"; font.pixelSize: 14; implicitWidth: 28; implicitHeight: 28
                                ToolTip.text: "复制"; ToolTip.visible: hovered; ToolTip.delay: 500
                                onClicked: { duplicateDialog.sourceName = modelData.name; duplicateDialog.open() }
                            }
                            ToolButton {
                                text: "✕"; font.pixelSize: 13; implicitWidth: 28; implicitHeight: 28
                                ToolTip.text: "删除"; ToolTip.visible: hovered; ToolTip.delay: 500
                                onClicked: {
                                    deleteDialog.targetId = modelData.id
                                    deleteDialog.targetName = modelData.name
                                    deleteDialog.open()
                                }
                            }
                        }
                    }
                    onClicked: {
                        if (root.dirty && root.currentSolution && root.currentSolution.id !== modelData.id) {
                            root.pendingSolutionId = modelData.id
                            unsavedConfirmDialog.open()
                        } else {
                            root.selectSolution(modelData.id)
                        }
                    }
                }
            }
        }

        // ── 右侧：编辑表单 ─────────────────────────────
        Item {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true

            Item {
                anchors.fill: parent
                visible: root.currentSolution === null
                ColumnLayout {
                    anchors.centerIn: parent; spacing: 16
                    Label { text: "尚未选择培育方案"; color: palette.placeholderText; font.pixelSize: 16; Layout.alignment: Qt.AlignHCenter }
                    Label { text: "从左侧列表选择，或点击下方按钮新建"; color: palette.placeholderText; font.pixelSize: 12; Layout.alignment: Qt.AlignHCenter }
                    Button { text: "+ 新建培育方案"; highlighted: true; Layout.alignment: Qt.AlignHCenter; onClicked: createDialog.open() }
                }
            }

            ScrollView {
                anchors.fill: parent; clip: true; contentWidth: availableWidth
                visible: root.currentSolution !== null

                ColumnLayout {
                    width: parent.width; spacing: 12

                    Pane {
                        Layout.fillWidth: true; visible: root.dirty; padding: 8
                        background: Rectangle { color: palette.base; opacity: 0.06 }
                        RowLayout {
                            width: parent.width
                            Label { text: "有未保存的更改"; Layout.fillWidth: true }
                            Button { text: "保存"; highlighted: true; onClicked: root.save() }
                            Button { text: "放弃"; onClicked: root.selectSolution(root.currentSolution ? root.currentSolution.id : "") }
                        }
                    }

                    // ── 方案信息 ──────────────────────────────
                    FormGroupBox {
                        title: "方案信息"
                        visible: root.currentSolution !== null
                        binder: sb_top

                        FormTextField {
                            field: "name"
                            label: "方案名称"
                        }
                        FormTextField {
                            field: "description"
                            label: "方案描述"
                        }
                    }

                    // ── 基本设置 ──────────────────────────────
                    FormGroupBox {
                        title: "基本设置"
                        visible: root.currentSolution !== null
                        binder: sb

                        FormSegmentedButton {
                            field: "mode"
                            label: "培育模式"
                            options: [
                                { label: "REGULAR", value: "regular" },
                                { label: "PRO", value: "pro" },
                                { label: "MASTER", value: "master" }
                            ]
                        }
                        // 自定义行：左侧 label + 右侧选择按钮（替换 FormComboBox）
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            RowLayout {
                                Layout.preferredWidth: 120
                                spacing: 6
                                Label { text: "选择要培育的偶像"; Layout.alignment: Qt.AlignVCenter }
                            }

                            Button {
                                id: idolPickerButton
                                Layout.fillWidth: true
                                text: {
                                    var _ = sb._revision
                                    var sid = sb.get("idol", null)
                                    if (!sid) return "未选择"
                                    for (var i = 0; i < root.idolCards.length; i++) {
                                        if (root.idolCards[i].skin_id === sid)
                                            return root.idolDisplayText(root.idolCards[i])
                                    }
                                    return sid
                                }
                                onClicked: idolPickerDialog.open()
                            }
                        }
                        FormSegmentedButton {
                            field: "battle_strategy"
                            label: "打牌策略"
                            options: [
                                { label: "游戏 AI", value: "bandai" },
                                { label: "脚本简单 AI（实验性）", value: "expert" }
                            ]
                        }
                    }

                    // ── 编成设置 ──────────────────────────────
                    FormGroupBox {
                        title: "编成设置"
                        visible: root.currentSolution !== null
                        binder: sb

                        FormCheckBox {
                            field: "auto_set_memory"
                            label: "自动编成回忆"
                        }
                        FormSpinBox {
                            field: "memory_set"
                            label: "回忆编成编号"
                            labelWidth: 100
                            from: 1
                            to: 20
                            enabled: !sb.get("auto_set_memory", false)
                        }
                        FormCheckBox {
                            field: "auto_set_support_card"
                            label: "自动编成支援卡"
                        }
                        FormSpinBox {
                            field: "support_card_set"
                            label: "支援卡编成编号"
                            labelWidth: 100
                            from: 1
                            to: 20
                            enabled: !sb.get("auto_set_support_card", false)
                        }
                        FormNotice {
                            style: "info"
                            title: ""
                            content: "目前只能自动编成支援卡，无论是否勾选「自动编成支援卡」，队伍编制均不受此开关影响"
                        }
                    }

                    // ── 强化设置 ──────────────────────────────
                    FormGroupBox {
                        title: "强化设置"
                        visible: root.currentSolution !== null
                        binder: sb

                        FormCheckBox {
                            field: "use_pt_boost"
                            label: "使用支援强化 Pt 提升"
                        }
                        FormCheckBox {
                            field: "use_note_boost"
                            label: "使用笔记数提升"
                        }
                        FormCheckBox {
                            field: "follow_producer"
                            label: "关注租借了支援卡的制作人"
                        }
                    }

                    // ── 课程设置 ──────────────────────────────
                    FormGroupBox {
                        title: "课程设置"
                        visible: root.currentSolution !== null
                        binder: sb

                        FormSegmentedButton {
                            field: "self_study_lesson"
                            label: "文化课自习时选项"
                            options: [
                                { label: "舞蹈", value: "dance" },
                                { label: "形象", value: "visual" },
                                { label: "声乐", value: "vocal" }
                            ]
                        }
                        FormCheckBox {
                            field: "prefer_lesson_ap"
                            label: "SP 课程优先"
                        }
                    }

                    // ── 行动优先级 ────────────────────────────
                    // 直接操作数组，不通过 binder，保留原有写法
                    GroupBox {
                        title: "行动优先级"
                        Layout.fillWidth: true
                        visible: root.currentSolution !== null
                        ColumnLayout {
                            width: parent.width; spacing: 4

                            Label { text: "从上到下依次尝试"; color: palette.placeholderText; font.pixelSize: 11 }

                            ListView {
                                id: actionsList
                                Layout.fillWidth: true; implicitHeight: contentHeight; clip: true; spacing: 2
                                model: root.currentSolution ? root.currentSolution.data.actions_order : []

                                delegate: RowLayout {
                                    width: actionsList.width; spacing: 4
                                    Label {
                                        text: {
                                            var found = root.produceActions.find(function(a) { return a.value === modelData })
                                            return found ? found.display_name : modelData
                                        }
                                        Layout.fillWidth: true
                                    }
                                    Button {
                                        text: "↑"; enabled: index > 0
                                        onClicked: {
                                            var arr = root.currentSolution.data.actions_order
                                            var tmp = arr[index - 1]; arr[index - 1] = arr[index]; arr[index] = tmp
                                            root.markDirty(); actionsList.modelChanged()
                                        }
                                    }
                                    Button {
                                        text: "↓"; enabled: index < root.currentSolution.data.actions_order.length - 1
                                        onClicked: {
                                            var arr = root.currentSolution.data.actions_order
                                            var tmp = arr[index + 1]; arr[index + 1] = arr[index]; arr[index] = tmp
                                            root.markDirty(); actionsList.modelChanged()
                                        }
                                    }
                                    Button {
                                        text: "✕"
                                        onClicked: {
                                            root.currentSolution.data.actions_order.splice(index, 1)
                                            root.markDirty(); actionsList.modelChanged()
                                        }
                                    }
                                }
                            }

                            RowLayout {
                                spacing: 4
                                Select {
                                    id: addActionCombo
                                    Layout.fillWidth: true
                                    model: {
                                        var current = root.currentSolution ? root.currentSolution.data.actions_order : []
                                        return root.produceActions.filter(function(a) { return !current.includes(a.value) })
                                    }
                                    textRole: "display_name"; valueRole: "value"
                                }
                                Button {
                                    text: "添加"; enabled: addActionCombo.currentValue !== undefined
                                    onClicked: {
                                        root.currentSolution.data.actions_order.push(addActionCombo.currentValue)
                                        root.markDirty(); actionsList.modelChanged(); addActionCombo.currentIndex = 0
                                    }
                                }
                            }
                        }
                    }

                    // ── 检测与道具 ────────────────────────────
                    FormGroupBox {
                        title: "检测与道具"
                        visible: root.currentSolution !== null
                        binder: sb

                        FormComboBox {
                            field: "recommend_card_detection_mode"
                            label: "推荐卡检测模式"
                            options: root.detectModes.map(function(mode) {
                                return { label: mode.display_name, value: mode.value }
                            })
                        }
                        FormCheckBox {
                            field: "use_ap_drink"
                            label: "AP 不足时自动使用 AP 饮料"
                        }
                        FormCheckBox {
                            field: "skip_commu"
                            label: "检测并跳过交流"
                        }
                        FormNotice {
                            style: "warning"
                            title: ""
                            visible: sb.get("skip_commu", false)
                            content: "建议关闭此处设置，转而开启游戏内快进所有交流，效果更佳。"
                        }
                    }
                }
            }
        }
    }
}
