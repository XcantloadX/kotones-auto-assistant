import React from 'react';
import { View, Pressable, StyleSheet } from 'react-native';
import { List, Text, useTheme } from 'react-native-paper';
import { MD3Switch } from './MD3Switch';
import { useDeviceType } from '../hooks/useDeviceType';

interface Props {
  label: string;
  description?: string;
  value?: boolean;
  onValueChange?: (v: boolean) => void;
  disabled?: boolean;
  size?: 'small' | 'medium';
}

const MD3SwitchItem: React.FC<Props> = ({ label, description, value, onValueChange, disabled, size = 'small' }) => {
  const { isMobile } = useDeviceType();
  const theme = useTheme();

  const handlePress = () => {
    if (disabled) return;
    onValueChange && onValueChange(!value);
  };

  const contentDesktop = (
    <Pressable
      onPress={handlePress}
      disabled={disabled}
      style={({ pressed }) => [styles.pressable, pressed && styles.pressed]}
      accessibilityRole="switch"
      accessibilityState={{ disabled, checked: !!value }}
      accessibilityLabel={label}
    >
      <View style={styles.row}>
        <MD3Switch value={value} onValueChange={onValueChange} disabled={disabled} size={size} />
        <View style={styles.textContainer}>
          <Text variant="bodyMedium" style={[styles.labelDesktop, disabled && { opacity: 0.5 }, { color: theme.colors.onSurfaceVariant }]}>{label}</Text>
          {description ? (
            <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 6 }}>{description}</Text>
          ) : null}
        </View>
      </View>
    </Pressable>
  );

  const contentMobile = (
    <Pressable
      onPress={handlePress}
      disabled={disabled}
        style={({ pressed }) => [styles.pressableMobile, pressed && styles.pressed]}
      accessibilityRole="switch"
      accessibilityState={{ disabled, checked: !!value }}
      accessibilityLabel={label}
    >
      <List.Item
        title={label}
        description={description}
        style={{ flex: 1 }}
        right={() =>
          <MD3Switch value={value} onValueChange={onValueChange} disabled={disabled} size="medium" />
        }
      >
      </List.Item>
    </Pressable>
  );

  return isMobile ? contentMobile : contentDesktop;
};

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 6,
    marginBottom: 4,
  },
  rowMobile: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
    marginBottom: 8,
  },
  textContainer: {
    marginLeft: 12,
  },
  labelDesktop: {
    fontSize: 13,
    marginLeft: 2,
  },
  labelMobile: {
    fontSize: 16,
  },
  switchContainerMobile: {
    transform: [{ scale: 1.35 }],
    alignSelf: 'center',
  },
  pressable: {
    borderRadius: 6,
  },
  pressableMobile: {
    borderRadius: 8,
  },
  pressed: {
  },
});

export default MD3SwitchItem;
