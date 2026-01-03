import { useQuery } from '@tanstack/react-query';
import useOptimisticMutation from './useOptimisticMutation';
import { getOptions, patchOptions, saveOptions } from '../api/client';

export function useConfigOptions() {
  const query = useQuery<any, Error>({
    queryKey: ['get_options'],
    queryFn: getOptions,
  });

  // 1. 补全泛型，确保 TVariables (第三个) 是正确的
  // 泛型顺序: <TMutationData, TError, TVariables, TQueryData>
  const patchMut = useOptimisticMutation<
    any,                  // 后端返回的数据类型
    Error,                // 错误类型
    Record<string, any>,  // 变量(参数)类型 -> 这里定义了 patch 是对象
    any                   // 缓存中的数据类型
  >(
    ['get_options'],
    async (patch) => patchOptions(patch),
    {
      autoReplace: true 
    }
  );

  const saveMut = useOptimisticMutation<any, Error, any, any>(
    ['get_options'],
    async (opts) => saveOptions(opts),
    // 如果 saveOptions 也返回最新配置，这里也可以加 { autoReplace: true }
  );

  return { ...query, patchOptions: patchMut, saveOptions: saveMut };
}

export default useConfigOptions;