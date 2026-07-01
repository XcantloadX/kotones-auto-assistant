import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: root
    property alias labelText: label.text
    property string helpText: ""
    property string errorText: ""
    property alias control: controlLoader.sourceComponent
    readonly property bool hasLabel: labelText !== null && labelText !== undefined && labelText !== ""

    default property alias _contentChildren: controlContainer.data

    RowLayout {
        visible: root.hasLabel || root.helpText.length > 0
        Layout.preferredWidth: visible ? 120 : 0
        Layout.alignment: Qt.AlignVCenter
        spacing: 6

        Label {
            id: label
            Layout.alignment: Qt.AlignVCenter
        }

        HelpTip {
            visible: root.helpText.length > 0
            richText: root.helpText
            Layout.alignment: Qt.AlignVCenter
        }
    }

    ColumnLayout {
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignTop
        spacing: 4

        ColumnLayout {
            id: controlContainer
            Layout.fillWidth: true
            spacing: 0

            Loader {
                id: controlLoader
                Layout.fillWidth: true
            }
        }

        Label {
            visible: root.errorText !== ""
            text: root.errorText
            color: "#DC3545"
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }
    }
}
