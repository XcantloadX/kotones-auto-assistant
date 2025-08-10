import React, { useEffect, useState } from "react";
import { Container, Nav, Navbar, Offcanvas } from "react-bootstrap";
import { Link, NavLink } from "react-router";

export default function AppShell({ children }: { children?: React.ReactNode }) {
  const [showDrawer, setShowDrawer] = useState(false);
  const [dark, setDark] = useState<boolean>(false);

  // 客户端初始化主题（避免 SSR 访问 window/localStorage）
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const stored = window.localStorage?.getItem("theme");
      const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
      const initial = stored === "dark" ? true : stored === "light" ? false : prefersDark;
      setDark(initial);
    } catch {}
  }, []);

  useEffect(() => {
    if (typeof document === "undefined") return;
    try {
      document.documentElement.setAttribute("data-bs-theme", dark ? "dark" : "light");
      window.localStorage?.setItem("theme", dark ? "dark" : "light");
    } catch {}
  }, [dark]);

  return (
    <div className="kaa-layout">
      <Navbar bg="body-tertiary" expand="lg" className="border-bottom sticky-top">
        <Container fluid>
          <button className="btn d-lg-none me-2" onClick={() => setShowDrawer(true)}>
            <i className="bi bi-list fs-4" />
          </button>
          <Navbar.Brand as={Link} to="/">
            <i className="bi bi-music-note-beamed me-2" />
            <span className="fw-bold text-warning">琴音小助手</span>
          </Navbar.Brand>
          <div className="ms-auto d-flex align-items-center gap-2">
            <div className="form-check form-switch m-0" title="深色模式">
              <input
                className="form-check-input"
                type="checkbox"
                role="switch"
                id="themeSwitch"
                checked={dark}
                onChange={(e) => setDark(e.target.checked)}
              />
              <label className="form-check-label ms-2" htmlFor="themeSwitch">
                <i className="bi bi-moon-stars" />
              </label>
            </div>
          </div>
        </Container>
      </Navbar>

      <div className="kaa-layout-wrapper">
        <aside className="d-none d-lg-flex kaa-layout-sidebar bg-body-tertiary p-3 border-end">
          <SidebarNav />
        </aside>
        <main className="kaa-layout-content">
          <Container fluid className="py-3">{children}</Container>
        </main>
      </div>

      <Offcanvas show={showDrawer} onHide={() => setShowDrawer(false)} placement="start">
        <Offcanvas.Header closeButton>
          <Offcanvas.Title>
            <i className="bi bi-list me-2" />导航
          </Offcanvas.Title>
        </Offcanvas.Header>
        <Offcanvas.Body>
          <SidebarNav onNavigate={() => setShowDrawer(false)} />
        </Offcanvas.Body>
      </Offcanvas>
    </div>
  );
}

function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="w-100">
      <div className="text-uppercase small fw-bold text-secondary mb-2">主导航</div>
      <Nav className="flex-column gap-1" variant="pills">
        <Nav.Item>
          <Nav.Link as={NavLink} to="/" end onClick={onNavigate}>
            <i className="bi bi-speedometer2 me-2" />状态
          </Nav.Link>
        </Nav.Item>
        <Nav.Item>
          <Nav.Link as={NavLink} to="/tasks" onClick={onNavigate}>
            <i className="bi bi-clipboard-check me-2" />任务
          </Nav.Link>
        </Nav.Item>
        <Nav.Item>
          <Nav.Link as={NavLink} to="/settings" onClick={onNavigate}>
            <i className="bi bi-gear me-2" />设置
          </Nav.Link>
        </Nav.Item>
        <Nav.Item>
          <Nav.Link as={NavLink} to="/produce" onClick={onNavigate}>
            <i className="bi bi-diagram-3 me-2" />培育
          </Nav.Link>
        </Nav.Item>
        <Nav.Item>
          <Nav.Link as={NavLink} to="/feedback" onClick={onNavigate}>
            <i className="bi bi-chat-dots me-2" />反馈
          </Nav.Link>
        </Nav.Item>
        <Nav.Item>
          <Nav.Link as={NavLink} to="/update" onClick={onNavigate}>
            <i className="bi bi-newspaper me-2" />更新
          </Nav.Link>
        </Nav.Item>
        <Nav.Item>
          <Nav.Link as={NavLink} to="/screen" onClick={onNavigate}>
            <i className="bi bi-display me-2" />画面
          </Nav.Link>
        </Nav.Item>
      </Nav>
      <div className="text-uppercase small fw-bold text-secondary mt-3 mb-2">快速入口</div>
      <div className="d-grid gap-2">
        <NavLink to="/" className="btn btn-primary btn-sm" onClick={onNavigate}>
          <i className="bi bi-play-fill me-1" />启动全部
        </NavLink>
        <NavLink to="/" className="btn btn-outline-primary btn-sm" onClick={onNavigate}>
          <i className="bi bi-pause-fill me-1" />暂停
        </NavLink>
      </div>
    </nav>
  );
} 