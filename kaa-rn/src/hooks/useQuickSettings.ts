import { useQuery } from '@tanstack/react-query';
import useOptimisticMutation from './useOptimisticMutation';
import { getQuickSettings, patchQuickSettings } from '../api/client';
import type { QuickSettingsResponse } from '../types/api';

export function useQuickSettings() {
  const query = useQuery<QuickSettingsResponse, Error>({
    queryKey: ['get_quick'],
    queryFn: getQuickSettings,
  });

  const mut = useOptimisticMutation<QuickSettingsResponse, Record<string, any>>(
    ['get_quick'],
    patchQuickSettings,
    (draft, patch) => {
      if (!draft) return;
      // Only merge into values (the boolean flags), keep items intact
      draft.values = { ...draft.values, ...patch } as any;
    }
  );

  return { ...query, patchQuickSettings: mut };
}

export default useQuickSettings;
