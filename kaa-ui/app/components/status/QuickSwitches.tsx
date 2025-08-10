import React from "react";
import { Form } from "react-bootstrap";
import { useRunStore } from "../../stores/runStore";

export default function QuickSwitches() {
  const { quick, setQuick } = useRunStore();

  const items: { key: keyof typeof quick; label: string }[] = [
    { key: "purchase", label: "商店" },
    { key: "assignment", label: "工作" },
    { key: "contest", label: "竞赛" },
    { key: "produce", label: "培育" },
    { key: "mission_reward", label: "任务" },
    { key: "club_reward", label: "社团" },
    { key: "activity_funds", label: "活动费" },
    { key: "presents", label: "礼物" },
    { key: "capsule_toys", label: "扭蛋" },
    { key: "upgrade_support_card", label: "支援卡" },
  ];

  return (
    <div className="d-flex flex-wrap gap-3 mb-3">
      {items.map((it) => (
        <Form.Check
          key={String(it.key)}
          type="switch"
          id={`quick-${String(it.key)}`}
          label={it.label}
          checked={Boolean(quick?.[it.key])}
          onChange={(e) => setQuick({ [it.key]: e.target.checked } as any)}
        />
      ))}
    </div>
  );
} 