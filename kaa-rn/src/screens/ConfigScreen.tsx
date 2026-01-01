import React, { useState, useRef } from 'react';
import { View, StyleSheet, ScrollView, LayoutChangeEvent, NativeSyntheticEvent, NativeScrollEvent } from 'react-native';
import { Text, List, Divider, TextInput, Checkbox, RadioButton, Button, SegmentedButtons, useTheme } from 'react-native-paper';
import { useForm, Controller, useWatch } from 'react-hook-form';
import { MD3Switch } from '../components/MD3Switch';

const SETTINGS_SECTIONS = [
  {
    id: 'basic',
    label: '基本',
    icon: 'cog',
    children: [
      { id: 'basic_emulator', label: '模拟器设置' },
      { id: 'basic_launch', label: '启动游戏设置' },
      { id: 'basic_after', label: '任务结束设置' },
    ]
  },
  {
    id: 'daily',
    label: '日常',
    icon: 'calendar-check',
    children: [
      { id: 'daily_store', label: '商店购买设置' },
      { id: 'daily_work', label: '工作设置' },
      { id: 'daily_contest', label: '竞赛设置' },
      { id: 'daily_rewards', label: '奖励领取设置' },
    ]
  },
  { id: 'training', label: '培育', icon: 'school' },
  {
    id: 'misc',
    label: '杂项',
    icon: 'dots-horizontal',
    children: [
      { id: 'misc_general', label: '通用设置' },
      { id: 'misc_idle', label: '闲置挂机设置' },
      { id: 'misc_debug', label: '调试设置' },
    ]
  },
];

const EMULATOR_TYPES = [
  { value: 'mumu12v4', label: 'MuMu 12 v4.x' },
  { value: 'mumu12v5', label: 'MuMu 12 v5.x' },
  { value: 'ldplayer', label: '雷电' },
  { value: 'custom', label: '自定义' },
  { value: 'dmm', label: 'DMM' },
];

type FormData = {
  // Basic
  emulatorType: string;
  screenshotMethod: string;
  minScreenshotInterval: string;
  autoLaunchGame: boolean;
  autoDisableLocalify: boolean;
  dmmGamePath: string;
  skipDmmLauncher: boolean;
  autoLaunchEmulator: boolean;
  launchViaKuyo: boolean;
  gamePackageName: string;
  emulatorExePath: string;
  adbEmulatorName: string;
  emulatorLaunchArgs: string;
  exitKaa: boolean;
  closeGame: boolean;
  closeDmmPlayer: boolean;
  closeEmulator: boolean;
  closeSystem: boolean;
  hibernateSystem: boolean;
  restoreLocalify: boolean;

  // Daily
  enableStorePurchase: boolean;
  enableGoldPurchase: boolean;
  goldStoreItems: string;
  dailyFreeRefresh: boolean;
  enableApPurchase: boolean;
  enableWeeklyGift: boolean;
  enableWork: boolean;
  enableReassignMiniLive: boolean;
  miniLiveDuration: string;
  enableReassignOnlineLive: boolean;
  onlineLiveDuration: string;
  enableContest: boolean;
  contestChallengers: string;
  contestTeamNotFormedAction: string;
  collectMissionRewards: boolean;
  collectCircleRewards: boolean;
  collectGifts: boolean;
  collectEventRewards: boolean;

  // Training
  enableTraining: boolean;
  trainingPlan: string;
  trainingCount: string;
  cardDetectionLimit: string;
  detectionTimeout: string;
  preTrainingActivityMode: string;

  // Misc
  checkUpdateTiming: string;
  autoInstallUpdate: boolean;
  allowLanAccess: boolean;
  updateChannel: string;
  logLevel: string;
  enableIdle: boolean;
  idleSeconds: string;
  minimizeOnPause: boolean;
  keepScreenshotData: boolean;
  trackCardDetection: boolean;
};

const componentStyles = StyleSheet.create({
  checkboxRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 4,
    marginBottom: 4,
  },
  checkboxLabel: {
    marginLeft: 12,
    fontSize: 14,
  },
  input: {
    marginBottom: 12,
    backgroundColor: 'transparent',
  },
});

const ConfigSwitch = ({ label, value, onChange, disabled }: { label: string, value: boolean, onChange: (val: boolean) => void, disabled?: boolean }) => (
  <View style={componentStyles.checkboxRow}>
    <MD3Switch
      value={value}
      onValueChange={onChange}
      disabled={disabled}
      size="small"
    />
    <Text onPress={() => !disabled && onChange(!value)} style={[componentStyles.checkboxLabel, disabled && { opacity: 0.5 }]}>{label}</Text>
  </View>
);

const ConfigInput = ({ label, value, onChange, style, ...props }: any) => (
  <TextInput
    label={label}
    value={value}
    onChangeText={onChange}
    mode="flat"
    style={[componentStyles.input, style]}
    {...props}
  />
);

export const ConfigScreen = () => {
  const [activeSection, setActiveSection] = useState('basic');
  const theme = useTheme();
  const scrollViewRef = useRef<ScrollView>(null);
  const sectionPositions = useRef<{ [key: string]: number }>({});
  const isScrollingRef = useRef(false);

  const { control, watch } = useForm<FormData>({
    defaultValues: {
      // Basic
      emulatorType: 'dmm',
      screenshotMethod: 'windows',
      minScreenshotInterval: '0.1',
      autoLaunchGame: true,
      autoDisableLocalify: true,
      dmmGamePath: 'F:\\Games\\gakumas\\gakumas.exe',
      skipDmmLauncher: true,
      autoLaunchEmulator: true,
      launchViaKuyo: false,
      gamePackageName: 'com.bandainamcoent.idolmaster_gakuen',
      emulatorExePath: 'F:\\Apps\\Netease\\MuMuPlayer-12.0\\shell\\MuMuPlayer.exe',
      adbEmulatorName: '',
      emulatorLaunchArgs: '',
      exitKaa: false,
      closeGame: false,
      closeDmmPlayer: false,
      closeEmulator: false,
      closeSystem: false,
      hibernateSystem: false,
      restoreLocalify: true,

      // Daily
      enableStorePurchase: true,
      enableGoldPurchase: true,
      goldStoreItems: '所有推荐商品, 感性笔记 (声乐)',
      dailyFreeRefresh: true,
      enableApPurchase: false,
      enableWeeklyGift: false,
      enableWork: true,
      enableReassignMiniLive: true,
      miniLiveDuration: '12',
      enableReassignOnlineLive: true,
      onlineLiveDuration: '12',
      enableContest: true,
      contestChallengers: '3',
      contestTeamNotFormedAction: 'notify_skip',
      collectMissionRewards: true,
      collectCircleRewards: false,
      collectGifts: true,
      collectEventRewards: true,

      // TrainingSwitch
      enableTraining: true,
      trainingPlan: '会长 our chant - 无描述',
      trainingCount: '7',
      cardDetectionLimit: '30',
      detectionTimeout: '90',
      preTrainingActivityMode: 'none',

      // Misc
      checkUpdateTiming: 'startup',
      autoInstallUpdate: false,
      allowLanAccess: false,
      updateChannel: 'stable',
      logLevel: 'normal',
      enableIdle: true,
      idleSeconds: '30',
      minimizeOnPause: true,
      keepScreenshotData: false,
      trackCardDetection: false,
    }
  });

  const enableStorePurchase = watch('enableStorePurchase');
  const enableWork = watch('enableWork');
  const enableContest = watch('enableContest');
  const enableTraining = watch('enableTraining');
  const enableIdle = watch('enableIdle');

  const onSectionLayout = (id: string, event: LayoutChangeEvent) => {
    sectionPositions.current[id] = event.nativeEvent.layout.y;
  };

  const scrollToSection = (id: string) => {
    const y = sectionPositions.current[id];
    if (y !== undefined && scrollViewRef.current) {
      isScrollingRef.current = true;
      setActiveSection(id);
      scrollViewRef.current.scrollTo({ y, animated: true });
      // Reset scrolling flag after animation
      setTimeout(() => {
        isScrollingRef.current = false;
      }, 500);
    }
  };

  const handleScroll = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    if (isScrollingRef.current) return;

    const scrollY = event.nativeEvent.contentOffset.y;
    const positions = sectionPositions.current;
    
    // Find the section that is currently in view
    let currentSection = activeSection;
    let minDistance = Infinity;

    // Flatten all sections and subsections to check against
    const allSectionIds: string[] = [];
    SETTINGS_SECTIONS.forEach(section => {
      allSectionIds.push(section.id);
      if (section.children) {
        section.children.forEach(child => allSectionIds.push(child.id));
      }
    });

    for (const id of allSectionIds) {
      const pos = positions[id];
      if (pos !== undefined) {
        // Check if we passed this section
        if (scrollY >= pos - 50) { // 50px buffer
           // We want the last section that satisfies this condition
           currentSection = id;
        }
      }
    }

    if (currentSection !== activeSection) {
      setActiveSection(currentSection);
    }
  };

  const renderBasicSettings = () => {
    return (
    <>
      <View style={styles.formContainer} onLayout={(e) => { onSectionLayout('basic', e); onSectionLayout('basic_emulator', e); }}>
          <Text variant="titleMedium" style={styles.sectionTitle}>模拟器设置</Text>
          <Controller
            control={control}
            name="emulatorType"
            render={({ field: { onChange, value } }) => (
              <SegmentedButtons
                value={value}
                onValueChange={onChange}
                buttons={EMULATOR_TYPES}
                style={styles.segmentedButton}
              />
            )}
          />
          <Controller
            control={control}
            name="emulatorType"
            render={({ field: { value } }) => (
              <Text style={styles.helperText}>已选中 {EMULATOR_TYPES.find(e => e.value === value)?.label}</Text>
            )}
          />

          <Controller
            control={control}
            name="screenshotMethod"
            render={({ field: { value } }) => (
              <ConfigInput
                label="截图方法"
                value={value}
                right={<TextInput.Icon icon="menu-down" />}
                editable={false}
              />
            )}
          />
          <Controller
            control={control}
            name="minScreenshotInterval"
            render={({ field: { onChange, value } }) => (
              <ConfigInput
                label="最小截图间隔 (秒)"
                value={value}
                onChange={onChange}
                keyboardType="numeric"
              />
            )}
          />
      </View>

      <View style={styles.formContainer} onLayout={(e) => onSectionLayout('basic_launch', e)}>
          <Text variant="titleMedium" style={styles.sectionTitle}>启动游戏设置</Text>
          <Controller
            control={control}
            name="autoLaunchGame"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="启用自动启动游戏" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="autoDisableLocalify"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="自动禁用 Gakumas Localify 汉化" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="dmmGamePath"
            render={({ field: { onChange, value } }) => (
              <ConfigInput
                label="DMM 版游戏路径 (可选)"
                value={value}
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="skipDmmLauncher"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="跳过 DMM 启动器" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="autoLaunchEmulator"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="自动启动模拟器" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="launchViaKuyo"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="通过Kuyo来启动游戏" 
                value={value} 
                onChange={onChange}
                disabled={true}
              />
            )}
          />
          <Controller
            control={control}
            name="gamePackageName"
            render={({ field: { onChange, value } }) => (
              <ConfigInput
                label="游戏包名"
                value={value}
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="emulatorExePath"
            render={({ field: { onChange, value } }) => (
              <ConfigInput
                label="模拟器 exe 文件路径"
                value={value}
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="adbEmulatorName"
            render={({ field: { onChange, value } }) => (
              <ConfigInput
                label="ADB 模拟器名称"
                value={value}
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="emulatorLaunchArgs"
            render={({ field: { onChange, value } }) => (
              <ConfigInput
                label="模拟器启动参数"
                value={value}
                onChange={onChange}
              />
            )}
          />
      </View>

      <View style={styles.formContainer} onLayout={(e) => onSectionLayout('basic_after', e)}>
          <Text variant="titleMedium" style={styles.sectionTitle}>全部任务结束后</Text>
          <Text variant="bodySmall" style={styles.noteText}>注: 执行单个任务不会触发下面这些，只有状态页的启动按钮才会触发</Text>
          
          <Controller
            control={control}
            name="exitKaa"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="退出 kaa" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="closeGame"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="关闭游戏" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="closeDmmPlayer"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="关闭 DMMGamePlayer" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="closeEmulator"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="关闭模拟器" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="closeSystem"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="关闭系统" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="hibernateSystem"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="休眠系统" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="restoreLocalify"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="恢复 Gakumas Localify 汉化状态" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
      </View>
      
      <View style={{height: 50}} />
    </>
  )};

  const renderDailySettings = () => {
    return (
    <>
      <View style={styles.formContainer} onLayout={(e) => { onSectionLayout('daily', e); onSectionLayout('daily_store', e); }}>
          <Text variant="titleMedium" style={styles.sectionTitle}>商店购买设置</Text>
          <Controller
            control={control}
            name="enableStorePurchase"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="启用商店购买" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          
          {enableStorePurchase && (
            <View>
              <Controller
                control={control}
                name="enableGoldPurchase"
                render={({ field: { onChange, value } }) => (
                  <ConfigSwitch 
                    label="启用金币购买" 
                    value={value} 
                    onChange={onChange}
                  />
                )}
              />
              <Controller
                control={control}
                name="goldStoreItems"
                render={({ field: { onChange, value } }) => (
                  <ConfigInput
                    label="金币商店购买物品 (逗号分隔)"
                    value={value}
                    onChange={onChange}
                    multiline
                  />
                )}
              />
              <Controller
                control={control}
                name="dailyFreeRefresh"
                render={({ field: { onChange, value } }) => (
                  <ConfigSwitch 
                    label="每日一次免费刷新金币商店" 
                    value={value} 
                    onChange={onChange}
                  />
                )}
              />
              <Controller
                control={control}
                name="enableApPurchase"
                render={({ field: { onChange, value } }) => (
                  <ConfigSwitch 
                    label="启用AP购买" 
                    value={value} 
                    onChange={onChange}
                  />
                )}
              />
              <Controller
                control={control}
                name="enableWeeklyGift"
                render={({ field: { onChange, value } }) => (
                  <ConfigSwitch 
                    label="启用每周免费礼包购买" 
                    value={value} 
                    onChange={onChange}
                  />
                )}
              />
            </View>
          )}
      </View>

      <View style={styles.formContainer} onLayout={(e) => onSectionLayout('daily_work', e)}>
          <Text variant="titleMedium" style={styles.sectionTitle}>工作设置</Text>
          <Controller
            control={control}
            name="enableWork"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="启用工作" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          
          {enableWork && (
            <View>
              <Controller
                control={control}
                name="enableReassignMiniLive"
                render={({ field: { onChange, value } }) => (
                  <ConfigSwitch 
                    label="启用重新分配 MiniLive" 
                    value={value} 
                    onChange={onChange}
                  />
                )}
              />
              <Controller
                control={control}
                name="miniLiveDuration"
                render={({ field: { onChange, value } }) => (
                  <ConfigInput
                    label="MiniLive 工作时长"
                    value={value}
                    onChange={onChange}
                    keyboardType="numeric"
                  />
                )}
              />
              <Controller
                control={control}
                name="enableReassignOnlineLive"
                render={({ field: { onChange, value } }) => (
                  <ConfigSwitch 
                    label="启用重新分配 OnlineLive" 
                    value={value} 
                    onChange={onChange}
                  />
                )}
              />
              <Controller
                control={control}
                name="onlineLiveDuration"
                render={({ field: { onChange, value } }) => (
                  <ConfigInput
                    label="OnlineLive 工作时长"
                    value={value}
                    onChange={onChange}
                    keyboardType="numeric"
                  />
                )}
              />
            </View>
          )}
      </View>

      <View style={styles.formContainer} onLayout={(e) => onSectionLayout('daily_contest', e)}>
          <Text variant="titleMedium" style={styles.sectionTitle}>竞赛设置</Text>
          <Controller
            control={control}
            name="enableContest"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="启用竞赛" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          
          {enableContest && (
            <View>
              <Controller
                control={control}
                name="contestChallengers"
                render={({ field: { onChange, value } }) => (
                  <ConfigInput
                    label="选择第几个挑战者"
                    value={value}
                    onChange={onChange}
                    keyboardType="numeric"
                  />
                )}
              />
              <Text style={{marginBottom: 8}}>竞赛队伍未编成时</Text>
              <Controller
                control={control}
                name="contestTeamNotFormedAction"
                render={({ field: { onChange, value } }) => (
                  <SegmentedButtons
                    value={value}
                    onValueChange={onChange}
                    buttons={[
                      { value: 'notify_skip', label: '通知我并跳过' },
                      { value: 'stop', label: '停止' },
                    ]}
                    style={styles.segmentedButton}
                  />
                )}
              />
            </View>
          )}
      </View>

      <View style={styles.formContainer} onLayout={(e) => onSectionLayout('daily_rewards', e)}>
          <Text variant="titleMedium" style={styles.sectionTitle}>奖励领取设置</Text>
          <Controller
            control={control}
            name="collectMissionRewards"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="领取任务奖励" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="collectCircleRewards"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="领取社团奖励" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="collectGifts"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="收取礼物" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="collectEventRewards"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="收取活动费" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
      </View>
      <View style={{height: 50}} />
    </>
  )};

  const renderTrainingSettings = () => (
    <View style={styles.formContainer} onLayout={(e) => onSectionLayout('training', e)}>
      <Text variant="titleMedium" style={styles.sectionTitle}>培育设置</Text>
      <Controller
        control={control}
        name="enableTraining"
        render={({ field: { onChange, value } }) => (
          <ConfigSwitch 
            label="启用培育" 
            value={value} 
            onChange={onChange}
          />
        )}
      />
      
      {enableTraining && (
        <View>
          <Controller
            control={control}
            name="trainingPlan"
            render={({ field: { onChange, value } }) => (
              <ConfigInput
                label="当前使用的培育方案"
                value={value}
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="trainingCount"
            render={({ field: { onChange, value } }) => (
              <ConfigInput
                label="培育次数"
                value={value}
                onChange={onChange}
                keyboardType="numeric"
              />
            )}
          />
          <Controller
            control={control}
            name="cardDetectionLimit"
            render={({ field: { onChange, value } }) => (
              <ConfigInput
                label="推荐卡检测用时上限"
                value={value}
                onChange={onChange}
                keyboardType="numeric"
              />
            )}
          />
          <Controller
            control={control}
            name="detectionTimeout"
            render={({ field: { onChange, value } }) => (
              <ConfigInput
                label="检测超时时间"
                value={value}
                onChange={onChange}
                keyboardType="numeric"
              />
            )}
          />

          <Text variant="titleMedium" style={styles.sectionTitle}>培育前开启活动模式</Text>
          <Text variant="bodySmall" style={styles.noteText}>某些活动期间，在选择培育模式/难度页面的切换活动开关</Text>
          <Controller
            control={control}
            name="preTrainingActivityMode"
            render={({ field: { onChange, value } }) => (
              <RadioButton.Group onValueChange={onChange} value={value}>
                <View style={{flexDirection: 'row', alignItems: 'center'}}>
                  <RadioButton.Item label="不操作" value="none" />
                  <RadioButton.Item label="自动启用" value="enable" />
                  <RadioButton.Item label="自动禁用" value="disable" />
                </View>
              </RadioButton.Group>
            )}
          />
        </View>
      )}
      <View style={{height: 50}} />
    </View>
  );

  const renderMiscSettings = () => {
    return (
    <>
      <View style={styles.formContainer} onLayout={(e) => { onSectionLayout('misc', e); onSectionLayout('misc_general', e); }}>
          <Text variant="titleMedium" style={styles.sectionTitle}>杂项设置</Text>
          
          <Text style={{marginBottom: 8, fontWeight: 'bold'}}>检查更新时机</Text>
          <Controller
            control={control}
            name="checkUpdateTiming"
            render={({ field: { onChange, value } }) => (
              <RadioButton.Group onValueChange={onChange} value={value}>
                <View style={{flexDirection: 'row', alignItems: 'center'}}>
                  <RadioButton.Item label="从不" value="never" />
                  <RadioButton.Item label="启动时" value="startup" />
                </View>
              </RadioButton.Group>
            )}
          />

          <Controller
            control={control}
            name="autoInstallUpdate"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="自动安装更新" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="allowLanAccess"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="允许局域网访问 Web 界面" 
                value={value} 
                onChange={onChange}
              />
            )}
          />

          <Text style={{marginBottom: 8, marginTop: 16, fontWeight: 'bold'}}>更新通道</Text>
          <Controller
            control={control}
            name="updateChannel"
            render={({ field: { onChange, value } }) => (
              <RadioButton.Group onValueChange={onChange} value={value}>
                <View style={{flexDirection: 'row', alignItems: 'center'}}>
                  <RadioButton.Item label="稳定版" value="stable" />
                  <RadioButton.Item label="测试版" value="beta" />
                </View>
              </RadioButton.Group>
            )}
          />

          <Text style={{marginBottom: 8, marginTop: 16, fontWeight: 'bold'}}>日志等级</Text>
          <Controller
            control={control}
            name="logLevel"
            render={({ field: { onChange, value } }) => (
              <RadioButton.Group onValueChange={onChange} value={value}>
                <View style={{flexDirection: 'row', alignItems: 'center'}}>
                  <RadioButton.Item label="普通" value="normal" />
                  <RadioButton.Item label="详细" value="detailed" />
                </View>
              </RadioButton.Group>
            )}
          />
      </View>

      <View style={styles.formContainer} onLayout={(e) => onSectionLayout('misc_idle', e)}>
          <Text variant="titleMedium" style={styles.sectionTitle}>闲置挂机设置</Text>
          <Controller
            control={control}
            name="enableIdle"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="启用闲置挂机" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          
          {enableIdle && (
            <View>
              <Controller
                control={control}
                name="idleSeconds"
                render={({ field: { onChange, value } }) => (
                  <ConfigInput
                    label="闲置秒数"
                    value={value}
                    onChange={onChange}
                    keyboardType="numeric"
                  />
                )}
              />
              <Controller
                control={control}
                name="minimizeOnPause"
                render={({ field: { onChange, value } }) => (
                  <ConfigSwitch 
                    label="按键暂停时最小化窗口" 
                    value={value} 
                    onChange={onChange}
                  />
                )}
              />
            </View>
          )}
      </View>

      <View style={styles.formContainer} onLayout={(e) => onSectionLayout('misc_debug', e)}>
          <Text variant="titleMedium" style={styles.sectionTitle}>调试设置</Text>
          <Text style={{color: 'red', marginBottom: 8}}>仅供调试使用。正常运行时务必关闭下面所有的选项。</Text>
          <Controller
            control={control}
            name="keepScreenshotData"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="保留截图数据" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="trackCardDetection"
            render={({ field: { onChange, value } }) => (
              <ConfigSwitch 
                label="跟踪推荐卡检测" 
                value={value} 
                onChange={onChange}
              />
            )}
          />
      </View>
      <View style={{height: 50}} />
    </>
  )};

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
          style={{ flex: 1 }} 
          contentContainerStyle={styles.contentScroll}
          onScroll={handleScroll}
          scrollEventThrottle={16}
        >
          {renderBasicSettings()}
          {renderDailySettings()}
          {renderTrainingSettings()}
          {renderMiscSettings()}
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
    backgroundColor: '#f5f5f5',
    height: '100%',
  },
  sidebarItem: {
    paddingVertical: 8,
  },
  content: {
    flex: 1,
    backgroundColor: '#fff',
    overflow: 'hidden',
    height: '100%',
    minHeight: 0,
    minWidth: 0,
    display: 'flex',
    flexDirection: 'column',
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
