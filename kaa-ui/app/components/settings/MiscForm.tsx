import { Form } from "react-bootstrap";
import SectionTitle from "./SectionTitle";

type Props = {
  get: (path: string, def?: any) => any;
  set: (path: string) => (e: any) => void;
};

export default function MiscForm({ get, set }: Props) {
  return (
    <div className="vstack gap-3">
      <SectionTitle title="杂项设置" />
      <Form.Group className="mb-2">
        <Form.Label>检查更新时机</Form.Label>
        <Form.Select value={get('data.user_configs.0.options.misc.check_update', 'startup')} onChange={set('data.user_configs.0.options.misc.check_update')}>
          <option value="startup">启动时检查更新</option>
          <option value="never">从不检查更新</option>
        </Form.Select>
      </Form.Group>
      <Form.Check type="switch" label="自动安装更新" checked={!!get('data.user_configs.0.options.misc.auto_install_update', false)} onChange={set('data.user_configs.0.options.misc.auto_install_update')} />
      <Form.Check type="switch" label="允许局域网访问" checked={!!get('data.user_configs.0.options.misc.expose_to_lan', false)} onChange={set('data.user_configs.0.options.misc.expose_to_lan')} />

      <SectionTitle title="调试设置" />
      <div className="alert alert-danger py-2">仅供调试使用。正常运行时务必关闭下面所有的选项。</div>
      <Form.Check type="switch" label="保留截图数据" checked={!!get('data.user_configs.0.keep_screenshots', false)} onChange={set('data.user_configs.0.keep_screenshots')} />
      <Form.Check type="switch" label="跟踪推荐卡检测" checked={!!get('data.user_configs.0.options.trace.recommend_card_detection', false)} onChange={set('data.user_configs.0.options.trace.recommend_card_detection')} />
    </div>
  );
} 