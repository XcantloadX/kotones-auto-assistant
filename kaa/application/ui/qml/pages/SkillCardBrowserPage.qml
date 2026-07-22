import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import ".." as App

// 技能卡图鉴：列表/网格 + 无限滚动（底层按页加载）
Page {
    id: root
    background: Rectangle { color: palette.window }

    property var browserCtrl: null

    property var _staticIcons: ({})
    property string _search: ""
    property var _raritySel: ({})
    property var _categorySel: ({})
    property var _planSel: ({})
    property var _gradeSel: ({})
    property string _viewMode: "list"  // "list" | "grid"
    property bool _loadMoreThrottled: false

    function _reloadIcons() {
        if (!browserCtrl) return
        try {
            root._staticIcons = JSON.parse(browserCtrl.staticIconsJson())
        } catch (e) {
            console.log("icons parse failed", e)
        }
    }

    function _pushFilter() {
        if (!browserCtrl || !browserCtrl.indexLoaded) return
        var r = Object.keys(root._raritySel).filter(function(k) { return root._raritySel[k] }).join(",")
        var c = Object.keys(root._categorySel).filter(function(k) { return root._categorySel[k] }).join(",")
        var p = Object.keys(root._planSel).filter(function(k) { return root._planSel[k] }).join(",")
        var g = Object.keys(root._gradeSel).filter(function(k) { return root._gradeSel[k] }).join(",")
        browserCtrl.applyFilter(r, c, p, root._search, g)
    }

    function _toggleMap(map, key) {
        var m = Object.assign({}, map)
        m[key] = !m[key]
        var any = false
        for (var k in m) if (m[k]) any = true
        if (!any) return ({})
        return m
    }

    function _setViewMode(mode) {
        if (root._viewMode === mode) return
        root._viewMode = mode
        // 视图切换不重拉数据，只换展示
    }

    function _tryLoadMore() {
        if (!browserCtrl) return
        if (!browserCtrl.hasMore || browserCtrl.loadingMore || root._loadMoreThrottled) return
        root._loadMoreThrottled = true
        browserCtrl.loadMore()
        loadMoreThrottle.restart()
    }

    Component.onCompleted: {
        if (browserCtrl) browserCtrl.ensureLoaded()
    }

    Connections {
        target: browserCtrl
        function onIndexReady() {
            root._reloadIcons()
        }
        function onStaticIconsChanged() { root._reloadIcons() }
        function onPageReset() {
            if (listView.visible) listView.positionViewAtBeginning()
            if (gridView.visible) gridView.positionViewAtBeginning()
        }
    }

    // 筛选防抖
    Timer {
        id: filterDebounce
        interval: 180
        onTriggered: root._pushFilter()
    }

    // 加载更多节流（防止 onContentYChanged 高频触发）
    Timer {
        id: loadMoreThrottle
        interval: 200
        onTriggered: root._loadMoreThrottled = false
    }

    header: ToolBar {
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 12

            Label {
                text: "技能卡图鉴"
                font.pixelSize: 16
                font.weight: Font.DemiBold
            }

            Item { Layout.fillWidth: true }

            Row {
                spacing: 2

                Button {
                    id: listViewBtn
                    flat: true
                    checkable: true
                    checked: root._viewMode === "list"
                    implicitWidth: 36
                    implicitHeight: 32
                    onClicked: root._setViewMode("list")
                    ToolTip.visible: hovered
                    ToolTip.text: "列表视图"
                    ToolTip.delay: 400
                    contentItem: FluentIcon {
                        anchors.centerIn: parent
                        glyph: App.FluentIcons.list_20_regular
                        font.pixelSize: 16
                        color: listViewBtn.checked ? palette.highlight : palette.windowText
                        opacity: listViewBtn.checked ? 1 : 0.7
                    }
                    background: Rectangle {
                        radius: 4
                        color: listViewBtn.checked
                            ? (App.AppTheme.isDark ? Qt.rgba(1,1,1,0.12) : Qt.rgba(0,0,0,0.08))
                            : (listViewBtn.hovered
                                ? (App.AppTheme.isDark ? Qt.rgba(1,1,1,0.06) : Qt.rgba(0,0,0,0.04))
                                : "transparent")
                    }
                }

                Button {
                    id: gridViewBtn
                    flat: true
                    checkable: true
                    checked: root._viewMode === "grid"
                    implicitWidth: 36
                    implicitHeight: 32
                    onClicked: root._setViewMode("grid")
                    ToolTip.visible: hovered
                    ToolTip.text: "网格视图"
                    ToolTip.delay: 400
                    contentItem: FluentIcon {
                        anchors.centerIn: parent
                        glyph: App.FluentIcons.grid_20_regular
                        font.pixelSize: 16
                        color: gridViewBtn.checked ? palette.highlight : palette.windowText
                        opacity: gridViewBtn.checked ? 1 : 0.7
                    }
                    background: Rectangle {
                        radius: 4
                        color: gridViewBtn.checked
                            ? (App.AppTheme.isDark ? Qt.rgba(1,1,1,0.12) : Qt.rgba(0,0,0,0.08))
                            : (gridViewBtn.hovered
                                ? (App.AppTheme.isDark ? Qt.rgba(1,1,1,0.06) : Qt.rgba(0,0,0,0.04))
                                : "transparent")
                    }
                }
            }

            Label {
                text: {
                    if (browserCtrl && browserCtrl.loading) return "索引加载中…"
                    var n = listView.count
                    var t = browserCtrl ? browserCtrl.totalCount : 0
                    return n + " / " + t
                }
                opacity: 0.7
                font.pixelSize: 13
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        // ── 左侧筛选 ─────────────────────────────────────
        ScrollView {
            Layout.preferredWidth: 220
            Layout.fillHeight: true
            clip: true

            ColumnLayout {
                width: 200
                spacing: 10

                Label { text: "搜索"; font.weight: Font.Medium; opacity: 0.7 }
                TextField {
                    Layout.fillWidth: true
                    placeholderText: "名称 / ID / 效果"
                    onTextChanged: {
                        root._search = text
                        filterDebounce.restart()
                    }
                }

                Label { text: "稀有度"; font.weight: Font.Medium; opacity: 0.7; Layout.topMargin: 8 }
                Flow {
                    Layout.fillWidth: true
                    spacing: 6
                    Repeater {
                        model: [
                            { k: "Legend", t: "LR" }, { k: "Ssr", t: "SSR" },
                            { k: "Sr", t: "SR" }, { k: "R", t: "R" }, { k: "N", t: "N" }
                        ]
                        delegate: Button {
                            required property var modelData
                            text: modelData.t
                            checkable: true
                            checked: !!root._raritySel[modelData.k]
                            flat: true
                            onClicked: {
                                root._raritySel = root._toggleMap(root._raritySel, modelData.k)
                                filterDebounce.restart()
                            }
                        }
                    }
                }

                Label { text: "类别"; font.weight: Font.Medium; opacity: 0.7; Layout.topMargin: 8 }
                Flow {
                    Layout.fillWidth: true
                    spacing: 6
                    Repeater {
                        model: [
                            { k: "ActiveSkill", t: "A" },
                            { k: "MentalSkill", t: "M" },
                            { k: "Trouble", t: "T" }
                        ]
                        delegate: Button {
                            required property var modelData
                            text: modelData.t
                            checkable: true
                            checked: !!root._categorySel[modelData.k]
                            flat: true
                            onClicked: {
                                root._categorySel = root._toggleMap(root._categorySel, modelData.k)
                                filterDebounce.restart()
                            }
                        }
                    }
                }

                Label { text: "计划"; font.weight: Font.Medium; opacity: 0.7; Layout.topMargin: 8 }
                Flow {
                    Layout.fillWidth: true
                    spacing: 6
                    Repeater {
                        model: [
                            { k: "Common", t: "共通" }, { k: "Plan1", t: "感性" },
                            { k: "Plan2", t: "逻辑" }, { k: "Plan3", t: "非凡" }
                        ]
                        delegate: Button {
                            required property var modelData
                            text: modelData.t
                            checkable: true
                            checked: !!root._planSel[modelData.k]
                            flat: true
                            onClicked: {
                                root._planSel = root._toggleMap(root._planSel, modelData.k)
                                filterDebounce.restart()
                            }
                        }
                    }
                }

                Label { text: "强化"; font.weight: Font.Medium; opacity: 0.7; Layout.topMargin: 8 }
                Flow {
                    Layout.fillWidth: true
                    spacing: 6
                    Repeater {
                        model: [
                            { k: "0", t: "未强化" }, { k: "1", t: "+1" },
                            { k: "2", t: "+2" }, { k: "3", t: "+3" }
                        ]
                        delegate: Button {
                            required property var modelData
                            text: modelData.t
                            checkable: true
                            checked: !!root._gradeSel[modelData.k]
                            flat: true
                            onClicked: {
                                root._gradeSel = root._toggleMap(root._gradeSel, modelData.k)
                                filterDebounce.restart()
                            }
                        }
                    }
                }

                Button {
                    Layout.topMargin: 12
                    Layout.fillWidth: true
                    text: "清除筛选"
                    onClicked: {
                        root._search = ""
                        root._raritySel = ({})
                        root._categorySel = ({})
                        root._planSel = ({})
                        root._gradeSel = ({})
                        filterDebounce.restart()
                    }
                }
            }
        }

        // ── 右侧内容 ─────────────────────────────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            // 索引加载
            BusyIndicator {
                anchors.centerIn: parent
                running: browserCtrl && browserCtrl.loading
                visible: running
                z: 10
            }

            // ── 列表 ListView（虚拟化 + 无限滚动） ───────
            ListView {
                id: listView
                anchors.fill: parent
                visible: root._viewMode === "list"
                clip: true
                spacing: 10
                model: browserCtrl
                reuseItems: true
                cacheBuffer: height * 3
                ScrollBar.vertical: ScrollBar {
                    policy: listView.contentHeight > listView.height
                            ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                }

                // 轻量占位 → 100ms 后异步载入重委托（SkillCardIcon + EffectDescription）
                delegate: Rectangle {
                    id: listDelegate
                    required property var modelData
                    required property int index
                    width: listView.width
                    height: listHeavyLoader.item
                        ? listHeavyLoader.item.implicitHeight + 16
                        : placeholderHeight
                    radius: 8
                    color: App.AppTheme.isDark ? Qt.rgba(1,1,1,0.035) : Qt.rgba(0,0,0,0.025)
                    border.color: App.AppTheme.isDark ? Qt.rgba(1,1,1,0.12) : Qt.rgba(0,0,0,0.1)
                    border.width: 1

                    readonly property real placeholderHeight: 64

                    // 异步载入重委托
                    Loader {
                        id: listHeavyLoader
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 8
                        asynchronous: true
                        sourceComponent: listHeavyContent
                    }

                    Component {
                        id: listHeavyContent
                        Column {
                            spacing: 8
                            width: listHeavyLoader.width

                            Row {
                                width: parent.width
                                spacing: 12

                                SkillCardIcon {
                                    cardSize: 68
                                    card: modelData
                                    staticIcons: root._staticIcons
                                    showTooltip: false
                                }

                                Column {
                                    width: parent.width - 68 - 12
                                    spacing: 2
                                    anchors.verticalCenter: parent.verticalCenter

                                    Label {
                                        width: parent.width
                                        text: modelData.name || ""
                                        font.pixelSize: 15
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: 2
                                    }
                                    Label {
                                        visible: (modelData.evaluationLabel || "") !== ""
                                        text: modelData.evaluationLabel || ""
                                        font.pixelSize: 12
                                        opacity: 0.7
                                    }
                                    Label {
                                        visible: (modelData.unlockLevel || 0) > 0
                                        text: "P-Lv. " + (modelData.unlockLevel || 0)
                                        font.pixelSize: 12
                                        opacity: 0.7
                                    }
                                }
                            }

                            EffectDescription {
                                width: parent.width
                                segments: modelData.descriptionSegments || []
                                staticIcons: root._staticIcons
                                fontSize: 12
                                iconSize: 16
                            }
                        }
                    }

                }

                footer: Item {
                    width: listView.width
                    height: 48
                    BusyIndicator {
                        anchors.centerIn: parent
                        running: browserCtrl && browserCtrl.loadingMore
                        visible: running
                        width: 28
                        height: 28
                    }
                    Label {
                        anchors.centerIn: parent
                        visible: browserCtrl && !browserCtrl.hasMore && listView.count > 0 && !(browserCtrl.loadingMore)
                        text: "已加载全部"
                        opacity: 0.45
                        font.pixelSize: 12
                    }
                }

                onContentYChanged: {
                    if (!visible) return
                    if (contentHeight <= 0) return
                    var remain = contentHeight - (contentY + height)
                    if (remain < 200)
                        root._tryLoadMore()
                }
            }

            // ── 网格 GridView ────────────────────────────
            GridView {
                id: gridView
                anchors.fill: parent
                visible: root._viewMode === "grid"
                clip: true
                cellWidth: 120
                cellHeight: 150
                model: browserCtrl
                reuseItems: true
                cacheBuffer: height * 3
                ScrollBar.vertical: ScrollBar {
                    policy: gridView.contentHeight > gridView.height
                            ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                }

                delegate: Item {
                    width: gridView.cellWidth
                    height: gridView.cellHeight
                    required property var modelData

                    Loader {
                        id: heavyLoader
                        anchors.fill: parent
                        // active: false
                        asynchronous: true
                        sourceComponent: gridHeavyContent
                    }

                    Component {
                        id: gridHeavyContent
                        Column {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.top: parent.top
                            anchors.topMargin: 4
                            spacing: 4
                            width: gridView.cellWidth - 8

                            SkillCardIcon {
                                anchors.horizontalCenter: parent.horizontalCenter
                                cardSize: 96
                                card: modelData
                                staticIcons: root._staticIcons
                                showTooltip: true
                            }

                            Label {
                                width: parent.width
                                text: modelData.name || ""
                                font.pixelSize: 11
                                horizontalAlignment: Text.AlignHCenter
                                elide: Text.ElideRight
                            }

                            Label {
                                width: parent.width
                                visible: (modelData.evaluationLabel || "") !== ""
                                text: modelData.evaluationLabel || ""
                                font.pixelSize: 10
                                opacity: 0.55
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }
                }

                onContentYChanged: {
                    if (!visible) return
                    if (contentHeight <= 0) return
                    var remain = contentHeight - (contentY + height)
                    if (remain < 200)
                        root._tryLoadMore()
                }
            }

            // 底部加载条（网格）
            BusyIndicator {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 8
                running: root._viewMode === "grid" && browserCtrl && browserCtrl.loadingMore
                visible: running
                width: 28
                height: 28
                z: 5
            }
        }
    }
}
