import QtQuick
import ".." as App

// Fluent System Icons 字形渲染。glyph 传入 FluentIcons 单例中的命名常量。
Text {
    required property string glyph

    font.family: App.FluentIcons.family
    font.pixelSize: 16
    text: glyph
    color: App.AppTheme.fg
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
}