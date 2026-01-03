import React from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { Text, List, useTheme } from 'react-native-paper';
import { useScrollSpy } from '../../hooks/useScrollSpy';
import { SETTINGS_SECTIONS, ConfigFormData } from './types';
import { ConfigFormSections } from './ConfigFormSections';

export const ConfigScreenDesktop: React.FC = () => {
  const theme = useTheme();
  const allSectionIds = SETTINGS_SECTIONS.flatMap(s => [s.id, ...(s.children?.map(c => c.id) || [])]);
  const { activeSection, scrollViewRef, onSectionLayout, scrollToSection, handleScroll, handleScrollEnd } = useScrollSpy(allSectionIds);

  return (
    <View style={styles.container}>
      {/* Left Sidebar */}
      <View style={[styles.sidebar, { borderRightColor: theme.colors.outlineVariant }]}>
        <ScrollView>
          {SETTINGS_SECTIONS.map((section) => {
            const isActive = activeSection === section.id || (section.children && section.children.some(c => c.id === activeSection));
            
            return (
              <React.Fragment key={section.id}>
                <List.Item
                  title={section.label}
                  left={props => <List.Icon {...props} icon={section.icon} color={isActive ? theme.colors.primary : props.color} />}
                  onPress={() => scrollToSection(section.id)}
                  style={[
                    styles.sidebarItem,
                    {
                      borderLeftWidth: 4,
                      borderLeftColor: activeSection === section.id ? theme.colors.primary : 'transparent',
                      backgroundColor: activeSection === section.id ? theme.colors.surfaceVariant : 'transparent',
                    }
                  ]}
                  titleStyle={isActive && {
                    color: theme.colors.primary,
                    fontWeight: 'bold',
                  }}
                />
                {section.children && section.children.map(child => {
                   const isChildActive = activeSection === child.id;
                   return (
                     <List.Item
                       key={child.id}
                       title={child.label}
                       onPress={() => scrollToSection(child.id)}
                       style={[
                         styles.sidebarItem,
                         {
                           paddingLeft: 32,
                           borderLeftWidth: 4,
                           borderLeftColor: isChildActive ? theme.colors.primary : 'transparent',
                           backgroundColor: isChildActive ? theme.colors.surfaceVariant : 'transparent',
                           height: 40,
                         }
                       ]}
                       titleStyle={[
                         { fontSize: 13 },
                         isChildActive && { color: theme.colors.primary, fontWeight: 'bold' }
                       ]}
                     />
                   );
                })}
              </React.Fragment>
            );
          })}
        </ScrollView>
      </View>

      {/* Right Content */}
      <View style={styles.content}>
        <ScrollView 
          ref={scrollViewRef}
          style={styles.scrollView} 
          contentContainerStyle={styles.contentScroll}
          onScroll={handleScroll}
          onMomentumScrollEnd={handleScrollEnd}
          onScrollEndDrag={handleScrollEnd}
          scrollEventThrottle={16}
        >
          <ConfigFormSections onSectionLayout={onSectionLayout} />
        </ScrollView>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    flexDirection: 'row',
    height: '100%',
  },
  sidebar: {
    width: 200,
    borderRightWidth: 1,
    backgroundColor: '#F2F4F8',
    height: '100%',
  },
  sidebarItem: {
    paddingVertical: 8,
  },
  content: {
    flex: 1,
    backgroundColor: '#fff',
    overflow: 'hidden',
    minHeight: 0,
    minWidth: 0,
  },
  scrollView: {
    flex: 1,
  },
  contentScroll: {
    padding: 24,
  },
});
