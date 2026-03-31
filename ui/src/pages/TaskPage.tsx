/** @jsxImportSource @emotion/react */
import styled from '@emotion/styled';
import React, { useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/api';
import { useEvent } from '../api/client';
import { Button } from '../components/common/Button';
import { Card, Section } from '../components/common/Card';
import { PageContainer, PageTitle } from '../components/layout/Layout';

const TaskList = styled.div`
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
`;

const TaskRow = styled.div`
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
`;

const TaskName = styled.span`
  flex: 1;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
`;

const StatusText = styled.div`
  min-height: 20px;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
`;

export const TaskPage: React.FC = () => {
  const qc = useQueryClient();

  const { data: taskNames } = useQuery({
    queryKey: ['taskNames'],
    queryFn: api.task.getAllNames,
    staleTime: Infinity,
  });

  const { data: runStatus } = useQuery({
    queryKey: ['runStatus'],
    queryFn: api.task.getRunStatus,
    refetchInterval: 1000,
  });

  const { data: pauseStatus } = useQuery({
    queryKey: ['pauseStatus'],
    queryFn: api.task.getPauseStatus,
    refetchInterval: 1000,
  });

  const { data: statuses } = useQuery({
    queryKey: ['taskStatuses'],
    queryFn: api.task.getStatuses,
    refetchInterval: 1000,
  });

  useEvent('task.stopped', useCallback(() => {
    qc.invalidateQueries({ queryKey: ['runStatus'] });
    qc.invalidateQueries({ queryKey: ['pauseStatus'] });
  }, [qc]));

  const startMutation = useMutation({
    mutationFn: (name: string) => api.task.startSingle(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['runStatus'] });
    },
  });

  const stopMutation = useMutation({
    mutationFn: api.task.stopAll,
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

  const isRunning = runStatus?.text === '停止';
  const isStopping = runStatus?.text === '停止中...';

  const getTaskStatus = (name: string) => {
    return statuses?.find(s => s.name === name)?.status ?? 'pending';
  };

  const runningTaskName = statuses?.find(s => s.status === 'running')?.name;

  return (
    <PageContainer>
      <PageTitle>执行任务</PageTitle>

      <Card>
        <Section>
          <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
            <Button
              variant="destructive"
              onClick={() => stopMutation.mutate()}
              disabled={!isRunning && !isStopping}
              loading={stopMutation.isPending}
            >
              停止任务
            </Button>
            <Button
              onClick={() => pauseMutation.mutate()}
              disabled={!pauseStatus?.interactive}
            >
              {pauseStatus?.text ?? '暂停'}
            </Button>
            {runningTaskName && (
              <StatusText>
                正在执行任务: <strong>{runningTaskName}</strong>
              </StatusText>
            )}
          </div>
        </Section>
      </Card>

      <Card>
        <Section title="可执行任务">
          <TaskList>
            {taskNames?.map(name => {
              const status = getTaskStatus(name);
              const isThisRunning = status === 'running';

              return (
                <TaskRow key={name}>
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={isRunning || isStopping || startMutation.isPending}
                    loading={startMutation.variables === name && startMutation.isPending}
                    onClick={() => startMutation.mutate(name)}
                    style={{ minWidth: 60 }}
                  >
                    {isThisRunning ? '运行中' : '启动'}
                  </Button>
                  <TaskName>{name}</TaskName>
                </TaskRow>
              );
            })}
            {(!taskNames || taskNames.length === 0) && (
              <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: 'var(--space-4)' }}>
                暂无任务
              </div>
            )}
          </TaskList>
        </Section>
      </Card>
    </PageContainer>
  );
};
