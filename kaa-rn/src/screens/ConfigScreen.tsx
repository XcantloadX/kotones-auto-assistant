import React from 'react';
import { useDeviceType } from '../hooks/useDeviceType';
import { ConfigFormData, DEFAULT_CONFIG_VALUES } from './config/types';
import { ConfigScreenDesktop } from './config/ConfigScreenDesktop';
import { ConfigScreenMobile } from './config/ConfigScreenMobile';

export const ConfigScreen = () => {
  const { isMobile } = useDeviceType();
  return isMobile ? (
    <ConfigScreenMobile />
  ) : (
    <ConfigScreenDesktop />
  );
};
