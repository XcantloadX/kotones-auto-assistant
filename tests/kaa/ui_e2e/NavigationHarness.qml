import QtQuick
import QtQuick.Controls
import "../../../kaa/application/ui/qml/components"

Item {
    id: root

    width: 800
    height: 500

    property int actionCount: 0
    property var settingsCtrl
    property var produceCtrl
    property var prefsCtrl
    property var dialog

    NavigationCoordinator {
        id: coordinator

        unsavedChangesDialog: root.dialog
        settingsCtrl: root.settingsCtrl
        produceCtrl: root.produceCtrl
        prefsCtrl: root.prefsCtrl
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
