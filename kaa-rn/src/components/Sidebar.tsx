import React from 'react';
import { View, StyleSheet, TouchableOpacity } from 'react-native';
import { Text, useTheme, Icon } from 'react-native-paper';

const MENU_ITEMS = [
  { id: 'dashboard', label: '总览', icon: 'view-dashboard-outline' },
  { id: 'config', label: '配置', icon: 'tune' },
  { id: 'produce', label: '培育', icon: 'school-outline' },
  { id: 'about', label: '关于', icon: 'information-outline' },
];

interface SidebarProps {
  activeTab: string;
  onTabChange: (id: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  const theme = useTheme();

  return (
    <View style={[styles.container, { backgroundColor: '#F2F4F8' }]}>
      {/* Top Logo Area */}
      <View style={styles.logoContainer}>
        <View style={styles.logoIcon}>
          <Icon source="book" size={20} color="#555" />
        </View>
      </View>

      {/* Menu Items */}
      <View style={styles.menuContainer}>
        {MENU_ITEMS.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <TouchableOpacity
              key={item.id}
              style={[
                styles.item,
                isActive && { backgroundColor: '#E1E4E8' },
              ]}
              onPress={() => onTabChange(item.id)}
            >
              <Icon
                source={item.icon}
                size={24}
                color={isActive ? '#1A1A1A' : '#666666'}
              />
              <Text
                variant="labelSmall"
                style={[
                  styles.label,
                  { color: isActive ? '#1A1A1A' : '#666666' },
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
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: 72,
    height: '100%',
    alignItems: 'center',
    paddingVertical: 16,
    borderRightWidth: 1,
    borderRightColor: '#E1E4E8',
  },
  logoContainer: {
    marginBottom: 24,
    alignItems: 'center',
    justifyContent: 'center',
    width: 48,
    height: 48,
  },
  logoIcon: {
    width: 32,
    height: 32,
    borderRadius: 8,
    backgroundColor: '#E1E4E8',
    alignItems: 'center',
    justifyContent: 'center',
  },
  menuContainer: {
    flex: 1,
    width: '100%',
    alignItems: 'center',
    gap: 8,
  },
  item: {
    alignItems: 'center',
    justifyContent: 'center',
    width: 56,
    height: 56,
    borderRadius: 12,
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
