import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components" as Components
import ".." as App

Dialog {
    id: root
    modal: true
    title: "定时任务管理"
    width: 560
    padding: 16
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    anchors.centerIn: Overlay.overlay

    header: Item {
        width: parent.width
        height: 48

        Row {
            anchors.left: parent.left
            anchors.leftMargin: 16
            anchors.topMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            spacing: 12

            Label {
                anchors.verticalCenter: parent.verticalCenter
                text: "定时任务管理"
                font.pointSize: 16
                font.weight: Font.DemiBold
            }

            Button {
                anchors.verticalCenter: parent.verticalCenter
                flat: true
                contentItem: Row {
                    spacing: 6
                    Components.FluentIcon {
                        glyph: App.FluentIcons.add_16_regular
                        font.pixelSize: 16
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Label {
                        text: "新建"
                        font.pixelSize: 14
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
                implicitHeight: 32
                // leftPadding: 12
                // rightPadding: 12
                onClicked: {
                    editDialog.entryId = ""
                    editDialog.entryName = ""
                    editDialog.entryProfile = root.profiles.length > 0 ? root.profiles[0] : ""
                    editDialog.triggerType = "daily"
                    editDialog.triggerTime = ""
                    editDialog.triggerWeekdays = []
                    editDialog.open()
                }
            }
        }

        Button {
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            flat: true
            implicitWidth: 32
            implicitHeight: 32
            contentItem: Components.FluentIcon {
                glyph: App.FluentIcons.dismiss_16_regular
                font.pixelSize: 14
            }
            onClicked: root.close()
        }
    }

    property var entries: []
    property var profiles: []

    function reload() {
        entries = JSON.parse(ScheduleController.entriesJson())
        profiles = JSON.parse(ScheduleController.profilesJson())
    }

    Component.onCompleted: reload()

    Connections {
        target: ScheduleController
        function onEntriesChanged() { root.reload() }
    }

    contentItem: ColumnLayout {
        spacing: 12

        // ── 条目列表 ────────────────────────────────────────────
        ListView {
            id: entryList
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 280
            clip: true
            model: root.entries

            ScrollBar.vertical: ScrollBar {
                policy: entryList.contentHeight > entryList.height
                        ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
            }

            // 空状态
            Label {
                anchors.centerIn: parent
                visible: root.entries.length === 0
                text: "暂无定时任务"
                font.pixelSize: 14
                opacity: 0.5
            }

            delegate: Rectangle {
                width: ListView.view.width
                height: 56
                radius: 6
                color: itemHover.containsMouse
                    ? App.AppTheme.isDark ? Qt.rgba(1,1,1,0.06) : Qt.rgba(0,0,0,0.06)
                    : "transparent"

                HoverHandler { id: itemHover }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 12

                    // 启用开关
                    Switch {
                        checked: modelData.enabled
                        onToggled: ScheduleController.setEntryEnabled(modelData.id, checked)
                    }

                    // 信息区
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Label {
                            Layout.fillWidth: true
                            text: modelData.name || modelData.profileName
                            font.pixelSize: 14
                            font.weight: Font.Medium
                            elide: Text.ElideRight
                        }

                        Label {
                            Layout.fillWidth: true
                            text: modelData.triggerDesc + " 执行「" + modelData.profileName + "」"
                            font.pixelSize: 12
                            opacity: 0.6
                            elide: Text.ElideRight
                        }
                    }

                    // 编辑按钮
                    Button {
                        Layout.preferredWidth: 32
                        Layout.preferredHeight: 32
                        flat: true
                        contentItem: Components.FluentIcon {
                            glyph: App.FluentIcons.edit_16_regular
                            font.pixelSize: 15
                        }
                        onClicked: {
                            editDialog.entryId = modelData.id
                            editDialog.entryName = modelData.name
                            editDialog.entryProfile = modelData.profileName
                            editDialog.triggerType = modelData.triggerType
                            editDialog.triggerTime = modelData.triggerTime
                            editDialog.triggerWeekdays = modelData.triggerWeekdays.slice()
                            editDialog.open()
                        }
                    }

                    // 删除按钮
                    Button {
                        Layout.preferredWidth: 32
                        Layout.preferredHeight: 32
                        flat: true
                        contentItem: Components.FluentIcon {
                            glyph: App.FluentIcons.delete_16_regular
                            font.pixelSize: 15
                            color: App.AppTheme.error
                        }
                        onClicked: {
                            deleteConfirmDialog.entryId = modelData.id
                            deleteConfirmDialog.entryName = modelData.name || modelData.profileName
                            deleteConfirmDialog.open()
                        }
                    }
                }
            }
        }
    }

    // ── 新建/编辑子对话框 ──────────────────────────────────────
    Dialog {
        id: editDialog
        modal: true
        title: entryId === "" ? "新建定时任务" : "编辑定时任务"
        width: 400
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: Overlay.overlay

        property string entryId: ""
        property string entryName: ""
        property string entryProfile: ""
        property string triggerType: "daily"
        property string triggerTime: ""
        property var triggerWeekdays: []

        contentItem: ColumnLayout {
            spacing: 12

            // 名称
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Label {
                    Layout.preferredWidth: 100
                    text: "名称"
                    elide: Text.ElideRight
                }
                TextField {
                    Layout.fillWidth: true
                    text: editDialog.entryName
                    placeholderText: "可选，方便识别"
                    onTextChanged: editDialog.entryName = text
                }
            }

            // 目标配置
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Label {
                    Layout.preferredWidth: 100
                    text: "目标配置"
                    elide: Text.ElideRight
                }
                ComboBox {
                    id: profileCombo
                    Layout.fillWidth: true
                    model: root.profiles
                    currentIndex: {
                        var idx = root.profiles.indexOf(editDialog.entryProfile)
                        return idx >= 0 ? idx : 0
                    }
                    onCurrentIndexChanged: {
                        if (currentIndex >= 0 && currentIndex < root.profiles.length)
                            editDialog.entryProfile = root.profiles[currentIndex]
                    }
                }
            }

            // 触发类型
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Label {
                    Layout.preferredWidth: 100
                    text: "触发类型"
                    elide: Text.ElideRight
                }
                RowLayout {
                    spacing: 8
                    Button {
                        text: "每天"
                        highlighted: editDialog.triggerType === "daily"
                        onClicked: editDialog.triggerType = "daily"
                    }
                    Button {
                        text: "每周"
                        highlighted: editDialog.triggerType === "weekly"
                        onClicked: editDialog.triggerType = "weekly"
                    }
                }
            }

            // 星期选择（仅每周时显示）
            RowLayout {
                visible: editDialog.triggerType === "weekly"
                Layout.fillWidth: true
                spacing: 12
                Label {
                    Layout.preferredWidth: 100
                    text: "星期"
                    elide: Text.ElideRight
                }
                Flow {
                    Layout.fillWidth: true
                    spacing: 6
                    Repeater {
                        model: ["一", "二", "三", "四", "五", "六", "日"]
                        delegate: CheckDelegate {
                            required property int index
                            required property string modelData
                            text: "周" + modelData
                            checked: editDialog.triggerWeekdays.indexOf(index) >= 0
                            onToggled: {
                                if (checked) {
                                    if (editDialog.triggerWeekdays.indexOf(index) < 0) {
                                        var arr = editDialog.triggerWeekdays.slice()
                                        arr.push(index)
                                        arr.sort()
                                        editDialog.triggerWeekdays = arr
                                    }
                                } else {
                                    var arr2 = editDialog.triggerWeekdays.filter(function(d) { return d !== index })
                                    editDialog.triggerWeekdays = arr2
                                }
                            }
                        }
                    }
                }
            }

            // 时间
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Label {
                    Layout.preferredWidth: 100
                    text: "时间"
                    elide: Text.ElideRight
                }
                TextField {
                    Layout.fillWidth: true
                    text: editDialog.triggerTime
                    placeholderText: "04:00"
                    validator: RegularExpressionValidator { regularExpression: /^([01]\d|2[0-3]):[0-5]\d$/ }
                    onTextChanged: editDialog.triggerTime = text
                }
            }
        }

        footer: Rectangle {
            implicitHeight: 81
            color: palette.window
            Rectangle {
                width: parent.width; height: 1
                color: App.AppTheme.isDark ? "#15FFFFFF" : "#0F000000"
            }
            Row {
                anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: 24; spacing: 8
                Button {
                    text: "取消"
                    onClicked: editDialog.close()
                }
                Button {
                    text: "确定"
                    highlighted: true
                    enabled: editDialog.entryProfile.length > 0
                             && editDialog.triggerTime.length > 0
                             && /^([01]\d|2[0-3]):[0-5]\d$/.test(editDialog.triggerTime)
                    onClicked: {
                        var data = {
                            name: editDialog.entryName,
                            profileName: editDialog.entryProfile,
                            trigger: {
                                type: editDialog.triggerType,
                                time: editDialog.triggerTime,
                                weekdays: editDialog.triggerType === "weekly" ? editDialog.triggerWeekdays : []
                            }
                        }
                        if (editDialog.entryId === "") {
                            ScheduleController.addEntry(JSON.stringify(data))
                        } else {
                            ScheduleController.updateEntry(editDialog.entryId, JSON.stringify(data))
                        }
                        editDialog.close()
                    }
                }
            }
        }
    }

    // ── 删除确认对话框 ──────────────────────────────────────────
    Dialog {
        id: deleteConfirmDialog
        modal: true
        title: "确认删除"
        width: 360
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: Overlay.overlay

        property string entryId: ""
        property string entryName: ""

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: "确定要删除定时任务 '" + deleteConfirmDialog.entryName + "' 吗？"
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button { text: "取消"; onClicked: deleteConfirmDialog.close() }
                Button {
                    text: "删除"
                    highlighted: true
                    onClicked: {
                        ScheduleController.removeEntry(deleteConfirmDialog.entryId)
                        deleteConfirmDialog.close()
                    }
                }
            }
        }
    }
}
