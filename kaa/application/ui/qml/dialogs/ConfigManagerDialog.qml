import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// 配置管理对话框：新建/重命名/删除配置。
Dialog {
    id: root
    modal: true
    title: "配置管理"
    width: 400
    padding: 16
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    anchors.centerIn: Overlay.overlay

    property var configNames: []
    required property var tabManager

    function reload() {
        root.configNames = JSON.parse(ProfileStore.profilesJson).profiles || []
    }

    Component.onCompleted: reload()

    Connections {
        target: ProfileStore
        function onProfilesChanged() { root.reload() }
    }

    contentItem: ColumnLayout {
        spacing: 12

        RowLayout {
            Layout.fillWidth: true

            TextField {
                id: newConfigName
                Layout.fillWidth: true
                placeholderText: "新配置名称"
            }

            Button {
                text: "新建"
                highlighted: true
                enabled: newConfigName.text.trim().length > 0
                onClicked: {
                    var name = newConfigName.text.trim()
                    if (name.length > 0) {
                        root.tabManager.createProfile(name)
                        newConfigName.text = ""
                    }
                }
            }
        }

        ListView {
            id: configList
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 200
            clip: true
            model: root.configNames

            ScrollBar.vertical: ScrollBar {
                policy: configList.contentHeight > configList.height
                        ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
            }

            delegate: RowLayout {
                width: ListView.view.width
                height: 40

                ItemDelegate {
                    Layout.fillWidth: true
                    height: parent.height
                    text: modelData.label
                }

                Button {
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    text: "✎"
                    font.pixelSize: 16
                    flat: true
                    onClicked: {
                        renameDialog.targetConfigName = modelData.value;
                        renameDialog.newName = modelData.label;
                        renameDialog.open();
                    }
                }

                Button {
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    text: "×"
                    font.pixelSize: 18
                    flat: true
                    enabled: root.configNames.length > 1
                    visible: root.configNames.length > 1
                    onClicked: {
                        deleteConfirmDialog.targetConfigName = modelData.value;
                        deleteConfirmDialog.open();
                    }
                }
            }
        }

        Button {
            Layout.alignment: Qt.AlignRight
            text: "关闭"
            onClicked: root.close()
        }
    }

    Dialog {
        id: renameDialog
        modal: true
        title: "重命名配置"
        width: 360
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: Overlay.overlay

        property string targetConfigName: ""
        property string newName: ""

        contentItem: ColumnLayout {
            spacing: 12
            Label { text: "请输入新名称:" }
            TextField {
                id: renameInput
                Layout.fillWidth: true
                text: renameDialog.newName
                onTextChanged: renameDialog.newName = text
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button { text: "取消"; onClicked: renameDialog.close() }
                Button {
                    text: "确定"
                    highlighted: true
                    enabled: renameDialog.newName.trim().length > 0
                    onClicked: {
                        var oldName = renameDialog.targetConfigName
                        var newName = renameDialog.newName.trim()
                        var isCurrent = root.tabManager.isTabOpen(oldName)
                        // 重命名逻辑通过配置服务处理
                        var runner = function() {
                            try {
                                // 如果当前已打开，先关闭 tab
                                if (isCurrent) {
                                    // 找到 index 并关闭
                                    var tabs = JSON.parse(TabManager.tabsJson())
                                    for (var i = 0; i < tabs.length; i++) {
                                        if (tabs[i].configName === oldName) {
                                            TabManager.closeTab(i)
                                            break
                                        }
                                    }
                                }
                                // 执行重命名
                                var module = Qt.createQmlObject("import QtQml; QtObject {}", root)
                                // 使用 Python 侧的配置管理器
                                // 通过 ProfileStore 后端桥接
                                // 简化处理：在 Python 层通过 renameProfile 方法
                                // 目前暂不支持 Python 重命名桥接，输出警告
                                console.warn("Rename not yet bridged to Python. Please use config files directly.")
                            } catch(e) {
                                console.error("Rename failed:", e)
                            }
                        }
                        runner()
                        renameDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: deleteConfirmDialog
        modal: true
        title: "确认删除"
        width: 360
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: Overlay.overlay

        property string targetConfigName: ""

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: "确定要删除配置 '" + deleteConfirmDialog.targetConfigName + "' 吗？此操作不可撤销。"
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button { text: "取消"; onClicked: deleteConfirmDialog.close() }
                Button {
                    text: "删除"
                    highlighted: true
                    onClicked: {
                        var name = deleteConfirmDialog.targetConfigName
                        // 如果该配置的 tab 正在运行，拒绝删除
                        if (!root.tabManager.closeTabForConfig(name)) {
                            deleteConfirmDialog.close()
                            return
                        }
                        try {
                            // 文件删除通过 Python 侧实现
                            console.warn("Delete not yet bridged to Python. Please use config files directly.")
                        } catch(e) {
                            console.error("Delete failed:", e)
                        }
                        deleteConfirmDialog.close()
                    }
                }
            }
        }
    }
}
