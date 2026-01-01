import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Card, Text, useTheme } from 'react-native-paper';

interface StatusCardProps {
  status: string;
  detail: string;
}

export const StatusCard: React.FC<StatusCardProps> = ({ status, detail }) => {
  const theme = useTheme();

  return (
    <Card style={styles.card}>
      <Card.Content>
        <Text variant="titleMedium" style={styles.title}>
          当前状态
        </Text>
        <Text variant="bodyLarge">
          {status} - {detail}
        </Text>
      </Card.Content>
    </Card>
  );
};

const styles = StyleSheet.create({
  card: {
    marginBottom: 16,
    backgroundColor: 'white',
  },
  title: {
    marginBottom: 8,
    fontWeight: 'bold',
  },
  chartContainer: {
    height: 60,
    width: '100%',
    backgroundColor: '#FFF3E0', // Light orange background
    borderRadius: 8,
    overflow: 'hidden',
  },
});
