// 复刻自 FluentWinUI3 ComboBox select 模式。
// 与原版的区别：accent 条仅在真正选中的 item（currentIndex）上显示，
// hover 其他 item 时只做背景色变化（复用 highlighted 背景图），无 accent 条。
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.impl
import QtQuick.Controls.FluentWinUI3
import QtQuick.Controls.FluentWinUI3.impl as Impl

ComboBox {
    id: control

    delegate: ItemDelegate {
        id: delegateItem
        required property var model
        required property int index

        readonly property bool isCurrentItem: index === control.currentIndex
        readonly property bool __isHighContrast: Application.styleHints.accessibility.contrastPreference === Qt.HighContrast

        // 状态映射：
        //   当前选中项 → highlighted / highlighted_hovered / highlighted_pressed
        //   hover 非选中项 → highlighted（同背景，无 accent 条）
        //   其余 → normal / pressed
        readonly property string __delegateState: {
            if (!delegateItem.enabled) return "disabled"
            if (isCurrentItem) {
                if (delegateItem.down) return "highlighted_pressed"
                if (delegateItem.hovered) return "highlighted_hovered"
                return "highlighted"
            }
            if (delegateItem.hovered) return "highlighted"
            if (delegateItem.down) return "pressed"
            return "normal"
        }
        readonly property var __delegateConfig: Config.controls.itemdelegate[__delegateState] || {}

        width: ListView.view.width
        text: model[control.textRole]
        highlighted: control.highlightedIndex === index
        hoverEnabled: control.hoverEnabled

        background: Item {
            implicitWidth: 160
            implicitHeight: 40

            Impl.StyleImage {
                id: bgImg
                visible: !delegateItem.__isHighContrast
                imageConfig: delegateItem.__delegateConfig.background
                width: parent.width - 8
                height: parent.height - 4
                x: 4
                y: 2
            }

            // accent 条：仅当前选中项可见
            Rectangle {
                visible: delegateItem.isCurrentItem && !delegateItem.__isHighContrast
                x: 4
                y: (parent.height - height) / 2
                width: 3
                height: delegateItem.isCurrentItem ? (delegateItem.down ? 10 : 16) : 0
                radius: 1.5
                color: delegateItem.palette.accent

                Behavior on height {
                    NumberAnimation { duration: 187; easing.type: Easing.OutCubic }
                }
            }

            // 高对比度模式下的纯色背景
            Rectangle {
                visible: delegateItem.__isHighContrast
                width: parent.width - 8
                height: parent.height - 4
                x: 4
                y: 2
                color: (delegateItem.isCurrentItem || delegateItem.hovered)
                       ? delegateItem.palette.accent
                       : delegateItem.palette.window
                radius: 4
            }
        }
    }
}
