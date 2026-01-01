import React, { useState } from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { Text, Button, useTheme, FAB } from 'react-native-paper';
import { StatusCard } from '../components/StatusCard';
import { ModuleCard } from '../components/ModuleCard';
import { LogPanel } from '../components/LogPanel';
import { MODULES, LOGS, STATUS } from '../data/mockData';
import { useDeviceType } from '../hooks/useDeviceType';

export const DashboardScreen = () => {
  const theme = useTheme();
  const { isLargeScreen } = useDeviceType();

  const [modules, setModules] = useState(MODULES);

  const toggleModule = (id: string) => {
    setModules(prev => prev.map(m => m.id === id ? { ...m, enabled: !m.enabled } : m));
  };

  return (
    <View style={styles.container}>
      <View style={styles.contentRow}>
        {/* Left Column: Header + Main Content */}
        <View style={styles.leftColumn}>
          {/* Header Area */}
          <View style={styles.header}>
            <View>
              <Text variant="headlineMedium" style={styles.appTitle}>琴音小助手</Text>
              {isLargeScreen && <Text variant="bodySmall" style={styles.version}>v2025.11.post3</Text>}
            </View>
            {isLargeScreen ? (
              <View style={styles.headerControls}>
                <Button mode="contained" onPress={() => {}} style={styles.startButton}>
                  启动
                </Button>
                <Button mode="outlined" onPress={() => {}} style={styles.actionButton}>
                  完成后: 什么都不做
                </Button>
              </View>
            ) : (
              // small-screen header shows compact layout (no avatar)
              <></>
            )}
          </View>

          {/* Main Dashboard Content */}
          <ScrollView style={styles.mainContent} contentContainerStyle={!isLargeScreen && { paddingBottom: 80 }}>
            <StatusCard status={STATUS.state} detail={STATUS.detail} />
            
            {!isLargeScreen && <View style={{ height: 16 }} />}

            {isLargeScreen && <Text variant="titleMedium" style={styles.sectionTitle}>模块开关</Text>}
            
            <View style={isLargeScreen ? styles.grid : styles.list}>
              {modules.map((module) => (
                <View key={module.id} style={isLargeScreen ? styles.gridItem : styles.listItem}>
                  <ModuleCard
                    {...module}
                    onToggle={() => toggleModule(module.id)}
                    isMobile={!isLargeScreen}
                  />
                </View>
              ))}
            </View>
          </ScrollView>
        </View>

        {/* Log Panel - Visible on large screens or as a bottom section on small */}
        <View style={[styles.logContainer, !isLargeScreen && styles.logContainerSmall]}>
           <LogPanel logs={LOGS} />
        </View>
      </View>

      {!isLargeScreen && (
        <FAB
          icon="play"
          style={[styles.fab, { backgroundColor: theme.colors.primary }]}
          color="white"
          onPress={() => console.log('Start')}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#F7F9FC',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  appTitle: {
    fontWeight: 'bold',
  },
  version: {
    color: '#666',
  },
  headerControls: {
    flexDirection: 'row',
    gap: 12,
  },
  startButton: {
    borderRadius: 20,
    paddingHorizontal: 16,
  },
  actionButton: {
    borderRadius: 4,
    borderColor: '#E0E0E0',
  },
  contentRow: {
    flex: 1,
    flexDirection: 'row',
    gap: 16,
  },
  leftColumn: {
    flex: 2,
    flexDirection: 'column',
  },
  mainContent: {
    flex: 1,
  },
  sectionTitle: {
    marginBottom: 12,
    marginTop: 8,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: -4,
  },
  gridItem: {
    width: '33.33%', // 3 columns
    padding: 4,
    minWidth: 150,
  },
  list: {
    flexDirection: 'column',
  },
  listItem: {
    width: '100%',
  },
  logContainer: {
    flex: 1,
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 8,
    borderLeftWidth: 1,
    borderLeftColor: '#E0E0E0',
  },
  logContainerSmall: {
    display: 'none', // Hide on small screens for now, or make it a bottom sheet
  },
  fab: {
    position: 'absolute',
    margin: 16,
    right: 0,
    bottom: 0,
    borderRadius: 30,
  },
});
