import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Control {
    id: root
    background: null
    property string title: "NewPage"
    property bool showTitle: true
    default property alias contentData: contentArea.data
    /** 紧挨着标题文本右侧的内容 */
    property alias titleRightContent: titleRightArea.data
    /** 标题栏最右侧的操作按钮 */
    property alias headerActions: headerActionsArea.data

    padding: 20

    onVisibleChanged: {
        if (visible) {
            contentArea._entranceProgress = 0
            entranceAnim.restart()
        } else {
            entranceAnim.stop()
            contentArea._entranceProgress = 0
        }
    }

    // Handle the initially-visible page (currentIndex: 0) which never gets onVisibleChanged
    Timer {
        interval: 0
        repeat: false
        running: true
        onTriggered: {
            if (root.visible) {
                contentArea._entranceProgress = 0
                entranceAnim.restart()
            }
        }
    }

    NumberAnimation {
        id: entranceAnim
        target: contentArea
        property: "_entranceProgress"
        from: 0; to: 1
        duration: 250
        easing.type: Easing.BezierSpline
        easing.bezierCurve: [0, 0, 0, 1, 1.0, 1.0]
    }

    contentItem: ColumnLayout {
        id: column
        spacing: 20

        RowLayout {
            visible: root.showTitle

            Label {
                text: root.title
                font.pixelSize: 30
            }

            Item {
                id: titleRightArea
                visible: children.length > 0
                implicitWidth: childrenRect.width
                implicitHeight: childrenRect.height
            }

            Item { Layout.fillWidth: true }

            Item {
                id: headerActionsArea
                visible: children.length > 0
                implicitWidth: childrenRect.width
                implicitHeight: childrenRect.height
            }
        }

        Item {
            id: contentArea
            Layout.fillWidth: true
            Layout.fillHeight: true

            // Entrance animation: opacity + slide-up, 250ms cubic-bezier(0,0,0,1)
            property real _entranceProgress: 0
            opacity: _entranceProgress
            transform: Translate { y: (1 - contentArea._entranceProgress) * 28 }
        }
    }
}
