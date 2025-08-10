import { Form } from "react-bootstrap";
import SectionTitle from "./SectionTitle";

type Props = {
  get: (path: string, def?: any) => any;
  set: (path: string) => (e: any) => void;
};

export default function DailyForm({ get, set }: Props) {
  const assignmentEnabled = !!get('data.user_configs.0.options.assignment.enabled', false);
  const contestEnabled = !!get('data.user_configs.0.options.contest.enabled', false);
  const clubRewardEnabled = !!get('data.user_configs.0.options.club_reward.enabled', false);
  const capsuleToysEnabled = !!get('data.user_configs.0.options.capsule_toys.enabled', false);
  const upgradeCardEnabled = !!get('data.user_configs.0.options.upgrade_support_card.enabled', false);

  return (
    <div className="vstack gap-3">
      <SectionTitle
        title="工作设置"
        enabled={assignmentEnabled}
        showSwitch={true}
        onToggle={set('data.user_configs.0.options.assignment.enabled')}
      />
      
      <div className="ms-3">
        <Form.Check className="mb-2" type="switch" label="启用重新分配 MiniLive" checked={!!get('data.user_configs.0.options.assignment.mini_live_reassign_enabled', false)} onChange={set('data.user_configs.0.options.assignment.mini_live_reassign_enabled')} />
        <Form.Group className="mb-2">
          <Form.Label>MiniLive 工作时长</Form.Label>
          <Form.Select value={get('data.user_configs.0.options.assignment.mini_live_duration', 4)} onChange={set('data.user_configs.0.options.assignment.mini_live_duration')}>
            <option value={4}>4</option>
            <option value={6}>6</option>
            <option value={12}>12</option>
          </Form.Select>
        </Form.Group>
        <Form.Check className="mb-2" type="switch" label="启用重新分配 OnlineLive" checked={!!get('data.user_configs.0.options.assignment.online_live_reassign_enabled', false)} onChange={set('data.user_configs.0.options.assignment.online_live_reassign_enabled')} />
        <Form.Group className="mb-2">
          <Form.Label>OnlineLive 工作时长</Form.Label>
          <Form.Select value={get('data.user_configs.0.options.assignment.online_live_duration', 4)} onChange={set('data.user_configs.0.options.assignment.online_live_duration')}>
            <option value={4}>4</option>
            <option value={6}>6</option>
            <option value={12}>12</option>
          </Form.Select>
        </Form.Group>
      </div>

      <SectionTitle
        title="竞赛设置"
        enabled={contestEnabled}
        showSwitch={true}
        onToggle={set('data.user_configs.0.options.contest.enabled')}
      />
      <div className="ms-3">
        <Form.Group className="mb-2">
          <Form.Label>选择第几位竞赛目标</Form.Label>
          <Form.Select value={get('data.user_configs.0.options.contest.select_which_contestant', 1)} onChange={set('data.user_configs.0.options.contest.select_which_contestant')}>
            <option value={1}>1</option>
            <option value={2}>2</option>
            <option value={3}>3</option>
          </Form.Select>
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label>竞赛队伍未编成时</Form.Label>
          <Form.Select value={get('data.user_configs.0.options.contest.when_no_set','remind')} onChange={set('data.user_configs.0.options.contest.when_no_set')}>
            <option value="remind">通知我并跳过竞赛</option>
            <option value="wait">提醒我并等待手动编成</option>
            <option value="auto_set">使用自动编成并提醒我</option>
            <option value="auto_set_silent">使用自动编成</option>
          </Form.Select>
        </Form.Group>
      </div>

      <SectionTitle
        title="活动费"
        enabled={!!get('data.user_configs.0.options.activity_funds.enabled', false)}
        showSwitch={true}
        onToggle={set('data.user_configs.0.options.activity_funds.enabled')}
      />

      <SectionTitle
        title="礼物"
        enabled={!!get('data.user_configs.0.options.presents.enabled', false)}
        showSwitch={true}
        onToggle={set('data.user_configs.0.options.presents.enabled')}
      />

      <SectionTitle
        title="任务奖励"
        enabled={!!get('data.user_configs.0.options.mission_reward.enabled', false)}
        showSwitch={true}
        onToggle={set('data.user_configs.0.options.mission_reward.enabled')}
      />

      <SectionTitle
        title="社团奖励"
        enabled={clubRewardEnabled}
        showSwitch={true}
        onToggle={set('data.user_configs.0.options.club_reward.enabled')}
      />
      <div className="ms-3">
        <Form.Group className="mb-2">
          <Form.Label>想获取的笔记（枚举值）</Form.Label>
          <Form.Control value={get('data.user_configs.0.options.club_reward.selected_note','') ?? ''} onChange={set('data.user_configs.0.options.club_reward.selected_note')} />
        </Form.Group>
      </div>

      <SectionTitle
        title="扭蛋"
        enabled={capsuleToysEnabled}
        showSwitch={true}
        onToggle={set('data.user_configs.0.options.capsule_toys.enabled')}
      />
      <div className="ms-3">
        <Form.Group className="mb-2">
          <Form.Label>好友扭蛋机次数</Form.Label>
          <Form.Control type="number" min={0} max={5} value={get('data.user_configs.0.options.capsule_toys.friend_capsule_toys_count', 0)} onChange={set('data.user_configs.0.options.capsule_toys.friend_capsule_toys_count')} />
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label>感性扭蛋机次数</Form.Label>
          <Form.Control type="number" min={0} max={5} value={get('data.user_configs.0.options.capsule_toys.sense_capsule_toys_count', 0)} onChange={set('data.user_configs.0.options.capsule_toys.sense_capsule_toys_count')} />
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label>逻辑扭蛋机次数</Form.Label>
          <Form.Control type="number" min={0} max={5} value={get('data.user_configs.0.options.capsule_toys.logic_capsule_toys_count', 0)} onChange={set('data.user_configs.0.options.capsule_toys.logic_capsule_toys_count')} />
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label>非凡扭蛋机次数</Form.Label>
          <Form.Control type="number" min={0} max={5} value={get('data.user_configs.0.options.capsule_toys.anomaly_capsule_toys_count', 0)} onChange={set('data.user_configs.0.options.capsule_toys.anomaly_capsule_toys_count')} />
        </Form.Group>
      </div>
      
      <SectionTitle
        title="支援卡升级"
        enabled={upgradeCardEnabled}
        showSwitch={true}
        onToggle={set('data.user_configs.0.options.upgrade_support_card.enabled')}
      />
    </div>
  );
} 