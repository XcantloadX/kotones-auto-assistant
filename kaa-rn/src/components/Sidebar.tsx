import React from 'react';
import { View, StyleSheet, TouchableOpacity } from 'react-native';
import { Text, useTheme, Icon } from 'react-native-paper';

const MENU_ITEMS = [
  { id: 'dashboard', label: '总览', icon: 'view-dashboard-outline' },
  { id: 'config', label: '配置', icon: 'tune' },
  { id: 'produce', label: '培育', icon: 'school-outline' },
];

const BOTTOM_ITEM = { id: 'about', label: '关于', icon: 'information-outline' };

interface SidebarProps {
  activeTab: string;
  onTabChange: (id: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  const theme = useTheme();

  const secondaryContainer = theme.colors?.secondaryContainer ?? '#FFDCC2';
  const onSecondaryContainer = theme.colors?.onSecondaryContainer ?? '#2E1500';
  const onSurfaceVariant = theme.colors?.onSurfaceVariant ?? '#49454F';
  const onSurface = theme.colors?.onSurface ?? '#1d1b20';

  return (
    <View style={[styles.container, { backgroundColor: '#F2F4F8' }]}>

      {/* Menu Items */}
      <View style={styles.menuContainer}>
        {MENU_ITEMS.map((item) => {
          const isActive = activeTab === item.id;
          const iconName = isActive ? item.icon.replace('-outline', '') : item.icon;
          return (
            <TouchableOpacity
              key={item.id}
              style={styles.item}
              onPress={() => onTabChange(item.id)}
              activeOpacity={0.7}
            >
              <View
                style={[
                  styles.iconContainer,
                  isActive && { backgroundColor: secondaryContainer },
                ]}
              >
                <Icon
                  source={iconName}
                  size={24}
                  color={isActive ? onSecondaryContainer : onSurfaceVariant}
                />
              </View>

              <Text
                variant="labelSmall"
                style={[
                  styles.label,
                  isActive && { color: onSurface, fontWeight: '700' },
                ]}
              >
                {item.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Bottom Action */}
      <View style={styles.bottomContainer}>
        {(() => {
          const item = BOTTOM_ITEM;
          const isActive = activeTab === item.id;
          const iconName = isActive ? item.icon.replace('-outline', '') : item.icon;
          return (
            <TouchableOpacity
              key={item.id}
              style={styles.item}
              onPress={() => onTabChange(item.id)}
              activeOpacity={0.7}
            >
              <View
                style={[
                  styles.iconContainer,
                  isActive && { backgroundColor: secondaryContainer },
                ]}
              >
                <Icon
                  source={iconName}
                  size={24}
                  color={isActive ? onSecondaryContainer : onSurfaceVariant}
                />
              </View>

              <Text
                variant="labelSmall"
                style={[
                  styles.label,
                  isActive && { color: onSurface, fontWeight: '700' },
                ]}
              >
                {item.label}
              </Text>
            </TouchableOpacity>
          );
        })()}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: 80,
    height: '100%',
    alignItems: 'center',
    paddingTop: 20,
    paddingBottom: 12,
  },
  menuContainer: {
    flex: 1,
    width: '100%',
    alignItems: 'center',
    gap: 8,
  },
  item: {
    alignItems: 'center',
    justifyContent: 'flex-start',
    width: '100%',
    paddingVertical: 6,
    marginBottom: 12,
  },
  iconContainer: {
    width: 56,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 4,
  },
  label: {
    marginTop: 4,
    fontSize: 11,
    fontWeight: '500',
  },
  bottomContainer: {
    marginTop: 'auto',
    marginBottom: 8,
  },
  bottomItem: {
    width: 48,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 24,
  },
});
