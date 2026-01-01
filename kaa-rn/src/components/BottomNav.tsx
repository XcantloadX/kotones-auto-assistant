import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Text, Icon, TouchableRipple, useTheme } from 'react-native-paper';

const MENU_ITEMS = [
  { id: 'dashboard', label: '仪表盘', icon: 'view-dashboard' },
  { id: 'config', label: '配置', icon: 'tune' },
  { id: 'produce', label: '培育', icon: 'school-outline' },
  { id: 'about', label: '关于', icon: 'information' },
];

interface BottomNavProps {
  activeTab: string;
  onTabChange: (id: string) => void;
}

export const BottomNav: React.FC<BottomNavProps> = ({ activeTab, onTabChange }) => {
  const theme = useTheme();

  return (
    <View style={styles.container}>
      {MENU_ITEMS.map((item) => {
        const isActive = activeTab === item.id;
        return (
          <TouchableRipple
            key={item.id}
            style={styles.item}
            onPress={() => onTabChange(item.id)}
            rippleColor="rgba(0, 0, 0, .1)"
          >
            <View style={styles.content}>
              <Icon
                source={item.icon}
                size={24}
                color={isActive ? theme.colors.primary : theme.colors.onSurfaceVariant}
              />
              <Text
                variant="labelSmall"
                style={[
                  styles.label,
                  { color: isActive ? theme.colors.primary : theme.colors.onSurfaceVariant },
                ]}
              >
                {item.label}
              </Text>
            </View>
          </TouchableRipple>
        );
      })}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    backgroundColor: 'white',
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
    height: 60,
    paddingBottom: 4,
  },
  item: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    alignItems: 'center',
  },
  label: {
    marginTop: 4,
  },
});
