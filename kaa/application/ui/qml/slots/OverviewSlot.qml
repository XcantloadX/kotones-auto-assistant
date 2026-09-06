import QtQuick
import EuiShell
import "../dialogs"
import "../pages"

// 总览 slot 容器：持有配置管理 / 定时管理对话框并承载总览页。
Item {
    id: root

    ProfileManagerDialog {
        id: profileManagerDialog
        tabManager: TabManager
    }

    ScheduleManagerDialog {
        id: scheduleManagerDialog
    }

    OverviewPage {
        anchors.fill: parent
        configManagerDialog: profileManagerDialog
        scheduleManagerDialog: scheduleManagerDialog
    }
}
