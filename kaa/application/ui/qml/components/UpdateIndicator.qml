import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".." as App

// 标题栏更新指示器：后台检查 / 下载 / 构建索引时显示「↑ 更新中」，
// 样式与「配置 / 偏好」按钮一致；hover 弹出当前更新详情弹层
// （状态文本 + 各文件下载进度 / 索引构建进度）。
Item {
    id: root

    // 后台更新进行中（检查阶段 / 下载阶段 / 索引构建阶段）
    readonly property bool _active:
        GameDataCtrl.updateStatus === "checking"
        || GameDataCtrl.updateStatus === "downloading"
        || GameDataCtrl.updateStatus === "building"

    visible: _active
    // TabStrip 的交互行是普通 Row，隐藏项仍会占宽，故非激活时宽度归零
    width: _active ? rowContent.implicitWidth + 16 : 0
    height: parent.height

    // 指示器、弹层背景、弹层内按钮 任一被 hover 时保持弹层开启
    readonly property bool _hovering:
        _hoverMouse.containsMouse
        || _popupMouse.containsMouse
        || skipButton.hovered

    on_HoveringChanged: {
        if (_hovering) {
            closeTimer.stop()
            openTimer.restart()
        } else {
            openTimer.stop()
            closeTimer.restart()
        }
    }

    // 更新结束时（状态离开 checking/downloading）立即收起弹层
    on_ActiveChanged: {
        if (!_active)
            tipPopup.close()
    }

    function _positionPopup() {
        if (!tipPopup.parent)
            return
        var p = root.mapToItem(tipPopup.parent, 0, root.height + 6)
        tipPopup.x = p.x
        tipPopup.y = p.y
    }

    // ── hover 延迟开/关弹层 ─────────────────────────────────
    Timer {
        id: openTimer
        interval: 220
        repeat: false
        onTriggered: {
            root._positionPopup()
            tipPopup.open()
        }
    }

    Timer {
        id: closeTimer
        interval: 140
        repeat: false
        onTriggered: tipPopup.close()
    }

    // ── hover 背景（与「配置 / 偏好」按钮一致） ──────────────
    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 4; anchors.bottomMargin: 4
        anchors.leftMargin: 2; anchors.rightMargin: 2
        radius: 5
        color: root._hovering ? App.AppTheme.hover : "transparent"
    }

    // ── 内容：↑ 更新中 ──────────────────────────────────────
    Row {
        id: rowContent
        anchors.centerIn: parent
        spacing: 4

        FluentIcon {
            anchors.verticalCenter: parent.verticalCenter
            glyph: App.FluentIcons.arrow_clockwise_20_regular
            font.pixelSize: 14
            // 强调色高亮，突出「更新进行中」
            color: palette.accent

            // 更新进行中：图标旋转形成 loading 动画
            NumberAnimation on rotation {
                from: 0
                to: 360
                duration: 1200
                running: root._active
                loops: Animation.Infinite
            }
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: "更新中"
            font.pixelSize: 13
            color: palette.accent
        }
    }

    MouseArea {
        id: _hoverMouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }

    // ── hover 弹出层：当前更新信息 ──────────────────────────
    Popup {
        id: tipPopup
        parent: Overlay.overlay
        modal: false
        focus: false
        closePolicy: Popup.NoAutoClose
        padding: 12
        width: 300

        background: Rectangle {
            color: App.AppTheme.isDark ? "#2d2d2d" : "#ffffff"
            radius: 8
            border.color: App.AppTheme.isDark ? Qt.rgba(1,1,1,0.12) : Qt.rgba(0,0,0,0.12)
            border.width: 1

            // 弹层背景 hover：鼠标移入弹层时保持开启，避免跨过间隙被误关。
            // 置于 background（contentItem 之下），普通内容项不拦截 hover，
            // 弹层内的按钮在最上层自行处理 hover/点击。
            MouseArea {
                anchors.fill: parent
                id: _popupMouse
                hoverEnabled: true
                acceptedButtons: Qt.NoButton
            }
        }

        contentItem: Item {
            // 内容用普通 Item 包裹：ColumnLayout 作为布局，避免作为 Popup 子项时
            // 被自动重挂到内容区与 anchors 冲突。弹层 hover 追踪放在 background
            //（见上），此处不再需要覆盖层。
            implicitWidth: 300
            implicitHeight: columnLayout.implicitHeight

            ColumnLayout {
                id: columnLayout
                anchors.fill: parent
                spacing: 8

                // 标题：游戏数据更新（版本）
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    FluentIcon {
                        glyph: App.FluentIcons.arrow_clockwise_20_regular
                        font.pixelSize: 14
                        color: palette.accent
                        Layout.alignment: Qt.AlignVCenter
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "游戏数据更新"
                        font.pixelSize: 13
                        font.weight: Font.Medium
                        color: App.AppTheme.fg
                        elide: Text.ElideRight
                        Layout.alignment: Qt.AlignVCenter
                    }
                }

                // 当前状态文本
                Text {
                    Layout.fillWidth: true
                    text: GameDataCtrl.progressMessage || (GameDataCtrl.updateStatus === "downloading"
                        ? "正在下载游戏资源更新…"
                        : (GameDataCtrl.updateStatus === "building"
                            ? "正在构建图像数据索引…"
                            : "正在检查游戏资源…"))
                    color: App.AppTheme.isDark ? Qt.rgba(1,1,1,0.7) : Qt.rgba(0,0,0,0.7)
                    wrapMode: Text.Wrap
                    font.pixelSize: 12
                    lineHeight: 1.3
                }

                // 分隔线
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: App.AppTheme.isDark ? Qt.rgba(1,1,1,0.1) : Qt.rgba(0,0,0,0.1)
                    visible: GameDataCtrl.updateStatus === "downloading"
                        && GameDataCtrl.downloadFiles.length > 0
                }

                // 文件下载进度列表（仅下载阶段展示）
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    visible: GameDataCtrl.updateStatus === "downloading"
                        && GameDataCtrl.downloadFiles.length > 0

                    Repeater {
                        model: GameDataCtrl.downloadFiles
                        delegate: ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            // 文件名 + 速度 · 大小 + 百分比 放一行
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.fileName
                                    elide: Text.ElideMiddle
                                    font.pixelSize: 12
                                    color: App.AppTheme.fg
                                }

                                Text {
                                    text: (modelData.speedText || "—") + " · " + (modelData.sizeText || "—")
                                    font.pixelSize: 11
                                    color: App.AppTheme.isDark ? Qt.rgba(1,1,1,0.5) : Qt.rgba(0,0,0,0.5)
                                }

                                Text {
                                    text: (modelData.percent || 0).toFixed(0) + "%"
                                    font.pixelSize: 12
                                    color: App.AppTheme.isDark ? Qt.rgba(1,1,1,0.7) : Qt.rgba(0,0,0,0.7)
                                }
                            }

                            // 进度条
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 4
                                radius: 2
                                color: App.AppTheme.isDark ? Qt.rgba(1,1,1,0.12) : Qt.rgba(0,0,0,0.12)

                                Rectangle {
                                    width: parent.width * ((modelData.percent || 0) / 100)
                                    height: parent.height
                                    radius: 2
                                    color: palette.accent
                                }
                            }
                        }
                    }
                }

                // 索引构建进度（构建阶段展示）
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    visible: GameDataCtrl.updateStatus === "building"

                    // 当前 builder 名称 + 百分比
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        Text {
                            Layout.fillWidth: true
                            text: GameDataCtrl.buildMessage || "构建图像数据索引…"
                            elide: Text.ElideMiddle
                            font.pixelSize: 12
                            color: App.AppTheme.fg
                        }

                        Text {
                            text: GameDataCtrl.buildPercent.toFixed(0) + "%"
                            font.pixelSize: 12
                            color: App.AppTheme.isDark ? Qt.rgba(1,1,1,0.7) : Qt.rgba(0,0,0,0.7)
                        }
                    }

                    // 进度条
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 4
                        radius: 2
                        color: App.AppTheme.isDark ? Qt.rgba(1,1,1,0.12) : Qt.rgba(0,0,0,0.12)

                        Rectangle {
                            width: parent.width * (GameDataCtrl.buildPercent / 100)
                            height: parent.height
                            radius: 2
                            color: palette.accent
                        }
                    }
                }

                // 跳过下载（仅下载阶段展示，替代已移除的底部横幅按钮）
                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 2
                    visible: GameDataCtrl.updateStatus === "downloading"

                    Item { Layout.fillWidth: true }

                    Button {
                        id: skipButton
                        text: "跳过下载"
                        onClicked: GameDataCtrl.skipDownload()
                    }
                }
            }
        }

        onOpened: root._positionPopup()
        onWidthChanged: root._positionPopup()
    }
}
