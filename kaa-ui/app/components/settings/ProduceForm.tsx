import { Form } from "react-bootstrap";
import type { ProduceSolution } from "../../services/api/produce";
import SectionTitle from "./SectionTitle";

type Props = {
  get: (path: string, def?: any) => any;
  set: (path: string) => (e: any) => void;
  solutions: ProduceSolution[];
};

export default function ProduceForm({ get, set, solutions }: Props) {
  const produceEnabled = !!get('data.user_configs.0.options.produce.enabled', false);

  return (
    <div className="vstack gap-3">
      <SectionTitle
        title="培育"
        subtitle="管理和配置培育方案"
        enabled={produceEnabled}
        showSwitch={true}
        onToggle={set('data.user_configs.0.options.produce.enabled')}
      />
      
      <div className="ms-3">
        <Form.Group className="mb-2">
          <Form.Label>当前使用的培育方案</Form.Label>
          <Form.Select value={get('data.user_configs.0.options.produce.selected_solution_id', '') ?? ''} onChange={set('data.user_configs.0.options.produce.selected_solution_id')}>
            <option value="">未选择</option>
            {solutions.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </Form.Select>
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label>培育次数</Form.Label>
          <Form.Control type="number" min={1} value={get('data.user_configs.0.options.produce.produce_count', 1)} onChange={set('data.user_configs.0.options.produce.produce_count')} />
        </Form.Group>
      </div>
    </div>
  );
} 