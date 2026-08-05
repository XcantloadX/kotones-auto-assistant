import QtQuick
import QtQuick.Controls

// 严格对齐 hatsuboshi ProduceCardIcon / BlockIcon / CostIcon 布局百分比
Item {
    id: root

    property var card: ({})
    property var staticIcons: ({})
    property bool showTooltip: true
    property real cardSize: 96

    width: cardSize
    height: cardSize

    readonly property bool _hasBlock: (card.blockValue !== undefined && card.blockValue >= 0)
    readonly property bool _hasLesson: (card.lessonValue !== undefined && card.lessonValue > 0)
    readonly property int _upgrade: card.upgradeCount || 0
    readonly property var _effects: card.effectIcons || []

    // top-[3px] / bottom-[3px] 按卡面比例缩放（基准 96）
    readonly property real _edge3: Math.max(1, cardSize * 3 / 96)

    Rectangle {
        id: frame
        anchors.fill: parent
        radius: Math.max(4, cardSize * 8 / 96)   // rounded-lg ≈ 8px @96
        color: "#2a2a2a"
        border.color: "#71717a"
        border.width: Math.max(1, Math.round(cardSize * 2 / 96))
        clip: true

        // 1. artwork absolute object-fill
        Image {
            anchors.fill: parent
            source: root.card.assetPath ? "file:///" + root.card.assetPath : ""
            fillMode: Image.Stretch
            asynchronous: true
            cache: true
        }

        // 2. frame absolute object-fill
        Image {
            anchors.fill: parent
            source: root.card.framePath ? "file:///" + root.card.framePath : ""
            fillMode: Image.Stretch
            asynchronous: true
            cache: true
        }

        // 3. PlayEffects: absolute left-0 bottom-0 w-[29%] h-full
        //    内层 flex-col-reverse justify-start
        Item {
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            width: parent.width * 0.29
            height: parent.height

            Column {
                id: effectsCol
                anchors.left: parent.left
                anchors.bottom: parent.bottom
                width: parent.width
                spacing: {
                    // hatsuboshi: marginBottom = -mb% where
                    // mbPercentage = 4 * (30*n - 100) / (n - 0.2)
                    var n = root._effects.length
                    if (n <= 3)
                        return 0
                    var mb = 4.0 * (30.0 * n - 100.0) / (n - 0.2)
                    return -(width * mb / 100.0)
                }

                // displayEffects 已 reverse；flex-col-reverse 再倒一次
                // → 最终与 playEffects 过滤顺序一致、从下往上堆
                // 我们用 bottom 锚点 Column 正向排列 reverse 列表
                // = 列表最后一项在底部。hatsuboshi reverse+col-reverse = 原序从下到上
                // reverse 列表最后一项 = 原序第一项 → 在底部 ✓
                Repeater {
                    model: root._effects
                    ExamEffectIcon {
                        required property var modelData
                        width: effectsCol.width
                        height: width
                        iconPath: modelData.icon || ""
                        bgPath: modelData.bg || ""
                    }
                }
            }
        }

        // 4. Lesson: absolute left-0 top-0 h-1/4 opacity-70
        //    内层 flex-row justify-start h-full
        Item {
            visible: root._hasLesson
            anchors.left: parent.left
            anchors.top: parent.top
            height: parent.height * 0.25
            width: parent.width * 0.5
            opacity: 0.7

            Row {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                spacing: 0

                // CostNumberIcon className="h-full"（内容定宽）
                CostNumberIcon {
                    height: parent.height
                    value: root.card.lessonValue || 0
                    noMinus: true
                    invert: true
                    staticIcons: root.staticIcons
                }

                // multiplier: bg-black/70 rounded-3xl w-[18px] h-[80%]
                //   内嵌 CostNumberIcon h-[70%] withMultiplier
                Rectangle {
                    visible: (root.card.lessonMultiplier || 0) > 1
                    width: Math.max(10, root.cardSize * 18 / 96)
                    height: parent.height * 0.8
                    radius: height / 2
                    color: "#B3000000"
                    anchors.verticalCenter: parent.verticalCenter

                    CostNumberIcon {
                        anchors.centerIn: parent
                        height: parent.height * 0.7
                        value: root.card.lessonMultiplier || 0
                        noMinus: true
                        withMultiplier: true
                        staticIcons: root.staticIcons
                    }
                }
            }
        }

        // 5. Block: absolute right-0 top-0 w-1/3 h-1/3
        //    img: absolute top-0 object-contain （max-w-full → 宽=100%, 高=auto, 贴顶）
        //    number: absolute top-[3px] inset-x-0 h-[55%]
        Item {
            visible: root._hasBlock
            anchors.right: parent.right
            anchors.top: parent.top
            width: parent.width / 3
            height: parent.height / 3

            // max-width:100%; height:auto; top:0  → 宽度撑满，高度按比例，贴顶
            Image {
                id: blockImg
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                // 高度按源图比例：block 64x58
                height: width * 58 / 64
                source: root.staticIcons.block
                    ? "file:///" + root.staticIcons.block : ""
                fillMode: Image.PreserveAspectFit
                cache: true
                asynchronous: true
            }

            // inset-x-0 top-[3px] h-[55%]
            CostNumberIcon {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.topMargin: root._edge3
                height: parent.height * 0.55
                value: root.card.blockValue || 0
                noMinus: true
                staticIcons: root.staticIcons
            }
        }

        // 6. Cost: absolute right-0 bottom-0 w-1/3 h-1/3
        //    stamina img: absolute bottom-0 object-contain (宽100% 高auto 贴底)
        //    costType ExamEffectIcon: absolute -top-2 object-contain
        //    number: absolute bottom-[3px] inset-x-0 h-[55%]
        Item {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            width: parent.width / 3
            height: parent.height / 3

            // costType 图标: -top-2
            ExamEffectIcon {
                visible: !!(root.card.costTypeIcon)
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                anchors.topMargin: -root.cardSize * 2 / 96
                width: parent.width
                height: parent.width
                iconPath: root.card.costTypeIcon || ""
                bgPath: root.card.costTypeBg || ""
            }

            // stamina: bottom-0, max-w-full, height auto
            // stamina 图标 64x55 / 64x57
            Image {
                visible: !root.card.costTypeIcon
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: width * 55 / 64
                source: {
                    if (root.card.isRedStamina && root.staticIcons.staminaRed)
                        return "file:///" + root.staticIcons.staminaRed
                    if (root.staticIcons.stamina)
                        return "file:///" + root.staticIcons.stamina
                    return ""
                }
                fillMode: Image.PreserveAspectFit
                cache: true
                asynchronous: true
            }

            // inset-x-0 bottom-[3px] h-[55%]
            CostNumberIcon {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.bottomMargin: root._edge3
                height: parent.height * 0.55
                value: root.card.costTypeIcon
                    ? (root.card.costValue || 0)
                    : (root.card.costStamina || 0)
                noMinus: false
                staticIcons: root.staticIcons
            }
        }

        // 7. Plus: absolute -right-[2px] h-full w-[30%]
        //    flex flex-col justify-center
        Column {
            visible: root._upgrade > 0
            anchors.right: parent.right
            anchors.rightMargin: -root.cardSize * 2 / 96
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width * 0.30
            spacing: 0

            Repeater {
                model: root._upgrade
                Image {
                    width: parent.width
                    height: width
                    source: root.staticIcons.enhanced
                        ? "file:///" + root.staticIcons.enhanced : ""
                    fillMode: Image.PreserveAspectFit
                    cache: true
                }
            }
        }
    }

    HoverHandler {
        id: hover
        enabled: root.showTooltip
    }

    // 富文本 hover（对齐列表视图的 EffectDescription）
    ToolTip {
        id: richTip
        visible: root.showTooltip && hover.hovered
        delay: 280
        timeout: 0
        padding: 10

        contentItem: Column {
            spacing: 6
            width: Math.min(320, Math.max(180, descCol.implicitWidth))

            Text {
                width: parent.width
                text: (root.card && root.card.name) ? root.card.name : ""
                font.pixelSize: 13
                font.weight: Font.DemiBold
                color: palette.windowText
                wrapMode: Text.WordWrap
            }

            EffectDescription {
                id: descCol
                width: parent.width
                segments: (root.card && root.card.descriptionSegments)
                    ? root.card.descriptionSegments : []
                staticIcons: root.staticIcons
                fontSize: 12
                iconSize: 16
            }
        }
    }
}
