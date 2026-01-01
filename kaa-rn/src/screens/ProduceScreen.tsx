import React, { useState, useRef } from 'react';
import { View, StyleSheet, ScrollView, LayoutChangeEvent, NativeSyntheticEvent, NativeScrollEvent } from 'react-native';
import { Text, Card, Button, TextInput, IconButton, useTheme, List, SegmentedButtons } from 'react-native-paper';
import { useDeviceType } from '../hooks/useDeviceType';
import { MD3Switch } from '../components/MD3Switch';

// Mock data
const SCHEMES = ['ktn世一可', '会长 our chant', 'Test Scheme'];
const ACTIONS = ['推荐行动', '形象课程', '声乐课程', '舞蹈课程', '活动支援', '外出', '文化课', '休息', '咨询'];

const SECTIONS = [
  { id: 'basic', label: '基础', icon: 'card-account-details-outline' },
  { id: 'strategy', label: '策略', icon: 'playlist-check' },
  { id: 'automation', label: '自动化', icon: 'robot-outline' },
];

export const ProduceScreen = () => {
  const { isLargeScreen } = useDeviceType();
  const theme = useTheme();
  const [activeSection, setActiveSection] = useState('basic');
  
  const scrollViewRef = useRef<ScrollView>(null);
  const sectionPositions = useRef<{ [key: string]: number }>({});
  const isScrollingRef = useRef(false);

  // State
  const [scheme, setScheme] = useState(SCHEMES[0]);
  const [schemeName, setSchemeName] = useState('ktn世一可');
  const [schemeDesc, setSchemeDesc] = useState('两回 ことね 世界一可爱い私');
  const [mode, setMode] = useState('Pro');
  const [idol, setIdol] = useState('Kotone');
  
  // Switches
  const [switches, setSwitches] = useState({
    apDrink: false,
    skipComm: true,
    autoDeck: true,
    supportPt: false,
    noteBoost: false,
    rental: true,
  });

  const toggleSwitch = (key: keyof typeof switches) => {
    setSwitches(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // Action Priority List (Mock)
  const [actions, setActions] = useState(ACTIONS);

  const onSectionLayout = (id: string, event: LayoutChangeEvent) => {
    sectionPositions.current[id] = event.nativeEvent.layout.y;
  };

  const scrollToSection = (id: string) => {
    const y = sectionPositions.current[id];
    if (y !== undefined && scrollViewRef.current) {
      isScrollingRef.current = true;
      setActiveSection(id);
      scrollViewRef.current.scrollTo({ y, animated: true });
      setTimeout(() => {
        isScrollingRef.current = false;
      }, 500);
    }
  };

  const handleScroll = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    if (isScrollingRef.current) return;

    const scrollY = event.nativeEvent.contentOffset.y;
    const positions = sectionPositions.current;
    
    let currentSection = activeSection;

    for (const section of SECTIONS) {
      const pos = positions[section.id];
      if (pos !== undefined) {
        if (scrollY >= pos - 100) { // Buffer
           currentSection = section.id;
        }
      }
    }

    if (currentSection !== activeSection) {
      setActiveSection(currentSection);
    }
  };

  // Components
  const ConfigSwitch = ({ label, value, onChange, disabled }: { label: string, value: boolean, onChange: () => void, disabled?: boolean }) => (
    <View style={styles.switchRow}>
      <MD3Switch
        value={value}
        onValueChange={onChange}
        disabled={disabled}
        size="small"
      />
      <Text onPress={() => !disabled && onChange()} style={[styles.switchLabel, disabled && { opacity: 0.5 }]}>{label}</Text>
    </View>
  );

  const renderSchemeSelector = () => (
    <View style={styles.headerCard}>
      <View style={styles.schemeSelector}>
        <View style={{ flex: 1 }}>
            <TextInput
                mode="outlined"
                value={scheme}
                label="选择培育方案"
                right={<TextInput.Icon icon="chevron-down" />}
                editable={false}
                style={{ backgroundColor: 'white' }}
            />
        </View>
        <IconButton icon="plus" mode="contained" onPress={() => {}} />
        <IconButton icon="delete" mode="contained" containerColor={theme.colors.errorContainer} iconColor={theme.colors.error} onPress={() => {}} />
      </View>
    </View>
  );

  const renderBasicInfo = () => (
    <View style={styles.sectionContainer}>
      <Text variant="titleMedium" style={styles.sectionTitle}>基础信息</Text>
      <TextInput
        label="方案名称"
        value={schemeName}
        onChangeText={setSchemeName}
        mode="flat"
        style={styles.input}
        underlineColor="transparent"
      />
      <TextInput
        label="方案描述"
        value={schemeDesc}
        onChangeText={setSchemeDesc}
        mode="flat"
        multiline
        numberOfLines={3}
        style={styles.input}
        underlineColor="transparent"
      />
      
      <Text variant="titleMedium" style={styles.sectionTitle}>偶像设定</Text>
      <TextInput
          label="培育模式"
          value={mode}
          mode="flat"
          style={styles.input}
          right={<TextInput.Icon icon="chevron-down" />}
          underlineColor="transparent"
      />
        <TextInput
          label="选择偶像"
          value={idol}
          mode="flat"
          style={styles.input}
          right={<TextInput.Icon icon="chevron-down" />}
          underlineColor="transparent"
      />
    </View>
  );

  const renderStrategy = () => (
    <View style={styles.sectionContainer}>
      <Text variant="titleMedium" style={styles.sectionTitle}>行动优先级</Text>
      <Text variant="bodySmall" style={{marginBottom: 16, color: theme.colors.secondary}}>拖拽调整优先级 (Mock)</Text>
      <Card style={styles.card}>
        <Card.Content style={{padding: 0}}>
            {actions.map((action, index) => (
                <View key={action} style={[styles.actionItem, index === actions.length - 1 && { borderBottomWidth: 0 }]}>
                    <IconButton icon="menu" size={20} />
                    <Text style={{flex: 1}}>{action}</Text>
                </View>
            ))}
        </Card.Content>
      </Card>
    </View>
  );

  const renderAutomation = () => (
    <View style={styles.sectionContainer}>
        <Text variant="titleMedium" style={styles.sectionTitle}>道具使用</Text>
        <Card style={styles.card}>
            <Card.Content>
                <ConfigSwitch label="AP 饮料" value={switches.apDrink} onChange={() => toggleSwitch('apDrink')} />
                <ConfigSwitch label="支援强化 Pt" value={switches.supportPt} onChange={() => toggleSwitch('supportPt')} />
                <ConfigSwitch label="笔记数提升" value={switches.noteBoost} onChange={() => toggleSwitch('noteBoost')} />
            </Card.Content>
        </Card>

        <Text variant="titleMedium" style={styles.sectionTitle}>卡组与好友</Text>
        <Card style={styles.card}>
            <Card.Content>
                <ConfigSwitch label="自动编成" value={switches.autoDeck} onChange={() => toggleSwitch('autoDeck')} />
                {switches.autoDeck && <Text variant="bodySmall" style={{color: theme.colors.primary, marginLeft: 52, marginBottom: 8}}>目前只能自动编成支援卡...</Text>}
                <ConfigSwitch label="关注租借人" value={switches.rental} onChange={() => toggleSwitch('rental')} />
            </Card.Content>
        </Card>

        <Text variant="titleMedium" style={styles.sectionTitle}>系统行为</Text>
        <Card style={styles.card}>
            <Card.Content>
                <ConfigSwitch label="跳过交流" value={switches.skipComm} onChange={() => toggleSwitch('skipComm')} />
            </Card.Content>
        </Card>
    </View>
  );

  return (
    <View style={styles.container}>
        {/* Left Sidebar */}
        {isLargeScreen && (
            <View style={[styles.sidebar, { borderRightColor: theme.colors.outlineVariant }]}>
                <ScrollView>
                {SECTIONS.map((section) => {
                    const isActive = activeSection === section.id;
                    return (
                    <List.Item
                        key={section.id}
                        title={section.label}
                        left={props => <List.Icon {...props} icon={section.icon} color={isActive ? theme.colors.primary : props.color} />}
                        onPress={() => scrollToSection(section.id)}
                        style={[
                        styles.sidebarItem,
                        {
                            borderLeftWidth: 4,
                            borderLeftColor: isActive ? theme.colors.primary : 'transparent',
                            backgroundColor: isActive ? theme.colors.surfaceVariant : 'transparent',
                        }
                        ]}
                        titleStyle={isActive && {
                        color: theme.colors.primary,
                        fontWeight: 'bold',
                        }}
                    />
                    );
                })}
                </ScrollView>
            </View>
        )}

        {/* Right Content */}
        <View style={styles.content}>
            <View style={styles.contentHeader}>
                {renderSchemeSelector()}
            </View>
            
            <ScrollView 
                style={{ flex: 1 }} 
                contentContainerStyle={styles.contentScroll}
                ref={scrollViewRef}
                onScroll={handleScroll}
                scrollEventThrottle={16}
            >
                {!isLargeScreen && (
                     <View style={{marginBottom: 16}}>
                        <SegmentedButtons
                            value={activeSection}
                            onValueChange={(val) => scrollToSection(val)}
                            buttons={SECTIONS.map(s => ({ value: s.id, label: s.label, icon: s.icon }))}
                        />
                     </View>
                )}

                <View onLayout={(e) => onSectionLayout('basic', e)}>
                    {renderBasicInfo()}
                </View>
                <View onLayout={(e) => onSectionLayout('strategy', e)}>
                    {renderStrategy()}
                </View>
                <View onLayout={(e) => onSectionLayout('automation', e)}>
                    {renderAutomation()}
                </View>
                
                <View style={{height: 80}} /> 
            </ScrollView>

            {/* Floating Save Button */}
            <View style={[styles.fabContainer, { right: 32, bottom: 32 }]}>
                <Button 
                    mode="contained" 
                    icon="content-save" 
                    onPress={() => {}} 
                    style={{ borderRadius: 28 }} 
                    contentStyle={{ height: 48, paddingHorizontal: 16 }}
                >
                    保存培育方案
                </Button>
            </View>
        </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    flexDirection: 'row',
    backgroundColor: '#f5f5f5',
  },
  sidebar: {
    width: 200,
    borderRightWidth: 1,
    backgroundColor: '#f5f5f5',
    height: '100%',
  },
  sidebarItem: {
    paddingVertical: 8,
  },
  content: {
    flex: 1,
    backgroundColor: '#fff',
    display: 'flex',
    flexDirection: 'column',
  },
  contentHeader: {
    padding: 16,
    paddingBottom: 0,
    backgroundColor: '#fff',
  },
  contentScroll: {
    padding: 24,
  },
  headerCard: {
    marginBottom: 8,
  },
  schemeSelector: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  sectionContainer: {
    maxWidth: 800,
  },
  sectionTitle: {
    marginTop: 8,
    marginBottom: 16,
    fontWeight: 'bold',
  },
  card: {
    backgroundColor: 'white',
    marginBottom: 16,
    elevation: 1,
    borderWidth: 1,
    borderColor: '#eee',
  },
  input: {
    backgroundColor: '#fff',
    marginBottom: 12,
  },
  actionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
  },
  switchLabel: {
    marginLeft: 12,
    fontSize: 14,
    flex: 1,
  },
  fabContainer: {
    position: 'absolute',
  },
});
