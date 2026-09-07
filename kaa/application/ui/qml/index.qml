import QtQuick
import EuiShell
import "components"
import "dialogs"
import "pages"
import "pages/preferences"
import "pages/sections"
import "slots"

EuiShellApp {
    overviewContent: OverviewSlot { }
    titleBarTrailing: UpdateIndicator { }
    windowDialogs: KaaDialogs { }

    controlNotices: ProduceEngineNotice { }
    controlRunExtras: EndActionRow { }
    controlFooter: ControlFooterExtras { }
    aboutExtra: GameDataVersionRow { }

    pages: [
        EuiPageSpec { title: "方案"; source: ProducePage { } },
        EuiPageSpec { title: "更新"; source: UpdatePage { } }
    ]
    fullscreenPages: [
        EuiFullscreenPageSpec { id: "skillCardBrowser"; source: SkillCardBrowserPage { } }
    ]

    settingsSections: [
        EuiSectionSpec { title: "基本"; source: EmulatorSection { } },
        EuiSectionSpec { title: "日常"; source: DailySection { } },
        EuiSectionSpec { title: "培育"; source: ProduceSection { } },
        EuiSectionSpec { title: "杂项"; source: MiscSection { } }
    ]
    preferenceSections: [
        EuiSectionSpec { title: "启动"; source: InterfaceExtraSection { } },
        EuiSectionSpec { title: "更新"; source: UpdateSection { } },
        EuiSectionSpec { title: "游戏资源"; source: GameDataSection { } },
        EuiSectionSpec { title: "通知"; source: NotifySection { } },
        EuiSectionSpec { title: "快捷键"; source: HotkeysSection { } },
        EuiSectionSpec { title: "数据收集"; source: TelemetrySection { } }
    ]

    aboutLinks: [
        EuiLink { label: "GitHub"; url: "https://github.com/XcantloadX/kotones-auto-assistant" },
        EuiLink { label: "Bilibili"; url: "https://space.bilibili.com/3546853903698457" },
        EuiLink { label: "教程文档"; url: "https://www.kdocs.cn/l/cetCY8mGKHLj" },
        EuiLink { label: "QQ 群"; url: "https://qm.qq.com/q/OI0C3rMmAs" }
    ]
}
