import React from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { Text, useTheme } from 'react-native-paper';

interface LogItem {
  id: number;
  time: string;
  level: string;
  message: string;
}

interface LogPanelProps {
  logs: LogItem[];
}

export const LogPanel: React.FC<LogPanelProps> = ({ logs }) => {
  const theme = useTheme();

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {logs.map((log) => (
          <Text key={log.id} style={styles.logLine} variant="bodySmall">
            <Text style={{ color: '#666' }}>[{log.time}] </Text>
            <Text style={{ color: log.level === 'SUCCESS' ? 'green' : log.level === 'ERROR' ? 'red' : theme.colors.primary }}>
              {log.level}:{' '}
            </Text>
            <Text>{log.message}</Text>
          </Text>
        ))}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    padding: 8,
    borderRadius: 8,
  },
  scrollContent: {
    paddingBottom: 16,
  },
  logLine: {
    marginBottom: 4,
    fontFamily: 'monospace',
  },
});
