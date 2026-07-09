import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".." as App

Dialog {
    id: root
    modal: true
    title: "授業数据库 (SchoolEvent Inspector)"
    width: Overlay.overlay ? Overlay.overlay.width - 40 : 880
    height: Overlay.overlay ? Overlay.overlay.height - 60 : 600
    standardButtons: Dialog.Close
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    anchors.centerIn: Overlay.overlay

    required property var debugInspectorCtrl

    property var _events: []
    property var _filteredEvents: []
    property var _selectedEvent: null
    property string _filterText: ""

    function _reload() {
        if (root.debugInspectorCtrl) {
            root._events = []
            root._filteredEvents = []
            root._selectedEvent = null
            root.debugInspectorCtrl.loadSchoolEventListAsync()
        }
    }

    onVisibleChanged: {
        if (visible) _reload()
    }

    Connections {
        target: root.debugInspectorCtrl
        function onSchoolEventListReady(jsonStr) {
            var data = JSON.parse(jsonStr)
            if (data.error) {
                Notice.show("error", data.error)
                return
            }
            root._events = data
            root._applyFilter()
            if (root._filteredEvents.length > 0) {
                eventList.currentIndex = 0
                root.debugInspectorCtrl.loadSchoolEventDetailAsync(root._filteredEvents[0].id)
            }
        }
        function onSchoolEventDetailReady(jsonStr) {
            var data = JSON.parse(jsonStr)
            if (data.error) {
                Notice.show("error", data.error)
                return
            }
            root._selectedEvent = data
        }
    }

    function _applyFilter() {
        var txt = root._filterText.trim().toLowerCase()
        if (!txt) {
            root._filteredEvents = root._events
        } else {
            root._filteredEvents = root._events.filter(function(ev) {
                return (ev.id && ev.id.toLowerCase().indexOf(txt) >= 0)
                    || (ev.character_name && ev.character_name.toLowerCase().indexOf(txt) >= 0)
                    || (ev.character_id && ev.character_id.toLowerCase().indexOf(txt) >= 0)
                    || (ev.story_title && ev.story_title.toLowerCase().indexOf(txt) >= 0)
            })
        }
    }

    contentItem: RowLayout {
        spacing: 0

        // ── 左侧：列表 ────────────────────────────────────────
        Rectangle {
            Layout.preferredWidth: 280
            Layout.fillHeight: true
            color: palette.window

            ColumnLayout {
                anchors.fill: parent
                spacing: 4
                anchors.margins: 8

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    TextField {
                        id: searchField
                        Layout.fillWidth: true
                        placeholderText: "检索 ID / 角色 / 剧情…"
                        onTextChanged: {
                            root._filterText = text
                            root._applyFilter()
                        }
                    }
                }

                Label {
                    text: "共 " + root._filteredEvents.length + " 个事件"
                    font.pixelSize: 11
                    color: palette.placeholderText
                }

                ListView {
                    id: eventList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: root._filteredEvents
                    currentIndex: root._filteredEvents.length > 0 ? 0 : -1

                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }

                    delegate: ItemDelegate {
                        width: ListView.view.width
                        height: 40

                        required property int index
                        required property var modelData

                        highlighted: ListView.isCurrentItem

                        onClicked: {
                            eventList.currentIndex = index
                            if (root.debugInspectorCtrl)
                                root.debugInspectorCtrl.loadSchoolEventDetailAsync(modelData.id)
                        }

                        contentItem: Column {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8

                            Label {
                                text: modelData.id
                                font.pixelSize: 12
                                font.bold: true
                                elide: Text.ElideRight
                                width: parent.width
                            }
                            Label {
                                text: {
                                    var parts = []
                                    if (modelData.character_name) parts.push(modelData.character_name)
                                    if (modelData.story_title) parts.push(modelData.story_title)
                                    return parts.join(" · ") || "(无角色)"
                                }
                                font.pixelSize: 10
                                elide: Text.ElideRight
                                width: parent.width
                                color: palette.placeholderText
                            }
                        }
                    }
                }
            }
        }

        // ── 分割线 ─────────────────────────────────────────────
        Rectangle {
            width: 1
            Layout.fillHeight: true
            color: palette.mid
        }

        // ── 右侧：详情 ────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: palette.window

            Flickable {
                id: detailFlickable
                anchors.fill: parent
                anchors.margins: 16
                clip: true
                contentWidth: parent.width
                contentHeight: detailContent.height + 16
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }

                Column {
                    id: detailContent
                    width: detailFlickable.width
                    height: implicitHeight
                    spacing: 12

                    // ── 无选中 ─────────────────────────────────
                    Label {
                        visible: root._selectedEvent === null
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        text: "请从左侧选择一个事件"
                        color: palette.placeholderText
                        topPadding: 40
                    }

                    // ── 选中详情 ─────────────────────────────────
                    Column {
                        visible: root._selectedEvent !== null
                        width: parent.width
                        spacing: 12

                        // 基本信息
                        Rectangle {
                            width: parent.width
                            height: childrenRect.height + 24
                            color: palette.alternateBase
                            radius: 4

                            Column {
                                x: 12
                                width: parent.width - 24
                                height: implicitHeight
                                spacing: 6
                                Label { text: "<b>ID:</b> " + (root._selectedEvent?.id || "") }
                                Label { text: "<b>剧情标题:</b> " + (root._selectedEvent?.story_title || "—") }
                                Label { text: "<b>角色:</b> " + (root._selectedEvent?.character_name || "—") + " (" + (root._selectedEvent?.character_id || "—") + ")" }
                            }
                        }

                        // 选项列表
                        Label { text: "<b>选项</b>"; font.pixelSize: 15; topPadding: 4 }

                        Repeater {
                            model: root._selectedEvent?.options || []

                            Rectangle {
                                width: parent.width
                                height: childrenRect.height + 24
                                color: palette.alternateBase
                                radius: 4

                                required property int index
                                required property var modelData

                                Column {
                                    x: 12
                                    width: parent.width - 24
                                    height: implicitHeight
                                    spacing: 6

                                    Label { text: "<b>[选项 " + (index + 1) + "]:</b> " + modelData.id; font.pixelSize: 13 }

                                    Label {
                                        text: modelData.name
                                            ? "名称: " + modelData.name
                                            : "名称: —"
                                        wrapMode: Text.Wrap
                                        width: parent.width
                                    }

                                    Label {
                                        text: "体力: " + modelData.stamina
                                    }

                                    Label {
                                        text: "制作P: " + modelData.produce_point
                                    }

                                    Label {
                                        text: "必成功: " + (modelData.is_always_successful ? "是" : "否")
                                    }

                                    Label {
                                        visible: !modelData.is_always_successful
                                        text: "成功概率: " + (modelData.success_probability != null ? (modelData.success_probability / 100) + "%" : "—")
                                    }

                                    Label {
                                        text: "跳转: " + (modelData.step_type && modelData.step_type !== "ProduceStepType_Unknown"
                                            ? modelData.step_type + " → " + (modelData.step_id || "—")
                                            : "—")
                                    }

                                    // 效果列表
                                    Label {
                                        visible: modelData.effects && modelData.effects.length > 0
                                        text: "效果:"
                                        font.bold: true
                                        topPadding: 6
                                    }

                                    Repeater {
                                        model: modelData.effects || []

                                        Rectangle {
                                            width: parent.width
                                            height: childrenRect.height + 12
                                            color: palette.base
                                            radius: 3

                                            Column {
                                                x: 8
                                                width: parent.width - 16
                                                height: implicitHeight
                                                spacing: 2

                                                Label {
                                                    text: "  " + modelData.display
                                                    wrapMode: Text.Wrap
                                                    width: parent.width
                                                    font.bold: true
                                                }
                                                Label {
                                                    text: "    ID: " + modelData.id
                                                }
                                                Label {
                                                    text: "    type: " + modelData.effect_type
                                                    wrapMode: Text.Wrap
                                                    width: parent.width
                                                    color: palette.placeholderText
                                                }
                                                Label {
                                                    text: "    value: [" + (modelData.effect_value_min ?? "—") + "~" + (modelData.effect_value_max ?? "—") + "]"
                                                    wrapMode: Text.Wrap
                                                    width: parent.width
                                                    color: palette.placeholderText
                                                }
                                                Label {
                                                    text: "    resource: " + (modelData.resource_type || "—")
                                                    wrapMode: Text.Wrap
                                                    width: parent.width
                                                    color: palette.placeholderText
                                                    visible: modelData.resource_type ? true : false
                                                }
                                            }
                                        }
                                    }

                                    // 成功/失败效果 ID
                                    Label {
                                        visible: modelData.success_effect_ids && modelData.success_effect_ids.length > 0
                                        text: "成功效果 ID: " + modelData.success_effect_ids.join(", ")
                                        color: "#2E7D32"
                                    }
                                    Label {
                                        visible: modelData.fail_effect_ids && modelData.fail_effect_ids.length > 0
                                        text: "失败效果 ID: " + modelData.fail_effect_ids.join(", ")
                                        color: "#C62828"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
