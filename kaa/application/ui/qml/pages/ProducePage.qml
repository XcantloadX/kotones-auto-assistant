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
    property var cardDecks: []
    property var validationIssues: []

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
            root.refreshValidation()
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

    // mode（如 hajime_regular）拆成剧本 + 难度两个 UI 维度；仍写回单个 mode 字段
    readonly property string _modeScript: {
        var _ = sb.data
        var mode = sb.get("mode", "hajime_regular") || "hajime_regular"
        return String(mode).split("_")[0] || "hajime"
    }
    readonly property string _modeDifficulty: {
        var _ = sb.data
        var mode = sb.get("mode", "hajime_regular") || "hajime_regular"
        var parts = String(mode).split("_")
        return parts.length >= 2 ? parts.slice(1).join("_") : "regular"
    }

    // 各剧本的难度选项（HIF 暂仅展示 正赛，选拔赛不在 UI 中暴露）
    function _difficultyOptions(script) {
        if (script === "nia")
            return [
                { label: "PRO", value: "pro" },
                { label: "MASTER", value: "master" }
            ]
        if (script === "hif")
            return [
                { label: "正赛", value: "main" }
            ]
        return [
            { label: "REGULAR", value: "regular" },
            { label: "PRO", value: "pro" },
            { label: "MASTER", value: "master" }
        ]
    }

    // 各剧本的培育策略选项（初/NIA 仅「普通」；HIF 仅「正赛弃赛」）。
    // 直接按剧本调整选项列表，而不是通过 disabled 显示不可选项。
    function _strategyOptions(script) {
        if (script === "hif")
            return [ { label: "正赛弃赛", value: "withdraw_main" } ]
        return [ { label: "普通", value: "normal" } ]
    }

    // 当前剧本下合法的培育策略值；切换剧本后残留的旧值会被回退到首个合法选项
    readonly property string _strategyValue: {
        var _ = sb._revision
        var opts = root._strategyOptions(root._modeScript)
        var v = sb.get("produce_strategy", opts.length > 0 ? opts[0].value : null)
        for (var i = 0; i < opts.length; ++i)
            if (opts[i].value === v) return v
        return opts.length > 0 ? opts[0].value : null
    }

    function _setMode(script, difficulty) {
        // 剧本切换后难度可能不再适用（如 hajime_regular → hif），回退到首个合法难度
        var diffOpts = root._difficultyOptions(script)
        var diff = difficulty
        var diffValid = false
        for (var i = 0; i < diffOpts.length; ++i) {
            if (diffOpts[i].value === diff) { diffValid = true; break }
        }
        if (!diffValid && diffOpts.length > 0) diff = diffOpts[0].value
        // 剧本切换后培育策略可能不再适用，重置为当前剧本的首个合法策略
        var strategyOpts = root._strategyOptions(script)
        var strategy = sb.get("produce_strategy", strategyOpts.length > 0 ? strategyOpts[0].value : null)
        var strategyValid = false
        for (var i = 0; i < strategyOpts.length; ++i) {
            if (strategyOpts[i].value === strategy) { strategyValid = true; break }
        }
        if (!strategyValid && strategyOpts.length > 0)
            sb.set("produce_strategy", strategyOpts[0].value)
        sb.set("mode", script + "_" + diff)
    }

    // ── 初始化 ────────────────────────────────────────
    function loadStaticData() {
        if (!produceCtrl) return
        idolCards      = JSON.parse(produceCtrl.idolCardsJson())
        produceActions = JSON.parse(produceCtrl.produceActionsJson())
        cardDecks      = JSON.parse(produceCtrl.cardDecksJson())
    }

    function markClean() { dirty = false; if (produceCtrl) produceCtrl.markClean() }
    function markDirty() { dirty = true;  if (produceCtrl) produceCtrl.markDirty() }

    function selectSolution(id) {
        if (!produceCtrl || !id) { currentSolution = null; validationIssues = []; markClean(); return }
        var raw = produceCtrl.solutionJson(id)
        if (raw && raw !== '{}') { currentSolution = JSON.parse(raw); markClean(); refreshValidation() }
    }

    // 校验当前方案，刷新 validationIssues（供内联 FormNotice 展示）
    function refreshValidation() {
        validationIssues = []
        if (!produceCtrl || !currentSolution) return
        try {
            var raw = produceCtrl.validateSolution(JSON.stringify(currentSolution))
            validationIssues = JSON.parse(raw) || []
        } catch (err) {
            validationIssues = []
        }
    }

    // 是否存在 error 级校验问题
    function hasValidationErrors() {
        for (var i = 0; i < validationIssues.length; ++i) {
            if (validationIssues[i].severity === "error") return true
        }
        return false
    }

    function validationSummary() {
        var lines = []
        for (var i = 0; i < validationIssues.length; ++i)
            lines.push("• " + validationIssues[i].message)
        return lines.join("\n")
    }

    function save() {
        if (!produceCtrl || !currentSolution) return
        refreshValidation()
        if (root.hasValidationErrors()) {
            Notice.show("error", "存在配置错误，请修正后再保存。")
            return
        }
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

    // ── 行动优先级编辑器 ──────────────────────────────
    Dialog {
        id: actionsPriorityDialog
        title: "行动优先级"
        modal: true
        anchors.centerIn: Overlay.overlay
        width: 520
    height: Math.min(root.height - 40, 620)
    standardButtons: Dialog.Close

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

                    Item {
                        id: gripHandle
                        implicitWidth: 20
                        implicitHeight: 28
                        Layout.alignment: Qt.AlignVCenter
                        opacity: delegateRoot.isDragSource ? 0.4 : 1.0

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
                                let lv = delegateRoot.ListView.view
                                let pt = mapToItem(lv, mouseX, mouseY)
                                let h = delegateRoot.height
                                let mouseIdx = Math.max(0, Math.min(
                                    Math.floor(pt.y / h), lv.count - 1))
                                if (mouseIdx !== root._dragCurrentIndex) {
                                    root._moveDelegateItem(root._dragCurrentIndex, mouseIdx)
                                    root._dragCurrentIndex = mouseIdx
                                }
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
            anchors.fill: parent
            spacing: 6

            Label {
                text: "从上到下依次尝试"
                color: palette.placeholderText
                font.pixelSize: 11
                Layout.fillWidth: true
            }

            ScrollView {
                id: actionsScrollView
                Layout.fillWidth: true
                Layout.fillHeight: true
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
                Layout.fillWidth: true
                Select {
                    id: addActionCombo
                    Layout.fillWidth: true
                    model: {
                        var current = root.currentSolution ? root.currentSolution.data.actions_order : []
                        return root.produceActions.filter(function(a) { return !current.includes(a.value) })
                    }
                    textRole: "display_name"
                    valueRole: "value"
                }
                Button {
                    text: "添加"
                    enabled: addActionCombo.currentValue !== undefined
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

                    // 方案校验提示：存在配置问题时内联展示，阻止保存
                    FormNotice {
                        Layout.fillWidth: true
                        visible: root.validationIssues.length > 0
                        style: root.hasValidationErrors() ? "error" : "warning"
                        title: root.hasValidationErrors() ? "存在配置错误，请修正后保存" : "配置提示"
                        content: root.validationSummary()
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
                            label: "剧本"
                            options: [
                                { label: "初", value: "hajime" },
                                { label: "HIF", value: "hif" }
                            ]
                            value: root._modeScript
                            onUserSelected: function(v) { root._setMode(v, root._modeDifficulty) }
                        }
                        FormSegmentedButton {
                            label: "难度"
                            options: root._difficultyOptions(root._modeScript)
                            value: root._modeDifficulty
                            onUserSelected: function(v) { root._setMode(root._modeScript, v) }
                        }
                        FormSegmentedButton {
                            label: "培育策略"
                            options: root._strategyOptions(root._modeScript)
                            value: root._strategyValue
                            onUserSelected: function(v) { sb.set("produce_strategy", v) }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            // HIF 剧本无需选择偶像（由游戏内自动选中），隐藏选择器
                            visible: root._modeScript !== "hif"

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
                        visible: root.currentSolution !== null && root._modeScript !== "hif"
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
                        }
                        FormNotice {
                            style: "info"
                            title: ""
                            visible: sb.get("auto_set_memory", false)
                            content: "此编号的回忆会被覆盖，注意选择空闲编号槽位。"
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
                        }
                        FormNotice {
                            style: "info"
                            title: ""
                            visible: sb.get("auto_set_support_card", false)
                            content: "此编号的支援卡编成会被覆盖，注意选择空闲编号槽位。"
                        }
                    }

                    // ── HIF 编成设置 ────────────────────────────
                    FormGroupBox {
                        title: "HIF 编成设置"
                        visible: root.currentSolution !== null && root._modeScript === "hif"
                        binder: sb
                        Text {
                            text: "暂不支持指定 HIF 回忆编成。将会使用游戏内自动选中的回忆。"
                            font.pixelSize: 14
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
                        FormField {
                            labelText: "行动优先级"
                            control: Component {
                                Button {
                                    text: "配置行动优先级"
                                    onClicked: {
                                        root._rebuildModel()
                                        actionsPriorityDialog.open()
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
