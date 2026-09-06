def test_qt_sigint_handler_quits_application(monkeypatch):
    """Ctrl+C must request a normal Qt shutdown instead of raising KeyboardInterrupt."""
    import euishell.app as shell_app

    class FakeApp:
        def __init__(self):
            self.quit_called = False

        def quit(self):
            self.quit_called = True

    app = FakeApp()
    monkeypatch.setattr(shell_app.sys, "platform", "win32")
    registered = {}
    monkeypatch.setattr(
        shell_app.signal,
        "signal",
        lambda sig, handler: registered.setdefault(sig, handler),
    )

    shell_app._install_sigint_handler(app)
    registered[shell_app.signal.SIGINT](shell_app.signal.SIGINT, None)

    assert app.quit_called is True


def test_qt_sigint_handler_is_not_installed_on_non_windows(monkeypatch):
    import euishell.app as shell_app

    class FakeApp:
        pass

    called = False

    def fake_signal(*_args):
        nonlocal called
        called = True

    monkeypatch.setattr(shell_app.sys, "platform", "linux")
    monkeypatch.setattr(shell_app.signal, "signal", fake_signal)

    shell_app._install_sigint_handler(FakeApp())

    assert called is False
