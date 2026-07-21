import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQml.Models
import "../components"
import "../components/controls"
import "../components/form"

// 培育方案管理：左侧方案列表（使用 ProduceSolutionsModel）+ 右侧编辑表单
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
    property var currentSolution: null
    property bool dirty: false

    property var idolCards: []
    property var produceActions: []
    property var detectModes: []
    property var cardDecks: []

    // 拖拽排序状态（行动优先级列表）
    property int _dragCurrentIndex: -1
    property var _currentOrder: []
    readonly property bool _dragging: _dragCurrentIndex >= 0
    property real _autoScrollVelocity: 0

    ListModel { id: actionsModel }

    function _rebuildModel() {
        actionsModel.clear()
        if (!root.currentSolution) return
        var order = root.currentSolution.data.actions_order
        for (var i = 0; i < order.length; ++i) {
            var found = root.produceActions.find(function(a) { return a.value === order[i] })
            actionsModel.append({ value: order[i], label: found ? found.display_name : order[i] })
        }
    }

    function _moveDelegateItem(from, to) {
        if (from === to) return
        actionsDelegateModel.items.move(from, to)
        let arr = root._currentOrder.slice()
        let item = arr.splice(from, 1)[0]
        arr.splice(to, 0, item)
        root._currentOrder = arr
    }

    function _updateAutoScroll(rootY) {
        let svY = root.mapToItem(actionsScrollView, 0, rootY).y
        let threshold = 30
        let maxSpeed  = 8
        let svh = actionsScrollView.height
        if (svY < threshold) {
            root._autoScrollVelocity = -((threshold - Math.max(0, svY)) / threshold) * maxSpeed
        } else if (svY > svh - threshold) {
            root._autoScrollVelocity = ((Math.min(svh, svY) - (svh - threshold)) / threshold) * maxSpeed
        } else {
            root._autoScrollVelocity = 0
        }
    }

    onCurrentSolutionChanged: _rebuildModel()

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
        cardDecks      = JSON.parse(produceCtrl.cardDecksJson())
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
        if (root.solutionNameExists(currentSolution.name, currentSolution.id)) {
            renameConflictDialog.open()
            return
        }
        if (produceCtrl.saveSolution(JSON.stringify(currentSolution))) markClean()
    }

    function deleteSolution(id) {
        if (!produceCtrl || !id) return
        produceCtrl.deleteSolution(id)
        if (currentSolution && currentSolution.id === id) { currentSolution = null; markClean() }
    }

    function solutionNameExists(name, excludeId) {
        if (!produceCtrl || !name) return false
        return produceCtrl.checkSolutionNameExists(name, excludeId || "")
    }

    function idolDisplayText(card) {
        if (!card) return ""
        return card.is_another && card.another_name
            ? card.name + " 「" + card.another_name + "」"
            : card.name
    }

    Component.onCompleted: loadStaticData()

    Connections {
        target: produceCtrl
        function onSaveRequested()    { root.save() }
        function onDiscardRequested() { root.selectSolution(root.currentSolution ? root.currentSolution.id : "") }
        function onOperationSucceeded(msg) { Notice.show("success", msg) }
        function onOperationFailed(msg) { Notice.show("error", msg) }
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

        footer: DialogButtonBox {
            Button { text: "取消"; onClicked: createDialog.close() }
            Button {
                text: "确定"; highlighted: true
                enabled: createNameField.text.trim().length > 0
                onClicked: {
                    var name = createNameField.text.trim()
                    if (!name || !produceCtrl) return
                    if (root.solutionNameExists(name, "")) {
                        createNameError.visible = true
                        return
                    }
                    createDialog.accept()
                }
            }
        }

        onOpened: {
            createNameField.text = "新培育方案"
            createNameField.selectAll()
            createNameField.forceActiveFocus()
            createNameError.visible = false
        }
        onAccepted: {
            var name = createNameField.text.trim()
            if (!name || !produceCtrl) return
            var raw = produceCtrl.createSolution(name)
            if (raw && raw !== '{}') { root.currentSolution = JSON.parse(raw); root.markClean() }
        }

        ColumnLayout {
            spacing: 8; width: parent.width
            Label { text: "请输入方案名称：" }
            TextField {
                id: createNameField
                Layout.fillWidth: true
                onTextChanged: createNameError.visible = false
                Keys.onReturnPressed: {
                    var name = createNameField.text.trim()
                    if (name && produceCtrl && !root.solutionNameExists(name, ""))
                        createDialog.accept()
                }
            }
            Label {
                id: createNameError
                text: "该名称已被其他方案使用"
                color: "red"; visible: false; font.pixelSize: 12
            }
        }
    }

    Dialog {
        id: duplicateDialog
        title: "复制培育方案"
        modal: true; anchors.centerIn: parent; width: 320
        property string sourceName: ""
        property string sourceId: ""

        footer: DialogButtonBox {
            Button { text: "取消"; onClicked: duplicateDialog.close() }
            Button {
                text: "确定"; highlighted: true
                enabled: duplicateNameField.text.trim().length > 0
                onClicked: {
                    var name = duplicateNameField.text.trim()
                    if (!produceCtrl || !root.currentSolution) return
                    if (root.solutionNameExists(name, "")) {
                        duplicateNameError.visible = true
                        return
                    }
                    duplicateDialog.accept()
                }
            }
        }

        onOpened: {
            duplicateNameField.text = sourceName + " 副本"
            duplicateNameField.selectAll()
            duplicateNameField.forceActiveFocus()
            duplicateNameError.visible = false
        }
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
            TextField {
                id: duplicateNameField
                Layout.fillWidth: true
                onTextChanged: duplicateNameError.visible = false
                Keys.onReturnPressed: {
                    var name = duplicateNameField.text.trim()
                    if (produceCtrl && root.currentSolution && !root.solutionNameExists(name, ""))
                        duplicateDialog.accept()
                }
            }
            Label {
                id: duplicateNameError
                text: "该名称已被其他方案使用"
                color: "red"; visible: false; font.pixelSize: 12
            }
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

    Dialog {
        id: renameConflictDialog
        title: "名称冲突"
        modal: true; anchors.centerIn: parent; width: 360
        standardButtons: Dialog.Ok
        Label {
            text: "该名称已被其他方案使用，请使用不同的名称后重试。"
            wrapMode: Text.Wrap; width: parent.width
            leftPadding: 8; topPadding: 4
        }
    }

    // ── 布局 ──────────────────────────────────────────

    Item {
        anchors.fill: parent
        visible: solutionList.count === 0

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
        visible: solutionList.count > 0

        // ── 左侧：方案列表（使用 ProduceSolutionsModel）───
        ColumnLayout {
            Layout.preferredWidth: 220; Layout.maximumWidth: 220
            Layout.fillWidth: false; Layout.fillHeight: true
            spacing: 8

            Button { text: "新建培育"; highlighted: true; Layout.fillWidth: true; onClicked: createDialog.open() }

            ListView {
                id: solutionList
                Layout.fillWidth: true; Layout.fillHeight: true
                clip: true; model: produceCtrl.solutionsModel; spacing: 4

                delegate: ItemDelegate {
                    id: delegateItem
                    width: solutionList.width
                    highlighted: root.currentSolution && root.currentSolution.id === model.id

                    contentItem: RowLayout {
                        spacing: 4
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 2
                            Label {
                                text: model.name; font.bold: delegateItem.highlighted
                                Layout.fillWidth: true; elide: Text.ElideRight
                            }
                            Label {
                                text: model.description || ""; font.pixelSize: 11
                                color: palette.placeholderText; visible: text.length > 0
                                elide: Text.ElideRight; Layout.fillWidth: true
                            }
                        }
                        RowLayout {
                            spacing: 0
                            ToolButton {
                                text: "⧉"; font.pixelSize: 14; implicitWidth: 28; implicitHeight: 28
                                ToolTip.text: "复制"; ToolTip.visible: hovered; ToolTip.delay: 500
                                onClicked: { duplicateDialog.sourceName = model.name; duplicateDialog.open() }
                            }
                            ToolButton {
                                text: "✕"; font.pixelSize: 13; implicitWidth: 28; implicitHeight: 28
                                ToolTip.text: "删除"; ToolTip.visible: hovered; ToolTip.delay: 500
                                onClicked: {
                                    deleteDialog.targetId = model.id
                                    deleteDialog.targetName = model.name
                                    deleteDialog.open()
                                }
                            }
                        }
                    }
                    onClicked: {
                        if (root.dirty && root.currentSolution && root.currentSolution.id !== model.id) {
                            root.pendingSolutionId = model.id
                            unsavedConfirmDialog.open()
                        } else {
                            root.selectSolution(model.id)
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
                        FormComboBox {
                            field: "card_deck_id"
                            label: "技能卡组"
                            options: {
                                var items = [{ label: "自动", value: "" }]
                                for (var i = 0; i < root.cardDecks.length; ++i) {
                                    var d = root.cardDecks[i]
                                    items.push({ label: d.name, value: d.value })
                                }
                                return items
                            }
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
                    GroupBox {
                        title: "行动优先级"
                        Layout.fillWidth: true
                        visible: root.currentSolution !== null

                        Timer {
                            id: autoScrollTimer
                            interval: 16
                            repeat: true
                            running: root._dragging && root._autoScrollVelocity !== 0
                            onTriggered: {
                                let f = actionsScrollView.contentItem
                                let maxY = Math.max(0, f.contentHeight - f.height)
                                f.contentY = Math.max(0, Math.min(f.contentY + root._autoScrollVelocity, maxY))
                            }
                        }

                        DelegateModel {
                            id: actionsDelegateModel
                            model: actionsModel

                            delegate: Item {
                                id: delegateRoot
                                required property int index
                                required property var modelData

                                property int visualIndex: DelegateModel.itemsIndex

                                readonly property bool isDragSource:
                                    root._dragging && root._dragCurrentIndex === delegateRoot.visualIndex

                                width: ListView.view.width
                                height: rowContent.implicitHeight

                                ItemDelegate {
                                    id: rowContent
                                    width: parent.width
                                    highlighted: delegateRoot.isDragSource
                                    topPadding: 0
                                    bottomPadding: 0
                                    leftPadding: 8
                                    rightPadding: 4

                                    contentItem: RowLayout {
                                        spacing: 6

                                        // Drag grip handle
                                        Item {
                                            id: gripHandle
                                            implicitWidth: 20
                                            implicitHeight: 28
                                            Layout.alignment: Qt.AlignVCenter
                                            opacity: delegateRoot.isDragSource ? 0.4 : 1.0

                                            // Three short bars as a visual grip indicator
                                            Column {
                                                anchors.centerIn: parent
                                                spacing: 3
                                                Repeater {
                                                    model: 3
                                                    delegate: Rectangle {
                                                        required property int index
                                                        width: 12
                                                        height: 2
                                                        radius: 1
                                                        color: rowContent.palette.mid
                                                    }
                                                }
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.SizeVerCursor
                                                preventStealing: true

                                                onPressed: (mouse) => {
                                                    root._currentOrder = root.currentSolution.data.actions_order.slice()
                                                    root._dragCurrentIndex = delegateRoot.visualIndex
                                                    mouse.accepted = true
                                                }

                                                onPositionChanged: (mouse) => {
                                                    if (!root._dragging) return
                                                    // Reorder
                                                    let lv = delegateRoot.ListView.view
                                                    let pt = mapToItem(lv, mouseX, mouseY)
                                                    let h = delegateRoot.height
                                                    let mouseIdx = Math.max(0, Math.min(
                                                        Math.floor(pt.y / h), lv.count - 1))
                                                    if (mouseIdx !== root._dragCurrentIndex) {
                                                        root._moveDelegateItem(root._dragCurrentIndex, mouseIdx)
                                                        root._dragCurrentIndex = mouseIdx
                                                    }
                                                    // Edge auto-scroll
                                                    root._updateAutoScroll(mapToItem(root, mouseX, mouseY).y)
                                                }

                                                onReleased: {
                                                    root._autoScrollVelocity = 0
                                                    let order = root._currentOrder
                                                    root._dragCurrentIndex = -1
                                                    root._currentOrder = []
                                                    root.currentSolution.data.actions_order = order
                                                    root.markDirty()
                                                }

                                                onCanceled: {
                                                    root._autoScrollVelocity = 0
                                                    let order = root._currentOrder
                                                    root._dragCurrentIndex = -1
                                                    root._currentOrder = []
                                                    root.currentSolution.data.actions_order = order
                                                    root.markDirty()
                                                }
                                            }
                                        }

                                        Label {
                                            Layout.fillWidth: true
                                            text: delegateRoot.modelData.label
                                        }

                                        Button {
                                            text: "✕"
                                            onClicked: {
                                                root.currentSolution.data.actions_order.splice(delegateRoot.visualIndex, 1)
                                                root._rebuildModel()
                                                root.markDirty()
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        ColumnLayout {
                            width: parent.width; spacing: 4

                            Label { text: "从上到下依次尝试"; color: palette.placeholderText; font.pixelSize: 11 }

                            ScrollView {
                                id: actionsScrollView
                                Layout.fillWidth: true
                                implicitHeight: Math.min(contentHeight, 300)
                                clip: true
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                                ColumnLayout {
                                    width: actionsScrollView.availableWidth
                                    spacing: 0

                                    ListView {
                                        id: actionsListView
                                        Layout.fillWidth: true
                                        implicitHeight: contentHeight
                                        interactive: false
                                        clip: false
                                        model: actionsDelegateModel

                                        move: Transition {
                                            NumberAnimation { property: "y"; duration: 150; easing.type: Easing.OutQuad }
                                        }
                                        moveDisplaced: Transition {
                                            NumberAnimation { property: "y"; duration: 150; easing.type: Easing.OutQuad }
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
                                        root._rebuildModel()
                                        root.markDirty()
                                        addActionCombo.currentIndex = 0
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
