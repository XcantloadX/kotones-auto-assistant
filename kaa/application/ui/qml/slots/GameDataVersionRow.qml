import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import EuiShell

// 关于页附加内容：游戏数据版本行。
RowLayout {
    id: root

    Label {
        text: "游戏数据 " + (GameDataCtrl.currentVersion || "未安装")
        Layout.alignment: Qt.AlignHCenter
    }
}
