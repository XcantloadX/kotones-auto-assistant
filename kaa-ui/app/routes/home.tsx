import { useEffect } from "react";
import RunControls from "../components/status/RunControls";
import QuickSwitches from "../components/status/QuickSwitches";
import TaskTable from "../components/status/TaskTable";
import { useRunStore } from "../stores/runStore";
import { startSSE } from "../services/events";

export default function Home() {
  const { refresh } = useRunStore();

  useEffect(() => {
    refresh();
    const stop = startSSE({
      onEvent: async () => {
        await refresh();
      },
      vitalPolls: [refresh],
    });
    return () => stop();
  }, [refresh]);

  return (
    <div className="row g-3">
      <div className="col-12">
        <div className="card">
          <div className="card-body">
            <RunControls />
            <QuickSwitches />
            <div className="alert alert-info" role="alert">
              脚本报错或卡住？前往"反馈"快速导出报告！
            </div>
          </div>
        </div>
      </div>
      <div className="col-12">
        <div className="d-flex align-items-center justify-content-between mb-2">
          <h6 className="mb-0">任务状态</h6>
        </div>
        <TaskTable />
        <div className="small text-secondary mt-2">调试提示：保留截图数据（建议调试结束后关闭）。</div>
      </div>
    </div>
  );
}
