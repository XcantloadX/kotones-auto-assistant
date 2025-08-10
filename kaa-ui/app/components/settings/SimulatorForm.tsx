import { Button, ButtonGroup, Form } from "react-bootstrap";
import SectionTitle from "./SectionTitle";

type Props = {
  get: (path: string, def?: any) => any;
  set: (path: string) => (e: any) => void;
};

export default function SimulatorForm({ get, set }: Props) {
  const type = get('data.user_configs.0.backend.type','custom');
  const setType = (val: string) => () => set('data.user_configs.0.backend.type')({ target: { value: val } });

  return (
    <div className="vstack gap-3">
      <SectionTitle
        title="模拟器设置"
        subtitle="选择模拟器并配置截图方式与性能相关参数"
      />

      <div className="mb-2">
        <div className="mb-1">平台</div>
        <ButtonGroup>
          <Button size="sm" variant={type === 'mumu12' ? 'primary' : 'outline-primary'} onClick={setType('mumu12')}>MuMu 12</Button>
          <Button size="sm" variant={type === 'leidian' ? 'primary' : 'outline-primary'} onClick={setType('leidian')}>雷电</Button>
          <Button size="sm" variant={type === 'custom' ? 'primary' : 'outline-primary'} onClick={setType('custom')}>自定义</Button>
          <Button size="sm" variant={type === 'dmm' ? 'primary' : 'outline-primary'} onClick={setType('dmm')}>DMM</Button>
        </ButtonGroup>
      </div>

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

      {(type === 'mumu12' || type === 'leidian') && (
        <>
          <Form.Group className="mb-2">
            <Form.Label>实例 ID</Form.Label>
            <Form.Control value={get('data.user_configs.0.backend.instance_id','') ?? ''} onChange={set('data.user_configs.0.backend.instance_id')} />
          </Form.Group>
        </>
      )}

      {type === 'mumu12' && (
        <Form.Check className="mb-2" type="switch" label="MuMu12 后台保活" checked={!!get('data.user_configs.0.backend.mumu_background_mode', false)} onChange={set('data.user_configs.0.backend.mumu_background_mode')} />
      )}

      {type === 'custom' && (
        <>
          <Form.Check className="mb-2" type="switch" label="检查并启动模拟器" checked={!!get('data.user_configs.0.backend.check_emulator', false)} onChange={set('data.user_configs.0.backend.check_emulator')} />
          <Form.Group className="mb-2">
            <Form.Label>模拟器 exe 文件路径</Form.Label>
            <Form.Control value={get('data.user_configs.0.backend.emulator_path','') ?? ''} onChange={set('data.user_configs.0.backend.emulator_path')} />
          </Form.Group>
          <Form.Group className="mb-2">
            <Form.Label>ADB 模拟器名称</Form.Label>
            <Form.Control value={get('data.user_configs.0.backend.adb_emulator_name','') ?? ''} onChange={set('data.user_configs.0.backend.adb_emulator_name')} />
          </Form.Group>
          <Form.Group className="mb-2">
            <Form.Label>模拟器启动参数</Form.Label>
            <Form.Control value={get('data.user_configs.0.backend.emulator_args','') ?? ''} onChange={set('data.user_configs.0.backend.emulator_args')} />
          </Form.Group>
          <Form.Group className="mb-2">
            <Form.Label>ADB IP</Form.Label>
            <Form.Control value={get('data.user_configs.0.backend.adb_ip','') ?? ''} onChange={set('data.user_configs.0.backend.adb_ip')} />
          </Form.Group>
          <Form.Group className="mb-2">
            <Form.Label>ADB 端口</Form.Label>
            <Form.Control type="number" value={get('data.user_configs.0.backend.adb_port', 5555)} onChange={set('data.user_configs.0.backend.adb_port')} />
          </Form.Group>
        </>
      )}

      {type === 'dmm' && (
        <div className="text-secondary small">DMM 平台无需额外模拟器设置。</div>
      )}
    </div>
  );
} 