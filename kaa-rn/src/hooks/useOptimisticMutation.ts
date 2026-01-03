import {
  useMutation,
  useQueryClient,
  type MutationFunction,
  type QueryKey,
  type UseMutationResult,
} from '@tanstack/react-query';
import { produce, type Draft } from 'immer';

// 定义 Context 用于回滚
interface OptimisticContext<TQueryData> {
  previousData: TQueryData | undefined;
}

/**
 * 乐观更新回调 (Mutate 前执行)
 */
export type OptimisticUpdater<TQueryData, TVariables> = (
  draft: Draft<TQueryData>,
  variables: TVariables
) => void | TQueryData;

/**
 * 服务端确认回调 (Success 后执行)
 * result: 后端接口返回的最新数据
 */
export type ServerSuccessUpdater<TQueryData, TMutationData, TVariables> = (
  draft: Draft<TQueryData>,
  result: TMutationData,
  variables: TVariables
) => void | TQueryData;

export interface OptimisticOptions<TQueryData, TMutationData, TVariables> {
  /**
   * 乐观更新逻辑，将会在发送请求前执行。
   * 
   * 可以在这里将本次请求修改的内容立刻反映到 React Query 缓存中，
   * 提升用户体验。
   */
  updater?: OptimisticUpdater<TQueryData, TVariables>;

  /**
   * 服务端数据同步逻辑，将会在请求成功后执行。
   *
   * 利用后端返回的 result 来修正缓存，确保数据绝对正确
   */
  onServerSuccess?: ServerSuccessUpdater<TQueryData, TMutationData, TVariables>;

  /**
   * 自动全量替换。
   * 
   * 如果后端返回的数据结构 (TMutationData) 和缓存 (TQueryData) 一致，
   * 设为 true 可直接用后端返回值覆盖缓存，无需手动写 onServerSuccess。
   * @default false
   */
  autoReplace?: boolean;
}

/**
 * 带有乐观更新的 React Query Mutation Hook。
 * 
 * @template TMutationData - 后端接口返回的数据类型
 * @template TError - 错误类型
 * @template TVariables - 请求参数类型
 * @template TQueryData - 本地 Query 缓存的数据类型
 */
export default function useOptimisticMutation<
  TMutationData = unknown,
  TError = unknown,
  TVariables = void,
  TQueryData = unknown
>(
  queryKey: QueryKey,
  mutationFn: MutationFunction<TMutationData, TVariables>,
  options?: OptimisticOptions<TQueryData, TMutationData, TVariables>
): UseMutationResult<
  TMutationData,
  TError,
  TVariables,
  OptimisticContext<TQueryData>
> {
  const queryClient = useQueryClient();
  const { updater, onServerSuccess, autoReplace = false } = options || {};

  return useMutation({
    mutationFn,

    // === 阶段 1: 乐观更新 ===
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey });
      const previousData = queryClient.getQueryData<TQueryData>(queryKey);

      if (updater && previousData) {
        queryClient.setQueryData<TQueryData>(queryKey, (oldData) => {
          if (oldData === undefined) return undefined;
          return produce(oldData, (draft) => {
            updater(draft, variables);
          });
        });
      }

      return { previousData };
    },

    // === 阶段 2: 服务端数据确认 ===
    onSuccess: (data, variables) => {
      // 策略 A: 自动替换 (适用于 patch_options 返回完整 BaseConfig)
      if (autoReplace) {
        queryClient.setQueryData(queryKey, data as unknown as TQueryData);
        return;
      }

      // 策略 B: 手动合并 (适用于只返回部分数据)
      if (onServerSuccess) {
        queryClient.setQueryData<TQueryData>(queryKey, (oldData) => {
          if (oldData === undefined) return undefined;
          return produce(oldData, (draft) => {
            onServerSuccess(draft, data, variables);
          });
        });
      }
    },

    // === 阶段 3: 错误回滚 ===
    onError: (_err, _vars, context) => {
      if (context?.previousData !== undefined) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
    },

    // === 阶段 4: 解决时序问题 ===
    onSettled: () => {
      // 关键点：标记数据为 stale (过期)，但**禁止立即重新请求** (refetchType: 'none')。
      // 因为我们刚刚在 onSuccess 里用后端的数据更新了缓存，现在的缓存是最新的。
      // 如果立即 refetch，可能会因为数据库写入延迟读到旧数据。
      // 这样设置后，只有当用户切出页面再切回来时，才会真正发请求。
      queryClient.invalidateQueries({
        queryKey,
        refetchType: 'none',
      });
    },
  });
}