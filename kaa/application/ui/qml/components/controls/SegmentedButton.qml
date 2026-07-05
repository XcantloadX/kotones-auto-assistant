pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.impl

Control {
    id: root

    property var model: []
    property int currentIndex: -1
    property string textRole: "text"
    property string valueRole: "value"

    // 外部通过 value 绑定选中项，SegmentedButton 负责将其映射到 currentIndex。
    // 避免直接绑定 currentIndex：onClicked 内部会对其做命令式赋值，会打断外部 binding。
    property var value: undefined
    onValueChanged: _syncIndex()
    onModelChanged: _syncIndex()

    function _syncIndex() {
        const idx = _findIndex(root.model, root.value)
        if (root.currentIndex !== idx)
            root.currentIndex = idx
    }

    function _findIndex(items, val) {
        if (!items || val === undefined) return -1
        for (let i = 0; i < items.length; i++) {
            const item = items[i]
            const v = (item && typeof item === 'object') ? item[root.valueRole] : item
            if (v === val) return i
        }
        return -1
    }

    readonly property var currentValue: {
        if (currentIndex >= 0 && currentIndex < root.model.length) {
            const item = root.model[currentIndex]
            if (item !== undefined) {
                return typeof item === 'object' ? item[root.valueRole] : item
            }
        }
        return null
    }

    signal activated(int index, var value)

    implicitWidth: row.implicitWidth + leftPadding + rightPadding
    implicitHeight: 36

    leftPadding: 3
    rightPadding: 3
    topPadding: 3
    bottomPadding: 3

    readonly property bool lightScheme: Application.styleHints.colorScheme === Qt.Light

    background: Rectangle {
        color: root.lightScheme ? Qt.rgba(0, 0, 0, 0.05) : Qt.rgba(1, 1, 1, 0.05)
        radius: 6
    }

    contentItem: Item {
        implicitWidth: row.implicitWidth
        implicitHeight: row.implicitHeight

        Rectangle {
            id: slider
            z: 0
            y: 0
            height: 30
            radius: 4
            color: root.lightScheme ? "white" : Qt.rgba(1, 1, 1, 0.08)
            border.width: 1
            border.color: Qt.tint(root.palette.accent, Qt.rgba(1, 1, 1, 0.7))

            property real targetX: 0
            property real targetWidth: 0

            x: targetX
            width: targetWidth
            visible: targetWidth > 0

            Behavior on targetX {
                enabled: slider.visible
                NumberAnimation { duration: 150; easing.type: Easing.OutCubic }
            }
            Behavior on targetWidth {
                enabled: slider.visible
                NumberAnimation { duration: 150; easing.type: Easing.OutCubic }
            }

            function updatePosition() {
                if (root.currentIndex < 0 || root.currentIndex >= repeater.count) return
                const item = repeater.itemAt(root.currentIndex)
                if (!item) return
                // 不读 item.x：Row 布局 pass 可能晚于 Qt.callLater，此时 x 仍为 0。
                // 改从各项 width 累加；width 由 label.implicitWidth 同步计算，不依赖布局 pass。
                let x = 0
                for (let i = 0; i < root.currentIndex; i++) {
                    const prev = repeater.itemAt(i)
                    if (prev) x += prev.width + row.spacing
                }
                slider.targetX = x
                slider.targetWidth = item.width
            }

            Connections {
                target: repeater
                function onCountChanged() {
                    Qt.callLater(slider.updatePosition)
                }
            }

            Connections {
                target: root
                function onCurrentIndexChanged() {
                    Qt.callLater(slider.updatePosition)
                }
            }

            Component.onCompleted: {
                Qt.callLater(updatePosition)
            }
        }

        Row {
            id: row
            spacing: 2

            Repeater {
                id: repeater
                model: root.model

                delegate: AbstractButton {
                    id: segmentItem

                    z: 1
                    required property int index
                    required property var modelData

                    property var itemValue: typeof modelData === 'object' ? modelData[root.valueRole] : modelData
                    property string itemText: typeof modelData === 'object' ? modelData[root.textRole] : modelData

                    implicitWidth: Math.max(60, label.implicitWidth + 20)
                    implicitHeight: 30

                    hoverEnabled: true
                    checked: root.currentIndex === index

                    background: Rectangle {
                        radius: 4
                        color: {
                            if (!segmentItem.enabled)
                                return "transparent"
                            if (segmentItem.down)
                                return root.lightScheme ? Qt.rgba(0, 0, 0, 0.04) : Qt.rgba(1, 1, 1, 0.04)
                            if (segmentItem.hovered && !segmentItem.checked)
                                return root.lightScheme ? Qt.rgba(0, 0, 0, 0.02) : Qt.rgba(1, 1, 1, 0.02)
                            return "transparent"
                        }
                    }

                    contentItem: Label {
                        id: label
                        text: segmentItem.itemText
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        color: segmentItem.checked ? root.palette.accent : root.palette.text
                        font.weight: segmentItem.checked ? Font.DemiBold : Font.Normal
                    }

                    onClicked: {
                        root.currentIndex = index
                        root.activated(index, segmentItem.itemValue)
                    }

                    Component.onCompleted: {
                        if (index === root.currentIndex) {
                            Qt.callLater(slider.updatePosition)
                        }
                    }
                }
            }
        }
    }
}
