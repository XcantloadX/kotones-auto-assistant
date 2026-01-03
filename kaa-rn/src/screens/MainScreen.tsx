import React, { useState } from 'react';
import { View, StyleSheet, SafeAreaView, Platform } from 'react-native';
import { Sidebar } from '../components/Sidebar';
import { BottomNav } from '../components/BottomNav';
import { DashboardScreen } from './DashboardScreen';
import { ConfigScreen } from './ConfigScreen';
import { ProduceScreen } from './ProduceScreen';
import { AboutScreen } from './AboutScreen';
import { Text } from 'react-native-paper';
import { useDeviceType } from '../hooks/useDeviceType';

export const MainScreen = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const { isLargeScreen } = useDeviceType();

  // Always mount screens, control visibility via style (display: 'none')
  const isActive = (id: string) => activeTab === id;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.row}>
        {isLargeScreen && <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />}
        <View style={styles.content}>
          <View style={[styles.screen, !isActive('dashboard') && styles.hidden]}>
            <DashboardScreen />
          </View>
          <View style={[styles.screen, !isActive('config') && styles.hidden]}>
            <ConfigScreen />
          </View>
          <View style={[styles.screen, !isActive('produce') && styles.hidden]}>
            <ProduceScreen />
          </View>
          <View style={[styles.screen, !isActive('about') && styles.hidden]}>
            <AboutScreen />
          </View>
        </View>
      </View>
      {!isLargeScreen && <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />}
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  row: {
    flex: 1,
    flexDirection: 'row',
  },
  content: {
    flex: 1,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  screen: {
    flex: 1,
  },
  hidden: {
    display: 'none',
  },
  
});
