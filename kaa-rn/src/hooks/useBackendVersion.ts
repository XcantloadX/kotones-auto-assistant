import { useQuery } from '@tanstack/react-query';
import { getBackendVersion } from '../api/client';

export function useBackendVersion() {
  const query = useQuery<string | null, Error>({
    queryKey: ['backend_version'],
    queryFn: getBackendVersion,
    staleTime: 1000 * 60 * 5,
  });

  return query;
}

export default useBackendVersion;
