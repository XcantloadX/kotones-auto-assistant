import { useWindowDimensions, Platform } from 'react-native';

export type DeviceInfo = {
  width: number;
  height: number;
  platform: string;
  isWeb: boolean;
  isDesktop: boolean;
  isTablet: boolean;
  isMobile: boolean;
  isLargeScreen: boolean;
};

/**
 * Hook to determine device type (mobile / tablet / desktop) in a single place.
 * Uses platform + screen width thresholds. Default threshold for "large" screens is 800px.
 */
export function useDeviceType(threshold = 800): DeviceInfo {
  const { width, height } = useWindowDimensions();
  const platform = Platform.OS;

  const isWeb = platform === 'web';
  const desktopLikePlatform = isWeb || platform === 'windows' || platform === 'macos';

  const isLargeScreen = width > threshold;
  const isDesktop = desktopLikePlatform && isLargeScreen;
  const isTablet = !isDesktop && width >= 600 && width <= threshold;
  const isMobile = !isDesktop && width < 600;

  return {
    width,
    height,
    platform,
    isWeb,
    isDesktop,
    isTablet,
    isMobile,
    isLargeScreen,
  };
}
