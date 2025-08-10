import { Form } from "react-bootstrap";
import SectionTitle from "./SectionTitle";

type Props = {
  get: (path: string, def?: any) => any;
  set: (path: string) => (e: any) => void;
};

export default function GameForm({ get, set }: Props) {
  const startGameEnabled = !!get('data.user_configs.0.options.start_game.enabled', false);

  return (
    <div className="vstack gap-3">
      <SectionTitle
        title="启动游戏设置"
        enabled={startGameEnabled}
        showSwitch={true}
        onToggle={set('data.user_configs.0.options.start_game.enabled')}
      />
      
      <div className="ms-3">
        <Form.Check className="mb-2" type="switch" label="通过 Kuyo 启动游戏" checked={!!get('data.user_configs.0.options.start_game.start_through_kuyo', false)} onChange={set('data.user_configs.0.options.start_game.start_through_kuyo')} />
        <Form.Group className="mb-2">
          <Form.Label>游戏包名</Form.Label>
          <Form.Control value={get('data.user_configs.0.options.start_game.game_package_name','') ?? ''} onChange={set('data.user_configs.0.options.start_game.game_package_name')} />
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label>Kuyo 包名</Form.Label>
          <Form.Control value={get('data.user_configs.0.options.start_game.kuyo_package_name','') ?? ''} onChange={set('data.user_configs.0.options.start_game.kuyo_package_name')} />
        </Form.Group>
        <Form.Check className="mb-2" type="switch" label="禁用 Gakumas Localify 插件" checked={!!get('data.user_configs.0.options.start_game.disable_gakumas_localify', false)} onChange={set('data.user_configs.0.options.start_game.disable_gakumas_localify')} />
        <Form.Group className="mb-2">
          <Form.Label>DMM 版游戏路径</Form.Label>
          <Form.Control placeholder="例如：F:\\Games\\gakumas\\gakumas.exe" value={get('data.user_configs.0.options.start_game.dmm_game_path','') ?? ''} onChange={set('data.user_configs.0.options.start_game.dmm_game_path')} />
        </Form.Group>
      </div>

      <SectionTitle title="关闭游戏设置" />
      <Form.Check type="switch" label="退出 kaa" checked={!!get('data.user_configs.0.options.end_game.exit_kaa', false)} onChange={set('data.user_configs.0.options.end_game.exit_kaa')} />
      <Form.Check type="switch" label="关闭游戏" checked={!!get('data.user_configs.0.options.end_game.kill_game', false)} onChange={set('data.user_configs.0.options.end_game.kill_game')} />
      <Form.Check type="switch" label="关闭 DMM" checked={!!get('data.user_configs.0.options.end_game.kill_dmm', false)} onChange={set('data.user_configs.0.options.end_game.kill_dmm')} />
      <Form.Check type="switch" label="关闭模拟器" checked={!!get('data.user_configs.0.options.end_game.kill_emulator', false)} onChange={set('data.user_configs.0.options.end_game.kill_emulator')} />
      <Form.Check type="switch" label="关闭系统（关机）" checked={!!get('data.user_configs.0.options.end_game.shutdown', false)} onChange={set('data.user_configs.0.options.end_game.shutdown')} />
      <Form.Check type="switch" label="休眠系统" checked={!!get('data.user_configs.0.options.end_game.hibernate', false)} onChange={set('data.user_configs.0.options.end_game.hibernate')} />
      <Form.Check type="switch" label="恢复 Gakumas Localify" checked={!!get('data.user_configs.0.options.end_game.restore_gakumas_localify', false)} onChange={set('data.user_configs.0.options.end_game.restore_gakumas_localify')} />
    </div>
  );
} 