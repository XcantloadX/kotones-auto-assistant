import { useQuery } from '@tanstack/react-query';
import useOptimisticMutation from './useOptimisticMutation';
import { getTaskOverview, postTaskAction } from '../api/client';
import type { TaskOverviewDto } from '../types/api';

export function useTaskOverview() {
  const query = useQuery<TaskOverviewDto, Error>({
    queryKey: ['taskOverview'],
    queryFn: getTaskOverview,
    refetchInterval: 3000,
  });

  const runAll = useOptimisticMutation<TaskOverviewDto, void>(['taskOverview'], async () =>
    postTaskAction({ action: 'run_all' })
  );

  const stopAll = useOptimisticMutation<TaskOverviewDto, void>(['taskOverview'], async () =>
    postTaskAction({ action: 'stop' })
  );

  const runSingle = useOptimisticMutation<TaskOverviewDto, string>(
    ['taskOverview'],
    async (taskName: string) => postTaskAction({ action: 'run_single', task_name: taskName })
  );

  const pauseToggle = useOptimisticMutation<TaskOverviewDto, void>(['taskOverview'], async () =>
    postTaskAction({ action: 'pause_toggle' })
  );

  return { ...query, runAll, stopAll, runSingle, pauseToggle };
}

export default useTaskOverview;
