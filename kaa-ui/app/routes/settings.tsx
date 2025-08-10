import { useEffect, useMemo, useState } from "react";
import { Button, Modal, Nav, Spinner, Toast, ToastContainer } from "react-bootstrap";
import { NavLink, useNavigate, useParams } from "react-router";
import { useConfigStore } from "../stores/configStore";
import * as produceApi from "../services/api/produce";
import SimulatorForm from "../components/settings/SimulatorForm";
import ShopForm from "../components/settings/ShopForm";
import DailyForm from "../components/settings/DailyForm";
import GameForm from "../components/settings/GameForm";
import MiscForm from "../components/settings/MiscForm";
import ProduceForm from "../components/settings/ProduceForm";

export default function SettingsPage() {
  const { doc, loading, message, error, load, save, setAt, getAt, dirty } = useConfigStore();
  const params = useParams<{ tab?: string }>();
  const navigate = useNavigate();

  const activeKey = useMemo(() => params.tab ?? "simulator", [params.tab]);

  useEffect(() => { load(); }, [load]);

  const [solutions, setSolutions] = useState<produceApi.ProduceSolution[]>([]);
  useEffect(() => {
    produceApi.listSolutions().then(setSolutions).catch(() => {});
  }, []);

  // 离开提示（路由）
  const [showLeave, setShowLeave] = useState(false);
  const [pendingHref, setPendingHref] = useState<string | null>(null);

  // Tab 链接不拦截；其它路由离开时拦截
  const guardNavigate = (href: string) => (e: React.MouseEvent) => {
    if (href.startsWith('/settings')) return; // Tab 内部切换不拦截
    if (dirty) {
      e.preventDefault();
      setPendingHref(href);
      setShowLeave(true);
    }
  };

  const confirmLeave = () => {
    const href = pendingHref;
    setShowLeave(false);
    setPendingHref(null);
    if (href) navigate(href);
  };

  const saveAndLeave = async () => {
    const href = pendingHref;
    await save();
    setShowLeave(false);
    setPendingHref(null);
    if (href) navigate(href);
  };

  // 捕获文档内所有 a 链接点击，拦截离开设置页的导航（放过 /settings 内部链接）
  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (!dirty) return;
      if (e.defaultPrevented) return;
      const isMainClick = e.button === 0 && !e.metaKey && !e.altKey && !e.ctrlKey && !e.shiftKey;
      if (!isMainClick) return;
      const target = e.target as Element | null;
      if (!target) return;
      const anchor = target.closest('a[href]') as HTMLAnchorElement | null;
      if (!anchor) return;
      if (anchor.target && anchor.target !== "") return;
      const url = new URL(anchor.href, window.location.href);
      const sameOrigin = url.origin === window.location.origin;
      if (!sameOrigin) return; // 外链不拦
      const href = url.pathname + url.search + url.hash;
      if (href.startsWith('/settings')) return; // 设置内 Tab 切换不拦
      e.preventDefault();
      setPendingHref(href);
      setShowLeave(true);
    };
    document.addEventListener('click', onDocClick, true);
    return () => document.removeEventListener('click', onDocClick, true);
  }, [dirty]);

  // 浏览器刷新/关闭提示
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (!dirty) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  // 便捷读取路径
  const get = (path: string, def?: any) => getAt(path, def);
  const set = (path: string) => (e: any) => setAt(path, e?.target?.type === 'checkbox' ? e.target.checked : e.target.value);

  const tabs = [
    { key: "simulator", label: "模拟器" },
    { key: "shop", label: "商店" },
    { key: "daily", label: "日常" },
    { key: "produce", label: "培育" },
    { key: "game", label: "游戏启停" },
    { key: "misc", label: "杂项/调试" },
  ] as const;

  // Toast：保存提示
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [showToast, setShowToast] = useState(false);
  useEffect(() => {
    if (message && !dirty) {
      setToastMsg(message);
      setShowToast(true);
    }
  }, [message, dirty]);

  return (
    <div className="vstack gap-3">
      {dirty && (
        <div className="alert bg-body-tertiary border d-flex align-items-center justify-content-between mb-0">
          <div className="text-secondary small"><i className="bi bi-info-circle me-1"></i>设置修改后需要保存才会生效</div>
          <div className="d-flex gap-2">
            <Button size="sm" variant="outline-secondary" onClick={() => load()} disabled={loading}>
              <i className="bi bi-arrow-counterclockwise me-1"></i>重置更改
            </Button>
            <Button size="sm" onClick={() => save()} disabled={loading}>
              <i className="bi bi-save me-1"></i>保存设置
            </Button>
          </div>
        </div>
      )}

      {/* 顶部 Tab，使用 URL 同步；不拦内部切换 */}
      <Nav variant="tabs" className="mb-3">
        {tabs.map((t) => (
          <Nav.Item key={t.key}>
            <Nav.Link
              as={NavLink as any}
              to={`/settings/${t.key}`}
              active={activeKey === t.key}
            >
              {t.label}
            </Nav.Link>
          </Nav.Item>
        ))}
      </Nav>

      {/* 配置未加载时避免空回显 */}
      {!doc ? (
        <div className="text-center text-secondary py-5"><Spinner animation="border" size="sm" className="me-2" />正在载入配置…</div>
      ) : (
        <>
          <div hidden={activeKey !== "simulator"}>
            <SimulatorForm get={get} set={set} />
          </div>
          <div hidden={activeKey !== "shop"}>
            <ShopForm get={get} set={set} />
          </div>
          <div hidden={activeKey !== "daily"}>
            <DailyForm get={get} set={set} />
          </div>
          <div hidden={activeKey !== "produce"}>
            <ProduceForm get={get} set={set} solutions={solutions} />
          </div>
          <div hidden={activeKey !== "game"}>
            <GameForm get={get} set={set} />
          </div>
          <div hidden={activeKey !== "misc"}>
            <MiscForm get={get} set={set} />
          </div>
        </>
      )}

      {error && <div className="text-danger small">{error}</div>}

      {/* 离开确认 Modal：取消、放弃更改、保存更改 */}
      <Modal show={showLeave} onHide={() => setShowLeave(false)} backdrop="static" centered>
        <Modal.Header closeButton>
          <Modal.Title>未保存的更改</Modal.Title>
        </Modal.Header>
        <Modal.Body>你有未保存的更改，确定要离开吗？</Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowLeave(false)} disabled={loading}>取消</Button>
          <Button variant="outline-danger" onClick={confirmLeave} disabled={loading}>放弃更改</Button>
          <Button variant="primary" onClick={saveAndLeave} disabled={loading}>保存更改</Button>
        </Modal.Footer>
      </Modal>

      {/* 保存结果 Toast */}
      <ToastContainer position="top-center" className="mb-3">
        <Toast bg="success" onClose={() => setShowToast(false)} show={showToast} delay={2000} autohide>
          <Toast.Body className="text-white">{toastMsg}</Toast.Body>
        </Toast>
      </ToastContainer>
    </div>
  );
} 