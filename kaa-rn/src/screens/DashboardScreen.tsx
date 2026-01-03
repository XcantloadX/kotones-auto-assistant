import React from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { Text, Button, useTheme, FAB, ActivityIndicator } from 'react-native-paper';
import { StatusCard } from '../components/StatusCard';
import { ModuleCard } from '../components/ModuleCard';
import { LogPanel } from '../components/LogPanel';
import { LOGS, STATUS } from '../data/mockData';
import useQuickSettings from '../hooks/useQuickSettings';
import useTaskOverview from '../hooks/useTasks';
import { useDeviceType } from '../hooks/useDeviceType';
import useBackendVersion from '../hooks/useBackendVersion';

export const DashboardScreen = () => {
  const theme = useTheme();
  const { isLargeScreen } = useDeviceType();
  const { data: version } = useBackendVersion();

  const { data: quickData, isLoading: quickLoading, patchQuickSettings } = useQuickSettings();
  const { data: overview, isLoading: overviewLoading, runAll, stopAll, pauseToggle } = useTaskOverview();

  const toggleModule = (valueKey?: string, id?: string) => {
    if (!quickData) return;
    const key = valueKey || id;
    if (!key) return;
    const current = (quickData as any).values?.[key];
    patchQuickSettings.mutate({ [key]: !current });
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
              {isLargeScreen && <Text variant="bodySmall" style={styles.version}>{`v${version}`}</Text>}
            </View>
            {isLargeScreen ? (
              <View style={styles.headerControls}>
                <Button
                  mode="contained"
                  onPress={() => {
                    if (!overview) return;
                    if (overview.run_button?.status === 'start') runAll.mutate();
                    else runAll.mutate();
                  }}
                  disabled={overviewLoading || !overview?.run_button?.interactive}
                  style={styles.startButton}
                >
                  {overview?.run_button?.status === 'stop' ? '停止' : overview?.run_button?.status === 'stopping' ? '停止中' : '启动'}
                </Button>

                <Button
                  mode="outlined"
                  onPress={() => {
                    if (!overview) return;
                    pauseToggle.mutate();
                  }}
                  disabled={overviewLoading || !overview?.pause_button?.interactive}
                  style={styles.actionButton}
                >
                  {overview?.pause_button?.status === 'resume' ? '恢复' : '暂停'}
                </Button>
              </View>
            ) : (
              <></>
            )}
          </View>

          {/* Main Dashboard Content */}
          <ScrollView style={styles.mainContent} contentContainerStyle={!isLargeScreen && { paddingBottom: 80 }}>
            <StatusCard status={STATUS.state} detail={STATUS.detail} />
            
            {!isLargeScreen && <View style={{ height: 16 }} />}

            {isLargeScreen && <Text variant="titleMedium" style={styles.sectionTitle}>模块开关</Text>}
            
            <View style={isLargeScreen ? styles.grid : styles.list}>
              {quickLoading ? (
                <View style={styles.loadingContainer}>
                  <ActivityIndicator animating={true} size={48} />
                </View>
              ) : (
                quickData?.items?.map((module) => {
                const key = module.value_key || module.id;
                const enabled = quickData?.values ? (quickData.values as any)[key] : false;
                return (
                  <View key={module.id} style={isLargeScreen ? styles.gridItem : styles.listItem}>
                    <ModuleCard
                      name={module.name}
                      icon={module.icon as any}
                      enabled={enabled}
                      hasSettings={!!module.has_settings}
                      onToggle={() => toggleModule(module.value_key ?? undefined, module.id)}
                      isMobile={!isLargeScreen}
                    />
                  </View>
                );
                })
              )}
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
          onPress={() => runAll.mutate()}
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
  loadingContainer: {
    width: '100%',
    minHeight: 120,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 24,
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
