import QtQuick
import QtQuick.Controls
import EuiShell

Item {
    id: root

    width: 800
    height: 500

    property int actionCount: 0
    property var settingsCtrl
    property var dialog

    NavigationCoordinator {
        id: coordinator

        unsavedChangesDialog: root.dialog
        tabGuards: root.settingsCtrl ? [root.settingsCtrl] : []
    }

    Button {
        objectName: "guardedActionButton"
        text: "执行操作"

        onClicked: coordinator.requestGuardedAction(
            "切换页面",
            function() {
                root.actionCount++
            }
        )
    }

    Button {
        objectName: "saveContinueButton"
        text: "保存并继续"

        onClicked: {
            coordinator.saveAndContinuePendingAction()
            root.dialog.close()
        }
    }

    Button {
        objectName: "discardContinueButton"
        text: "丢弃并继续"

        onClicked: {
            coordinator.discardAndContinuePendingAction()
            root.dialog.close()
        }
    }
}
