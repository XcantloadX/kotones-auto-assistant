import QtQuick.Controls
import QtQuick.Layouts

// GroupBox 预置 Layout.fillWidth + FormSection，子项直接声明在内部即可
GroupBox {
    id: root
    Layout.fillWidth: true
    property var binder: null
    default property alias content: _section.data

    FormSection { id: _section; binder: root.binder }
}
