import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "./controls"

// 偶像选择弹窗：搜索 + 分类列表 + 卡片网格。
// 使用方式：
//   IdolPickerDialog {
//       idolCards: root.idolCards
//       onIdolSelected: function(skinId) { sb.set("idol", skinId) }
//   }
Dialog {
    id: root

    title: "选择要培育的偶像"
    modal: true
    anchors.centerIn: Overlay.overlay

    width: Math.min(1000, Overlay.overlay ? Overlay.overlay.width * 0.9 : 1000)
    height: Math.min(600, Overlay.overlay ? Overlay.overlay.height * 0.85 : 600)

    // ── 输入 ──────────────────────────────────────────
    property var idolCards: []           // 所有卡片数据（从 produceCtrl 加载）
    property string selectedSkinId: ""   // 当前选中的 skin_id
    property string selectedDisplayName: ""  // 当前选中的显示文本

    // ── 内部状态 ──────────────────────────────────────
    property string _currentCharacterId: ""
    property string _searchText: ""
    property bool _showAfter: false
    property var _characters: []    // [{character_id, character_name, count}]

    // 根据分类+搜索过滤后的卡片列表
    property var _filteredCards: {
        var cards = root.idolCards
        var charId = root._currentCharacterId
        var search = root._searchText.trim().toLowerCase()

        // 先按分类过滤
        if (charId) {
            cards = cards.filter(function(c) { return c.character_id === charId })
        }
        // 再按搜索过滤
        if (search) {
            cards = cards.filter(function(c) {
                return c.name.toLowerCase().indexOf(search) >= 0
                    || (c.another_name && c.another_name.toLowerCase().indexOf(search) >= 0)
                    || c.character_name.toLowerCase().indexOf(search) >= 0
            })
        }
        return cards
    }

    // 从卡片数据构建分类列表
    function _buildCharacters() {
        var map = {}
        for (var i = 0; i < root.idolCards.length; i++) {
            var c = root.idolCards[i]
            if (!map[c.character_id]) {
                map[c.character_id] = { character_id: c.character_id, character_name: c.character_name, count: 0 }
            }
            map[c.character_id].count++
        }
        var result = []
        for (var key in map) result.push(map[key])
        // 保持数据库中出现的顺序（按首次出现排序）
        var order = {}
        for (var i = 0; i < root.idolCards.length; i++) {
            var cid = root.idolCards[i].character_id
            if (order[cid] === undefined) order[cid] = Object.keys(order).length
        }
        result.sort(function(a, b) { return order[a.character_id] - order[b.character_id] })
        // 在最前面插入「全部」分类
        result.unshift({ character_id: "", character_name: "全部", count: root.idolCards.length })
        root._characters = result

        // 默认选中第一个分类（如果当前没有选中任何分类）
        if (!root._currentCharacterId && result.length > 0) {
            root._currentCharacterId = result[0].character_id
        }
    }

    // 查找卡片在 idolCards 中的索引
    function _findCardIndex(skinId) {
        for (var i = 0; i < root.idolCards.length; i++) {
            if (root.idolCards[i].skin_id === skinId) return i
        }
        return -1
    }

    // 获取指定 skin_id 的显示文本（与 ProducePage.idolDisplayText 一致）
    function _displayText(card) {
        if (!card) return ""
        return card.is_another && card.another_name
            ? card.name + " 「" + card.another_name + "」"
            : card.name
    }

    onIdolCardsChanged: {
        // 重置选中状态
        root.selectedSkinId = ""
        root.selectedDisplayName = ""
        root._currentCharacterId = ""
        root._searchText = ""
        _buildCharacters()
    }

    Component.onCompleted: {
        if (root.idolCards.length > 0) _buildCharacters()
    }

    // ── 确认/取消按钮（IAA 风格：standardButtons: NoButton，按钮放 contentItem 末尾） ──
    standardButtons: Dialog.NoButton

    function _selectedCardIsAnother(): bool {
        if (!root.selectedSkinId) return false
        for (var i = 0; i < root.idolCards.length; i++) {
            if (root.idolCards[i].skin_id === root.selectedSkinId)
                return root.idolCards[i].is_another
        }
        return false
    }

    signal idolSelected(string skinId)

    // ── アナザー警告弹窗 ──
    Dialog {
        id: anotherWarningDialog
        title: "提示"
        modal: true
        anchors.centerIn: Overlay.overlay
        width: 380
        standardButtons: Dialog.NoButton

        ColumnLayout {
            width: parent.width
            spacing: 12

            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: "你选择的偶像卡为「アナザー」版本，需要先在游戏内手动切换到对应的版本，否则脚本无法自动识别。是否继续？"
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button { text: "取消"; onClicked: anotherWarningDialog.close() }
                Button {
                    text: "确定"
                    highlighted: true
                    onClicked: {
                        root.idolSelected(root.selectedSkinId)
                        anotherWarningDialog.close()
                        root.close()
                    }
                }
            }
        }
    }

    // ── 内容布局 ──────────────────────────────────────
    contentItem: ColumnLayout {
        spacing: 8

        // 搜索框 + 图片版本切换
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            TextField {
                id: searchField
                Layout.fillWidth: true
                placeholderText: "搜索卡片名称或偶像名称..."
                onTextChanged: root._searchText = text
            }

            SegmentedButton {
                model: [
                    { text: "特训前", value: false },
                    { text: "特训后", value: true }
                ]
                value: root._showAfter
                onActivated: function(index, value) {
                    root._showAfter = value
                }
            }
        }

        // 主区域：左分类 + 右卡片网格
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 8

            // ── 左：分类列表 ──────────────────────────
            Pane {
                Layout.preferredWidth: 160
                Layout.fillHeight: true
                padding: 0

                ListView {
                    id: categoryList
                    anchors.fill: parent
                    clip: true
                    model: root._characters
                    spacing: 1

                    delegate: ItemDelegate {
                        width: categoryList.width
                        highlighted: modelData.character_id === root._currentCharacterId

                        contentItem: RowLayout {
                            spacing: 4
                            Label {
                                text: modelData.character_name
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                                font.bold: parent.parent.highlighted
                            }
                            Label {
                                text: "(" + modelData.count + ")"
                                color: palette.placeholderText
                                font.pixelSize: 11
                            }
                        }

                        onClicked: {
                            root._currentCharacterId = modelData.character_id
                            // 如果当前选中了卡片但不在这个分类，清除选中
                            if (root.selectedSkinId) {
                                var idx = root._findCardIndex(root.selectedSkinId)
                                if (idx >= 0 && root.idolCards[idx].character_id !== modelData.character_id) {
                                    root.selectedSkinId = ""
                                    root.selectedDisplayName = ""
                                }
                            }
                        }
                    }
                }
            }

            // ── 右：卡片网格 ──────────────────────────
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true

                GridView {
                    id: cardGrid
                    anchors.fill: parent
                    cellWidth: 155
                    cellHeight: 250
                    model: root._filteredCards
                    delegate: cardDelegate
                    boundsBehavior: Flickable.StopAtBounds
                }
            }
        }

        // 底部按钮
        RowLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignRight
            spacing: 8

            Button { text: "取消"; onClicked: root.close() }
            Button {
                text: "确定"
                highlighted: true
                enabled: !!root.selectedSkinId
                onClicked: {
                    if (_selectedCardIsAnother()) {
                        anotherWarningDialog.open()
                    } else {
                        root.idolSelected(root.selectedSkinId)
                        root.close()
                    }
                }
            }
        }
    }

    // ── 卡片网格项 ──────────────────────────────────
    Component {
        id: cardDelegate

        Rectangle {
            required property var modelData
            required property int index

            width: cardGrid.cellWidth - 10
            height: 220

            radius: 6
            color: root.selectedSkinId === modelData.skin_id
                ? Qt.rgba(palette.accent.r, palette.accent.g, palette.accent.b, 0.15)
                : "transparent"
            border.color: root.selectedSkinId === modelData.skin_id
                ? palette.accent
                : "transparent"
            border.width: 2

            // 悬停效果
            property bool _hovered: false

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 4
                spacing: 6

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: width * 1.2  // 卡片图片比例
                    Layout.alignment: Qt.AlignHCenter

                    Image {
                        anchors.fill: parent
                        source: root._showAfter
                            ? modelData.image_path.replace("_0.png", "_1.png")
                            : modelData.image_path
                        fillMode: Image.PreserveAspectFit
                        sourceSize.width: 120
                        sourceSize.height: 120
                        asynchronous: true
                        cache: true
                    }
                }

                Label {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignHCenter
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignTop
                    wrapMode: Text.Wrap
                    text: modelData.is_another && modelData.another_name
                        ? modelData.another_name
                        : modelData.name
                }
            }

            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                onEntered: parent._hovered = true
                onExited: parent._hovered = false
                onClicked: {
                    root.selectedSkinId = modelData.skin_id
                    var card = root.idolCards[root._findCardIndex(modelData.skin_id)]
                    root.selectedDisplayName = root._displayText(card)
                }
            }
        }
    }
}
