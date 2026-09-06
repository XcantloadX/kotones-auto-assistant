import QtQml

// 全屏覆盖页规格：经 NavigationCoordinator 进入，window.fullscreenMode 与 id 匹配。
QtObject {
    property string id
    // fullscreenMode 匹配用 id（必填）。

    property Component source
    // 页面组件，由框架在窗口级实例化。
}
