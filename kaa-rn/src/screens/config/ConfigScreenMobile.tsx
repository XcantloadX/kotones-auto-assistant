import React from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { Chip } from 'react-native-paper';
import { useScrollSpy } from '../../hooks/useScrollSpy';
import { SETTINGS_SECTIONS, ConfigFormData } from './types';
import { ConfigFormSections } from './ConfigFormSections';

export const ConfigScreenMobile: React.FC = () => {
  const allSectionIds = SETTINGS_SECTIONS.flatMap(s => [s.id, ...(s.children?.map(c => c.id) || [])]);
  const { activeSection, scrollViewRef, onSectionLayout, scrollToSection, handleScroll, handleScrollEnd } = useScrollSpy(allSectionIds);

  return (
    <View style={styles.container}>
      {/* Mobile Tabs */}
      <ScrollView 
        horizontal 
        showsHorizontalScrollIndicator={false}
        style={styles.tabsContainer}
        contentContainerStyle={styles.tabsContent}
      >
        {SETTINGS_SECTIONS.map((section) => (
          <Chip
            key={section.id}
            mode={activeSection === section.id || (section.children && section.children.some(c => c.id === activeSection)) ? 'flat' : 'outlined'}
            selected={activeSection === section.id || (section.children && section.children.some(c => c.id === activeSection))}
            onPress={() => scrollToSection(section.id)}
            style={styles.tabChip}
            icon={section.icon}
          >
            {section.label}
          </Chip>
        ))}
      </ScrollView>

      {/* Content */}
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
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    flexDirection: 'column',
    height: '100%',
  },
  tabsContainer: {
    maxHeight: 56,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
    backgroundColor: '#fff',
  },
  tabsContent: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    alignItems: 'center',
  },
  tabChip: {
    marginRight: 8,
    height: 36,
  },
  scrollView: {
    flex: 1,
  },
  contentScroll: {
    padding: 24,
  },
});
