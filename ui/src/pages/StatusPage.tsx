/** @jsxImportSource @emotion/react */
import styled from '@emotion/styled';
import React, { useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/api';
import { useEvent } from '../api/client';
import { useAppStore } from '../store/appStore';
import { Button } from '../components/common/Button';
import { Checkbox } from '../components/common/Checkbox';
import { Select } from '../components/common/Select';
import { Card, Section, FormGroup } from '../components/common/Card';
import { Alert } from '../components/common/Alert';
import { PageContainer, PageTitle } from '../components/layout/Layout';
import type { TaskStatus } from '../api/types';

const ControlRow = styled.div`
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
`;

const QuickGrid = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3) var(--space-6);
`;

const TaskTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-base);
`;

const Th = styled.th`
  text-align: left;
  padding: var(--space-2) var(--space-3);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-light);
`;

const Td = styled.td`
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-light);
`;

const StatusBadge = styled.span<{ $status: string }>`
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  background: ${({ $status }) => {
    switch ($status) {
      case 'running': return 'rgba(48, 209, 88, 0.15)';
      case 'done': return 'rgba(0, 122, 255, 0.1)';
      case 'error': return 'rgba(255, 59, 48, 0.1)';
      default: return 'var(--bg-tertiary)';
    }
  }};
  color: ${({ $status }) => {
    switch ($status) {
      case 'running': return 'var(--color-green)';
      case 'done': return 'var(--color-accent)';
      case 'error': return 'var(--color-red)';
      default: return 'var(--text-secondary)';
    }
  }};
`;

const statusLabel = (s: string) => {
  switch (s) {
    case 'running': return '运行中';
    case 'done': return '已完成';
    case 'pending': return '等待中';
    case 'error': return '错误';
    default: return s;
  }
};

const endActionOptions = [
  { label: '完成后什么都不做', value: 'nothing' },
  { label: '完成后关机', value: 'shutdown' },
  { label: '完成后休眠', value: 'hibernate' },
];

const quickTaskFields = [
  { label: '商店', field: 'purchase.enabled' },
  { label: '工作', field: 'assignment.enabled' },
  { label: '竞赛', field: 'contest.enabled' },
  { label: '培育', field: 'produce.enabled' },
  { label: '任务', field: 'mission_reward.enabled' },
  { label: '社团', field: 'club_reward.enabled' },
  { label: '活动费', field: 'activity_funds.enabled' },
  { label: '礼物', field: 'presents.enabled' },
  { label: '扭蛋', field: 'capsule_toys.enabled' },
  { label: '支援卡', field: 'upgrade_support_card.enabled' },
] as const;

export const StatusPage: React.FC = () => {
  const qc = useQueryClient();
  const { taskStatuses, taskRuntime, setTaskStatuses, setTaskRuntime } = useAppStore();

  const { data: config } = useQuery({
    queryKey: ['config'],
    queryFn: api.config.get,
  });

  const { data: runStatus, refetch: refetchRunStatus } = useQuery({
    queryKey: ['runStatus'],
    queryFn: api.task.getRunStatus,
    refetchInterval: 1000,
  });

  const { data: pauseStatus } = useQuery({
    queryKey: ['pauseStatus'],
    queryFn: api.task.getPauseStatus,
    refetchInterval: 1000,
  });

  const { data: runtime } = useQuery({
    queryKey: ['taskRuntime'],
    queryFn: api.task.getRuntime,
    refetchInterval: 1000,
  });

  const { data: statuses } = useQuery({
    queryKey: ['taskStatuses'],
    queryFn: api.task.getStatuses,
    refetchInterval: 1000,
  });

  const { data: upgradeMsg } = useQuery({
    queryKey: ['upgradeMsg'],
    queryFn: api.app.getUpgradeMessage,
    staleTime: Infinity,
  });

  useEffect(() => {
    if (statuses) setTaskStatuses(statuses);
  }, [statuses, setTaskStatuses]);

  useEffect(() => {
    if (runtime) setTaskRuntime(runtime);
  }, [runtime, setTaskRuntime]);

  // Real-time events
  useEvent('task.statusChanged', useCallback(() => {
    qc.invalidateQueries({ queryKey: ['taskStatuses'] });
    qc.invalidateQueries({ queryKey: ['runStatus'] });
    qc.invalidateQueries({ queryKey: ['pauseStatus'] });
  }, [qc]));

  useEvent('task.stopped', useCallback(() => {
    qc.invalidateQueries({ queryKey: ['runStatus'] });
    qc.invalidateQueries({ queryKey: ['pauseStatus'] });
    qc.invalidateQueries({ queryKey: ['taskStatuses'] });
  }, [qc]));

  const runMutation = useMutation({
    mutationFn: async () => {
      if (runStatus?.text === '停止') {
        await api.task.stopAll();
      } else {
        await api.task.startAll();
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['runStatus'] });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: api.task.togglePause,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pauseStatus'] });
    },
  });

  const saveFieldMutation = useMutation({
    mutationFn: ({ path, value }: { path: string; value: unknown }) =>
      api.config.saveField(path, value),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config'] });
    },
  });

  const endActionMutation = useMutation({
    mutationFn: async (action: string) => {
      const opts = config?.options;
      if (!opts) return;
      await api.config.saveField('options.end_game.shutdown', action === 'shutdown');
      await api.config.saveField('options.end_game.hibernate', action === 'hibernate');
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config'] });
    },
  });

  const getEndAction = (): string => {
    const end = config?.options?.end_game;
    if (end?.shutdown) return 'shutdown';
    if (end?.hibernate) return 'hibernate';
    return 'nothing';
  };

  const getFieldValue = (field: string): boolean => {
    const opts = config?.options;
    if (!opts) return false;
    const parts = field.split('.');
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let obj: any = opts;
    for (const p of parts) {
      obj = obj?.[p];
    }
    return Boolean(obj);
  };

  const handleQuickBatch = (select: boolean, produceOnly?: boolean) => {
    const tasks: Array<typeof quickTaskFields[number]> = [...quickTaskFields];
    tasks.forEach(({ field }) => {
      const value = field === 'produce.enabled' ? (produceOnly !== undefined ? (produceOnly ? select : !select) : select) : select;
      saveFieldMutation.mutate({ path: `options.${field}`, value });
    });
  };

  const opts = config?.options;

  return (
    <PageContainer>
      <PageTitle>状态</PageTitle>

      {upgradeMsg && (
        <Alert variant="info">
          <strong>配置升级报告</strong>
          <br />
          {upgradeMsg}
        </Alert>
      )}

      <Card>
        <Section title="任务控制">
          <ControlRow>
            <Button
              variant={runStatus?.text === '停止' ? 'destructive' : 'primary'}
              size="lg"
              disabled={!runStatus?.interactive || runMutation.isPending}
              loading={runMutation.isPending}
              onClick={() => runMutation.mutate()}
              style={{ minWidth: 120 }}
            >
              {runStatus?.text ?? '启动'}
            </Button>
            <Button
              variant="secondary"
              size="lg"
              disabled={!pauseStatus?.interactive || pauseMutation.isPending}
              onClick={() => pauseMutation.mutate()}
            >
              {pauseStatus?.text ?? '暂停'}
            </Button>
            <Select
              value={getEndAction()}
              onChange={v => endActionMutation.mutate(v)}
              options={endActionOptions}
            />
          </ControlRow>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
            任务运行时间: <strong>{runtime ?? '未运行'}</strong>
          </div>
        </Section>
      </Card>

      <Card>
        <Section title="快速设置">
          <ControlRow>
            <Button size="sm" onClick={() => handleQuickBatch(true, undefined)}>全选</Button>
            <Button size="sm" onClick={() => handleQuickBatch(false, undefined)}>清空</Button>
            <Button size="sm" onClick={() => {
              quickTaskFields.forEach(({ field }) => {
                saveFieldMutation.mutate({ path: `options.${field}`, value: field === 'produce.enabled' });
              });
            }}>只选培育</Button>
            <Button size="sm" onClick={() => {
              quickTaskFields.forEach(({ field }) => {
                saveFieldMutation.mutate({ path: `options.${field}`, value: field !== 'produce.enabled' });
              });
            }}>只不选培育</Button>
          </ControlRow>
          <QuickGrid>
            {quickTaskFields.map(({ label, field }) => (
              <Checkbox
                key={field}
                label={label}
                checked={getFieldValue(field)}
                onChange={checked => saveFieldMutation.mutate({ path: `options.${field}`, value: checked })}
              />
            ))}
          </QuickGrid>
        </Section>
      </Card>

      <Card>
        <Section title="任务状态">
          <TaskTable>
            <thead>
              <tr>
                <Th>任务</Th>
                <Th>状态</Th>
              </tr>
            </thead>
            <tbody>
              {statuses?.map((s: TaskStatus) => (
                <tr key={s.name}>
                  <Td>{s.name}</Td>
                  <Td>
                    <StatusBadge $status={s.status}>{statusLabel(s.status)}</StatusBadge>
                  </Td>
                </tr>
              ))}
              {(!statuses || statuses.length === 0) && (
                <tr>
                  <Td colSpan={2} style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: 'var(--space-4)' }}>
                    暂无任务
                  </Td>
                </tr>
              )}
            </tbody>
          </TaskTable>
        </Section>
      </Card>

      <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
        脚本报错或者卡住？前往「反馈」选项卡可以快速导出报告！
      </div>
    </PageContainer>
  );
};
