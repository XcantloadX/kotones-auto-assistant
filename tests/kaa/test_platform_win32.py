from euishell import win32 as platform_win32


def test_window_state_bridge_minimizes_while_preserving_maximized_state():
    class FakeWindow:
        def __init__(self):
            self.states = platform_win32.Qt.WindowState.WindowMaximized | platform_win32.Qt.WindowState.WindowActive
            self.calls = []

        def windowStates(self):
            return self.states

        def setWindowStates(self, states):
            self.calls.append(states)
            self.states = states

    window = FakeWindow()
    platform_win32.WindowStateBridge(window).minimize()

    assert window.calls == [platform_win32.Qt.WindowState.WindowMaximized | platform_win32.Qt.WindowState.WindowMinimized]
    assert window.states == platform_win32.Qt.WindowState.WindowMaximized | platform_win32.Qt.WindowState.WindowMinimized


def test_window_state_bridge_minimizes_normal_window_without_adding_maximized_state():
    class FakeWindow:
        def __init__(self):
            self.states = platform_win32.Qt.WindowState.WindowActive
            self.calls = []

        def windowStates(self):
            return self.states

        def setWindowStates(self, states):
            self.calls.append(states)
            self.states = states

    window = FakeWindow()
    platform_win32.WindowStateBridge(window).minimize()

    assert window.calls == [platform_win32.Qt.WindowState.WindowMinimized]
    assert window.states == platform_win32.Qt.WindowState.WindowMinimized
