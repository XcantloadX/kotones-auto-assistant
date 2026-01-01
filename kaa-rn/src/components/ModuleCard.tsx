import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Card, Text, useTheme } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { MD3Switch } from './MD3Switch';

interface ModuleCardProps {
  name: string;
  icon: string;
  enabled: boolean;
  hasSettings: boolean;
  onToggle: () => void;
  isMobile?: boolean;
}

export const ModuleCard: React.FC<ModuleCardProps> = ({ name, icon, enabled, hasSettings, onToggle, isMobile }) => {
  const theme = useTheme();

  if (isMobile) {
    return (
      <Card style={styles.mobileCard} onPress={onToggle}>
        <Card.Content style={styles.mobileContent}>
          <View style={styles.mobileRow}>
            <View style={[styles.iconBox, { backgroundColor: '#F5F5F5' }]}>
              <MaterialCommunityIcons name={icon as any} size={24} color={theme.colors.onSurface} />
            </View>
            <View style={styles.mobileTextContainer}>
              <Text variant="titleMedium" style={styles.title}>{name}</Text>
              <Text variant="bodySmall" style={{ color: enabled ? theme.colors.primary : '#999' }}>
                {enabled ? '进行中' : '等待中'}
              </Text>
            </View>
          </View>
        </Card.Content>
      </Card>
    );
  }

  return (
    <Card style={styles.card}>
      <Card.Content style={styles.content}>
        <View style={styles.header}>
          <View style={styles.iconTitle}>
            <MaterialCommunityIcons name={icon as any} size={20} color={theme.colors.onSurface} />
            <Text variant="titleMedium" style={styles.title}>{name}</Text>
          </View>
          <MD3Switch value={enabled} onValueChange={onToggle} />
        </View>
      </Card.Content>
    </Card>
  );
};

const styles = StyleSheet.create({
  card: {
    flex: 1,
    margin: 4,
    backgroundColor: 'white',
    minWidth: 140,
  },
  mobileCard: {
    marginBottom: 12,
    backgroundColor: 'white',
    elevation: 1,
  },
  content: {
    padding: 12,
  },
  mobileContent: {
    padding: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  mobileRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  iconTitle: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  iconBox: {
    width: 48,
    height: 48,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  mobileTextContainer: {
    flex: 1,
  },
  title: {
    fontWeight: 'bold',
  },
  // slider and progress styles removed per design
  progressBar: {
    marginTop: 12,
  }
});
