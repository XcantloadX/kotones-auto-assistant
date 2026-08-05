import QtQuick

// 对应 hatsuboshi CostNumberIcon
// 外层由 className 控制尺寸（如 absolute inset-x-0 h-[55%]）
// 内部: flex flex-row justify-center items-center + 可选 invert
// 数字 img: object-contain h-full（高度撑满，宽度按比例）
Item {
    id: root

    property int value: 0
    property bool noMinus: false
    property bool withMultiplier: false
    property bool invert: false
    property var staticIcons: ({})

    // 高度由父级指定（h-[55%] 或 h-full）
    // 宽度：若父级用 anchors.left/right 拉满则填满；否则按内容（implicitWidth）
    implicitWidth: row.implicitWidth

    readonly property var _digits: {
        var s = Math.abs(root.value).toString()
        var arr = []
        for (var i = 0; i < s.length; i++)
            arr.push(s.charAt(i))
        return arr
    }

    Row {
        id: row
        // justify-center items-center
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        height: parent.height
        spacing: 0

        Image {
            visible: root.value !== 0 && !root.noMinus
            source: root.staticIcons.minus
                ? "file:///" + root.staticIcons.minus : ""
            height: row.height
            width: status === Image.Ready && sourceSize.height > 0
                ? sourceSize.width * height / sourceSize.height
                : height * (73 / 128)
            fillMode: Image.PreserveAspectFit
            mipmap: true
            cache: true
            asynchronous: false
        }

        Image {
            visible: root.withMultiplier
            source: root.staticIcons.multiplier
                ? "file:///" + root.staticIcons.multiplier : ""
            height: row.height
            width: status === Image.Ready && sourceSize.height > 0
                ? sourceSize.width * height / sourceSize.height
                : height * 0.6
            fillMode: Image.PreserveAspectFit
            mipmap: true
            cache: true
            asynchronous: false
        }

        Repeater {
            model: root._digits
            Image {
                required property string modelData
                // 数字位图约 95x128
                source: root.staticIcons["digit" + modelData]
                    ? "file:///" + root.staticIcons["digit" + modelData] : ""
                height: row.height
                width: status === Image.Ready && sourceSize.height > 0
                    ? sourceSize.width * height / sourceSize.height
                    : height * (95 / 128)
                fillMode: Image.PreserveAspectFit
                mipmap: true
                cache: true
                asynchronous: false
            }
        }
    }
}
