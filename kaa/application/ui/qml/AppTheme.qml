pragma Singleton
import QtQuick

// 全局主题调色板单例。
// TitleBar 区域统一从本单例获取色值，不再在各组件内重复判断。
// 不使用 palette.windowText（Windows 10 浅色系统主题下值为 #000000，与 FluentWinUI3 暗色 palette 冲突）。
QtObject {
    readonly property bool isDark: Application.styleHints.colorScheme !== Qt.Light
    readonly property bool isSolid: AppThemeController.windowStyle === "solid"

    // 前景色（icon / 自定义 Text 颜色）
    readonly property color fg: isDark ? "#ffffff" : "#000000"

    // 悬停背景
    readonly property color hover:       isDark ? Qt.rgba(1,1,1,0.08) : Qt.rgba(0,0,0,0.08)
    readonly property color hoverStrong: isDark ? Qt.rgba(1,1,1,0.15) : Qt.rgba(0,0,0,0.15)

    // TitleBar 背景
    //   solid → 不透明 Fluent 规范色
    //   Mica / acrylic / blur → 5% 半透明叠加，由 DWM 合成背景色
    readonly property color titleBg: isSolid
        ? (isDark ? "#202020" : "#f3f3f3")
        : (isDark ? Qt.rgba(1,1,1,0.05) : Qt.rgba(0,0,0,0.05))

    // 活跃 Tab 卡片背景（比 titleBg 浅一级，形成 Chrome 风格层次感）
    //   solid → 不透明色（与 titleBg 形成明显对比）
    //   Mica / acrylic / blur → 半透明叠加层（比 titleBg 5% 更亮）
    readonly property color tabCardBg: isSolid
        ? (isDark ? "#2d2d2d" : "#ffffff")
        : (isDark ? Qt.rgba(1,1,1,0.10) : Qt.rgba(1,1,1,0.60))
}
