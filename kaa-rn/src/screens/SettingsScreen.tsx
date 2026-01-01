import React, { useState } from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { Text, List, Divider, TextInput, Checkbox, RadioButton, Button, SegmentedButtons, useTheme } from 'react-native-paper';

const SETTINGS_SECTIONS = [
  { id: 'basic', label: '基本', icon: 'cog' },
  { id: 'daily', label: '日常', icon: 'calendar-check' },
  { id: 'training', label: '培育', icon: 'school' },
  { id: 'misc', label: '杂项', icon: 'dots-horizontal' },
];

const EMULATOR_TYPES = [
  { value: 'mumu12v4', label: 'MuMu 12 v4.x' },
  { value: 'mumu12v5', label: 'MuMu 12 v5.x' },
  { value: 'ldplayer', label: '雷电' },
  { value: 'custom', label: '自定义' },
  { value: 'dmm', label: 'DMM' },
];

export const SettingsScreen = () => {
  const [activeSection, setActiveSection] = useState('basic');
  const theme = useTheme();

  // Form State (Basic Settings)
  const [emulatorType, setEmulatorType] = useState('dmm');
  const [screenshotMethod, setScreenshotMethod] = useState('windows');
  const [minScreenshotInterval, setMinScreenshotInterval] = useState('0.1');
  
  // Game Launch Settings
  const [autoLaunchGame, setAutoLaunchGame] = useState(true);
  const [autoDisableLocalify, setAutoDisableLocalify] = useState(true);
  const [dmmGamePath, setDmmGamePath] = useState('F:\\Games\\gakumas\\gakumas.exe');
  const [skipDmmLauncher, setSkipDmmLauncher] = useState(true);
  const [autoLaunchEmulator, setAutoLaunchEmulator] = useState(true);
  const [launchViaKuyo, setLaunchViaKuyo] = useState(false);
  const [gamePackageName, setGamePackageName] = useState('com.bandainamcoent.idolmaster_gakuen');
  const [emulatorExePath, setEmulatorExePath] = useState('F:\\Apps\\Netease\\MuMuPlayer-12.0\\shell\\MuMuPlayer.exe');
  const [adbEmulatorName, setAdbEmulatorName] = useState('');
  const [emulatorLaunchArgs, setEmulatorLaunchArgs] = useState('');

  // After Tasks
  const [exitKaa, setExitKaa] = useState(false);
  const [closeGame, setCloseGame] = useState(false);
  const [closeDmmPlayer, setCloseDmmPlayer] = useState(false);
  const [closeEmulator, setCloseEmulator] = useState(false);
  const [closeSystem, setCloseSystem] = useState(false);
  const [hibernateSystem, setHibernateSystem] = useState(false);
  const [restoreLocalify, setRestoreLocalify] = useState(true);

  const renderBasicSettings = () => (
    <View style={styles.formContainer}>
      <Text variant="headlineMedium" style={styles.pageTitle}>设置</Text>
      <Text variant="bodyMedium" style={styles.pageSubtitle}>设置修改后将自动保存并即时生效。</Text>
      <Divider style={styles.divider} />

      <Text variant="titleMedium" style={styles.sectionTitle}>模拟器设置</Text>
      <SegmentedButtons
        value={emulatorType}
        onValueChange={setEmulatorType}
        buttons={EMULATOR_TYPES}
        style={styles.segmentedButton}
      />
      <Text style={styles.helperText}>已选中 {EMULATOR_TYPES.find(e => e.value === emulatorType)?.label}</Text>

      <TextInput
        label="截图方法"
        value={screenshotMethod}
        mode="outlined"
        style={styles.input}
        right={<TextInput.Icon icon="menu-down" />}
        editable={false}
      />
      <TextInput
        label="最小截图间隔 (秒)"
        value={minScreenshotInterval}
        onChangeText={setMinScreenshotInterval}
        mode="outlined"
        style={styles.input}
        keyboardType="numeric"
      />

      <Text variant="titleMedium" style={styles.sectionTitle}>启动游戏设置</Text>
      <Checkbox.Item 
        label="启用自动启动游戏" 
        status={autoLaunchGame ? 'checked' : 'unchecked'} 
        onPress={() => setAutoLaunchGame(!autoLaunchGame)}
        position="leading"
        labelStyle={styles.checkboxLabel}
      />
      <Checkbox.Item 
        label="自动禁用 Gakumas Localify 汉化" 
        status={autoDisableLocalify ? 'checked' : 'unchecked'} 
        onPress={() => setAutoDisableLocalify(!autoDisableLocalify)}
        position="leading"
        labelStyle={styles.checkboxLabel}
      />
      <TextInput
        label="DMM 版游戏路径 (可选)"
        value={dmmGamePath}
        onChangeText={setDmmGamePath}
        mode="outlined"
        style={styles.input}
      />
      <Checkbox.Item 
        label="跳过 DMM 启动器" 
        status={skipDmmLauncher ? 'checked' : 'unchecked'} 
        onPress={() => setSkipDmmLauncher(!skipDmmLauncher)}
        position="leading"
        labelStyle={styles.checkboxLabel}
      />
      <Checkbox.Item 
        label="自动启动模拟器" 
        status={autoLaunchEmulator ? 'checked' : 'unchecked'} 
        onPress={() => setAutoLaunchEmulator(!autoLaunchEmulator)}
        position="leading"
        labelStyle={styles.checkboxLabel}
      />
      <Checkbox.Item 
        label="通过Kuyo来启动游戏" 
        status={launchViaKuyo ? 'checked' : 'unchecked'} 
        onPress={() => setLaunchViaKuyo(!launchViaKuyo)}
        position="leading"
        labelStyle={styles.checkboxLabel}
        disabled={true} // Looks disabled in screenshot
      />
      <TextInput
        label="游戏包名"
        value={gamePackageName}
        onChangeText={setGamePackageName}
        mode="outlined"
        style={styles.input}
      />
      <TextInput
        label="模拟器 exe 文件路径"
        value={emulatorExePath}
        onChangeText={setEmulatorExePath}
        mode="outlined"
        style={styles.input}
      />
      <TextInput
        label="ADB 模拟器名称"
        value={adbEmulatorName}
        onChangeText={setAdbEmulatorName}
        mode="outlined"
        style={styles.input}
      />
      <TextInput
        label="模拟器启动参数"
        value={emulatorLaunchArgs}
        onChangeText={setEmulatorLaunchArgs}
        mode="outlined"
        style={styles.input}
      />

      <Text variant="titleMedium" style={styles.sectionTitle}>全部任务结束后</Text>
      <Text variant="bodySmall" style={styles.noteText}>注: 执行单个任务不会触发下面这些，只有状态页的启动按钮才会触发</Text>
      
      <Checkbox.Item 
        label="退出 kaa" 
        status={exitKaa ? 'checked' : 'unchecked'} 
        onPress={() => setExitKaa(!exitKaa)}
        position="leading"
        labelStyle={styles.checkboxLabel}
      />
      <Checkbox.Item 
        label="关闭游戏" 
        status={closeGame ? 'checked' : 'unchecked'} 
        onPress={() => setCloseGame(!closeGame)}
        position="leading"
        labelStyle={styles.checkboxLabel}
      />
      <Checkbox.Item 
        label="关闭 DMMGamePlayer" 
        status={closeDmmPlayer ? 'checked' : 'unchecked'} 
        onPress={() => setCloseDmmPlayer(!closeDmmPlayer)}
        position="leading"
        labelStyle={styles.checkboxLabel}
      />
      <Checkbox.Item 
        label="关闭模拟器" 
        status={closeEmulator ? 'checked' : 'unchecked'} 
        onPress={() => setCloseEmulator(!closeEmulator)}
        position="leading"
        labelStyle={styles.checkboxLabel}
      />
      <Checkbox.Item 
        label="关闭系统" 
        status={closeSystem ? 'checked' : 'unchecked'} 
        onPress={() => setCloseSystem(!closeSystem)}
        position="leading"
        labelStyle={styles.checkboxLabel}
      />
      <Checkbox.Item 
        label="休眠系统" 
        status={hibernateSystem ? 'checked' : 'unchecked'} 
        onPress={() => setHibernateSystem(!hibernateSystem)}
        position="leading"
        labelStyle={styles.checkboxLabel}
      />
      <Checkbox.Item 
        label="恢复 Gakumas Localify 汉化状态" 
        status={restoreLocalify ? 'checked' : 'unchecked'} 
        onPress={() => setRestoreLocalify(!restoreLocalify)}
        position="leading"
        labelStyle={styles.checkboxLabel}
      />
      
      <View style={{height: 50}} />
    </View>
  );

  return (
    <View style={styles.container}>
      {/* Left Sidebar */}
      <View style={[styles.sidebar, { borderRightColor: theme.colors.outlineVariant }]}>
        <ScrollView>
          {SETTINGS_SECTIONS.map((section) => (
            <List.Item
              key={section.id}
              title={section.label}
              left={props => <List.Icon {...props} icon={section.icon} />}
              onPress={() => setActiveSection(section.id)}
              style={[
                styles.sidebarItem,
                activeSection === section.id && { backgroundColor: theme.colors.secondaryContainer }
              ]}
              titleStyle={activeSection === section.id && { color: theme.colors.onSecondaryContainer }}
            />
          ))}
        </ScrollView>
      </View>

      {/* Right Content */}
      <View style={styles.content}>
        <ScrollView contentContainerStyle={styles.contentScroll}>
          {activeSection === 'basic' ? renderBasicSettings() : (
            <View style={styles.placeholder}>
              <Text>Content for {SETTINGS_SECTIONS.find(s => s.id === activeSection)?.label}</Text>
            </View>
          )}
        </ScrollView>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    flexDirection: 'row',
  },
  sidebar: {
    width: 200,
    borderRightWidth: 1,
    backgroundColor: '#f5f5f5',
  },
  sidebarItem: {
    paddingVertical: 8,
  },
  content: {
    flex: 1,
    backgroundColor: '#fff',
  },
  contentScroll: {
    padding: 24,
  },
  formContainer: {
    maxWidth: 800,
  },
  sectionTitle: {
    marginTop: 24,
    marginBottom: 16,
    fontWeight: 'bold',
  },
  pageTitle: {
    marginBottom: 8,
    fontWeight: 'bold',
  },
  pageSubtitle: {
    marginBottom: 16,
    color: '#666',
  },
  divider: {
    marginBottom: 24,
  },
  segmentedButton: {
    marginBottom: 8,
  },
  helperText: {
    marginBottom: 16,
    fontSize: 12,
    color: '#666',
  },
  input: {
    marginBottom: 12,
    backgroundColor: '#fff',
  },
  checkboxLabel: {
    textAlign: 'left',
  },
  noteText: {
    marginBottom: 12,
    color: '#666',
    fontStyle: 'italic',
  },
  placeholder: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
});
