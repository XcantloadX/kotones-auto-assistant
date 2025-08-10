import { useEffect } from "react";
import { Button, Form, Nav, Tab } from "react-bootstrap";
import { useConfigStore } from "../stores/configStore";

export default function SettingsPage() {
  const { doc, loading, message, error, load, save, setAt, getAt } = useConfigStore();

  useEffect(() => { load(); }, [load]);

  const onReset = () => load();
  const onSave = () => save();

  // 便捷读取路径
  const get = (path: string, def?: any) => getAt(path, def);
  const set = (path: string) => (e: any) => setAt(path, e?.target?.type === 'checkbox' ? e.target.checked : e.target.value);

  return (
    <div className="vstack gap-3">
      <div className="alert bg-body-tertiary border d-flex align-items-center justify-content-between mb-0">
        <div className="text-secondary small"><i className="bi bi-info-circle me-1"></i>设置修改后需要保存才会生效</div>
        <div className="d-flex gap-2">
          <Button size="sm" variant="outline-secondary" onClick={onReset} disabled={loading}>
            <i className="bi bi-arrow-counterclockwise me-1"></i>重置更改
          </Button>
          <Button size="sm" onClick={onSave} disabled={loading}>
            <i className="bi bi-save me-1"></i>保存设置
          </Button>
        </div>
      </div>

      <Tab.Container defaultActiveKey="simulator">
        <Nav variant="tabs" className="mb-3">
          <Nav.Item><Nav.Link eventKey="simulator">模拟器</Nav.Link></Nav.Item>
          <Nav.Item><Nav.Link eventKey="shop">商店</Nav.Link></Nav.Item>
          <Nav.Item><Nav.Link eventKey="daily">日常</Nav.Link></Nav.Item>
          <Nav.Item><Nav.Link eventKey="game">游戏启停</Nav.Link></Nav.Item>
          <Nav.Item><Nav.Link eventKey="misc">杂项/调试</Nav.Link></Nav.Item>
        </Nav>
        <Tab.Content>
          <Tab.Pane eventKey="simulator">
            <div className="vstack gap-3">
              <div>
                <div className="fw-bold mb-2">模拟器设置</div>
                <Form.Group className="mb-2">
                  <Form.Label>平台</Form.Label>
                  <Form.Select value={get('data.user_configs.0.backend.type','custom')} onChange={set('data.user_configs.0.backend.type')}>
                    <option value="mumu12">MuMu 12</option>
                    <option value="leidian">雷电</option>
                    <option value="custom">自定义</option>
                    <option value="dmm">DMM</option>
                  </Form.Select>
                </Form.Group>
                <Form.Group className="mb-2">
                  <Form.Label>截图方法</Form.Label>
                  <Form.Select value={get('data.user_configs.0.backend.screenshot_impl','adb')} onChange={set('data.user_configs.0.backend.screenshot_impl')}>
                    <option value="adb">adb</option>
                    <option value="adb_raw">adb_raw</option>
                    <option value="uiautomator2">uiautomator2</option>
                    <option value="windows">windows</option>
                    <option value="remote_windows">remote_windows</option>
                    <option value="nemu_ipc">nemu_ipc</option>
                  </Form.Select>
                </Form.Group>
                <Form.Group className="mb-2">
                  <Form.Label>最小截图间隔（秒）</Form.Label>
                  <Form.Control type="number" step="0.1" value={get('data.user_configs.0.backend.target_screenshot_interval','') ?? ''} onChange={set('data.user_configs.0.backend.target_screenshot_interval')} />
                </Form.Group>
                <Form.Check className="mb-2" type="switch" label="检查并启动模拟器" checked={!!get('data.user_configs.0.backend.check_emulator', false)} onChange={set('data.user_configs.0.backend.check_emulator')} />
                <Form.Group className="mb-2">
                  <Form.Label>模拟器 exe 文件路径</Form.Label>
                  <Form.Control value={get('data.user_configs.0.backend.emulator_path','') ?? ''} onChange={set('data.user_configs.0.backend.emulator_path')} />
                </Form.Group>
                <Form.Group className="mb-2">
                  <Form.Label>ADB IP</Form.Label>
                  <Form.Control value={get('data.user_configs.0.backend.adb_ip','') ?? ''} onChange={set('data.user_configs.0.backend.adb_ip')} />
                </Form.Group>
                <Form.Group className="mb-2">
                  <Form.Label>ADB 端口</Form.Label>
                  <Form.Control type="number" value={get('data.user_configs.0.backend.adb_port', 5555)} onChange={set('data.user_configs.0.backend.adb_port')} />
                </Form.Group>
                <Form.Check className="mb-2" type="switch" label="MuMu12 后台保活" checked={!!get('data.user_configs.0.backend.mumu_background_mode', false)} onChange={set('data.user_configs.0.backend.mumu_background_mode')} />
              </div>
            </div>
          </Tab.Pane>

          <Tab.Pane eventKey="shop">
            <div className="vstack gap-3">
              <div className="fw-bold">商店</div>
              <Form.Check type="switch" label="启用商店购买" checked={!!get('data.user_configs.0.options.purchase.enabled', false)} onChange={set('data.user_configs.0.options.purchase.enabled')} />
            </div>
          </Tab.Pane>

          <Tab.Pane eventKey="daily">
            <div className="vstack gap-3">
              <div className="fw-bold">工作</div>
              <Form.Check type="switch" label="启用工作" checked={!!get('data.user_configs.0.options.assignment.enabled', false)} onChange={set('data.user_configs.0.options.assignment.enabled')} />
              <div className="fw-bold">竞赛</div>
              <Form.Check type="switch" label="启用竞赛" checked={!!get('data.user_configs.0.options.contest.enabled', false)} onChange={set('data.user_configs.0.options.contest.enabled')} />
              <div className="fw-bold">活动费/礼物/奖励</div>
              <Form.Check type="switch" label="活动费" checked={!!get('data.user_configs.0.options.activity_funds.enabled', false)} onChange={set('data.user_configs.0.options.activity_funds.enabled')} />
              <Form.Check type="switch" label="礼物" checked={!!get('data.user_configs.0.options.presents.enabled', false)} onChange={set('data.user_configs.0.options.presents.enabled')} />
              <Form.Check type="switch" label="任务奖励" checked={!!get('data.user_configs.0.options.mission_reward.enabled', false)} onChange={set('data.user_configs.0.options.mission_reward.enabled')} />
              <Form.Check type="switch" label="社团奖励" checked={!!get('data.user_configs.0.options.club_reward.enabled', false)} onChange={set('data.user_configs.0.options.club_reward.enabled')} />
              <div className="fw-bold">扭蛋/支援卡</div>
              <Form.Check type="switch" label="扭蛋" checked={!!get('data.user_configs.0.options.capsule_toys.enabled', false)} onChange={set('data.user_configs.0.options.capsule_toys.enabled')} />
              <Form.Check type="switch" label="支援卡升级" checked={!!get('data.user_configs.0.options.upgrade_support_card.enabled', false)} onChange={set('data.user_configs.0.options.upgrade_support_card.enabled')} />
            </div>
          </Tab.Pane>

          <Tab.Pane eventKey="game">
            <div className="vstack gap-3">
              <div className="fw-bold">关闭游戏设置</div>
              <Form.Check type="switch" label="退出 kaa" checked={!!get('data.user_configs.0.options.end_game.exit_kaa', false)} onChange={set('data.user_configs.0.options.end_game.exit_kaa')} />
              <Form.Check type="switch" label="关闭游戏" checked={!!get('data.user_configs.0.options.end_game.kill_game', false)} onChange={set('data.user_configs.0.options.end_game.kill_game')} />
              <Form.Check type="switch" label="关闭 DMM" checked={!!get('data.user_configs.0.options.end_game.kill_dmm', false)} onChange={set('data.user_configs.0.options.end_game.kill_dmm')} />
              <Form.Check type="switch" label="关闭模拟器" checked={!!get('data.user_configs.0.options.end_game.kill_emulator', false)} onChange={set('data.user_configs.0.options.end_game.kill_emulator')} />
              <Form.Check type="switch" label="恢复 Gakumas Localify" checked={!!get('data.user_configs.0.options.end_game.restore_gakumas_localify', false)} onChange={set('data.user_configs.0.options.end_game.restore_gakumas_localify')} />
            </div>
          </Tab.Pane>

          <Tab.Pane eventKey="misc">
            <div className="vstack gap-3">
              <div className="fw-bold">杂项</div>
              <Form.Check type="switch" label="允许局域网访问" checked={!!get('data.user_configs.0.options.misc.expose_lan', false)} onChange={set('data.user_configs.0.options.misc.expose_lan')} />
              <div className="fw-bold">调试</div>
              <Form.Check type="switch" label="保留截图数据" checked={!!get('data.user_configs.0.keep_screenshots', false)} onChange={set('data.user_configs.0.keep_screenshots')} />
              <Form.Check type="switch" label="跟踪推荐卡检测" checked={!!get('data.user_configs.0.options.trace.recommend_card_detection', false)} onChange={set('data.user_configs.0.options.trace.recommend_card_detection')} />
            </div>
          </Tab.Pane>
        </Tab.Content>
      </Tab.Container>

      {message && <div className="text-muted small">{message}</div>}
      {error && <div className="text-danger small">{error}</div>}
    </div>
  );
} 