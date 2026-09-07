import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../components"

// 偏好页（全屏）：内置外观 section + 下游 preferenceSections。
PageContainer {
    id: root
    title: "偏好"

    property var prefsCtrl
    property bool dirty: false

    // 下游注册的偏好 section（由 EuiShellApp 透传；外观 section 内置并置首）
    property list<EuiSectionSpec> preferenceSections: []

    Component {
        id: appearanceSectionComponent
        AppearanceSection { }
    }

    readonly property var sections: {
        var list = [{ title: "外观", source: appearanceSectionComponent }]
        for (var i = 0; i < root.preferenceSections.length; i++)
            list.push(root.preferenceSections[i])
        return list
    }

    function save() {
        root.prefsCtrl.save()
    }

    function hasUnsavedChanges() {
        return root.prefsCtrl.isDirty()
    }

    function discardChanges() {
        root.prefsCtrl.discard()
    }

    function saveChanges() {
        root.prefsCtrl.save()
    }

    Connections {
        target: root.prefsCtrl
        function onDirtyChanged(d) { root.dirty = d }
        function onOperationSucceeded(msg) { Notice.show("success", msg) }
        function onOperationFailed(msg) { Notice.show("error", msg) }
    }

    titleRightContent: Rectangle {
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

    headerActions: Button {
        text: "保存"
        highlighted: true
        enabled: root.dirty
        onClicked: root.save()
    }

    ScrollView {
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 16

            Repeater {
                model: root.sections
                delegate: Loader {
                    required property var modelData
                    Layout.fillWidth: true
                    sourceComponent: modelData.source
                    onLoaded: {
                        // section 根元素按契约声明可选注入属性，挂载时回填
                        if (item && item.hasOwnProperty("prefsCtrl")) item.prefsCtrl = root.prefsCtrl
                    }
                }
            }
        }
    }
}
