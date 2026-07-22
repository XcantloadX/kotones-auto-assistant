import QtQuick

// 效果图标：背景色底图 + 前景图标（对应 hatsuboshi ExamEffectIcon）
Item {
    id: root

    property string iconPath: ""
    property string bgPath: ""

    implicitWidth: 24
    implicitHeight: 24

    Image {
        anchors.fill: parent
        source: root.bgPath ? "file:///" + root.bgPath : ""
        fillMode: Image.PreserveAspectFit
        mipmap: true
        asynchronous: true
        cache: true
    }

    Image {
        anchors.centerIn: parent
        width: parent.width * 0.77
        height: parent.height * 0.77
        source: root.iconPath ? "file:///" + root.iconPath : ""
        fillMode: Image.PreserveAspectFit
        mipmap: true
        asynchronous: true
        cache: true
    }
}
