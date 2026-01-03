import React, { useEffect } from 'react';
export type DirtyFields = boolean | { [key: string]: DirtyFields };

export function extractDirtyValues(values: any, dirty: object): any | undefined {
  if (typeof dirty === 'boolean') return dirty ? values : undefined;
  if (!dirty || typeof dirty !== 'object') return undefined;
  const result: any = Array.isArray(values) ? [] : {};
  for (const key of Object.keys(dirty)) {
    const dv = (dirty as any)[key];
    const val = values ? values[key] : undefined;
    const extracted = extractDirtyValues(val, dv);
    if (extracted !== undefined) result[key] = extracted;
  }
  if (Array.isArray(result)) {
    return result.length ? result : undefined;
  }
  return Object.keys(result).length ? result : undefined;
}
import { View, StyleSheet, LayoutChangeEvent } from 'react-native';
import { Text } from 'react-native-paper';
import useConfigOptions from '../../hooks/useConfig';
import { useForm, FormProvider, useWatch, Controller } from 'react-hook-form';
import { FormInput, FormSwitch, FormSegmented } from '../../components/FormFields';
import MD3Input from '../../components/MD3Input';
import { ConfigFormData, isAndroidEmulator, EMULATOR_TYPES, ANDROID_EMULATOR_VALUES, SELECT_CONTESTANT_OPTIONS, CONTEST_WHEN_NO_SET_OPTIONS, FEVER_MONTH_OPTIONS, ASSIGNMENT_DURATION_OPTIONS, CLUB_REWARD_NOTE_OPTIONS } from './types';

type Props = {
  onSectionLayout: (id: string, event: LayoutChangeEvent) => void;
};

export const ConfigFormSections: React.FC<Props> = ({ onSectionLayout }) => {
  const config = useConfigOptions();
  const methods = useForm<ConfigFormData>({ mode: 'onBlur', values: config?.data,  });
  const control = methods.control;

  const enableStorePurchase = useWatch({ control, name: 'options.purchase.enabled' });
  const enableGoldPurchase = useWatch({ control, name: 'options.purchase.money_enabled' });
  const enableApPurchase = useWatch({ control, name: 'options.purchase.ap_enabled' });
  const enableWork = useWatch({ control, name: 'options.assignment.enabled' });
  const enableReassignMiniLive = useWatch({ control, name: 'options.assignment.mini_live_reassign_enabled' });
  const enableReassignOnlineLive = useWatch({ control, name: 'options.assignment.online_live_reassign_enabled' });
  const enableContest = useWatch({ control, name: 'options.contest.enabled' });
  const enableTraining = useWatch({ control, name: 'options.produce.enabled' });
  const enableIdle = useWatch({ control, name: 'options.idle.enabled' });
  const enableClubReward = useWatch({ control, name: 'options.club_reward.enabled' });
  const enableCapsuleToys = useWatch({ control, name: 'options.capsule_toys.enabled' });
  const emulatorType = useWatch({ control, name: 'backend.type' });
  const screenshotMethod = useWatch({ control, name: 'backend.screenshot_impl' });
  const autoLaunchGame = useWatch({ control, name: 'options.start_game.enabled' });

  const isAndroid = isAndroidEmulator(emulatorType);
  const isDmm = emulatorType === 'dmm';
  const isMuMu = emulatorType === 'mumu12' || emulatorType === 'mumu12v5';
  const showInstanceId = isMuMu || emulatorType === 'leidian';

  // Watch all values so effect runs on any change
  const allValues = useWatch({ control });

  // When backend options load, reset the form options to match
  React.useEffect(() => {
    if (!config.data) return;
    // Backend returns UserConfig[BaseConfig] shape: { backend, keep_screenshots, options, ... }
    methods.reset(config.data);
  }, [config.data, methods]);

  const onSave = async (dirtyValues: any, currentValues: any) => {
    try {
      await config.patchOptions.mutateAsync(dirtyValues);
      // methods.reset(currentValues);
    } catch (e) {
      console.error('Auto-save failed', e);
    }
  };

  const parseCsvTokens = (text: string): string[] => {
    return text
      .split(/[\n,，]/g)
      .map(t => t.trim())
      .filter(Boolean);
  };

  const dailyMoneyItemLabelByValue: Record<number, string> = {
    [-1]: '所有推荐商品',
    0: '课程笔记',
    1: '老手笔记',
    2: '支援强化点数',
    3: '感性笔记（声乐）',
    4: '感性笔记（舞蹈）',
    5: '感性笔记（形象）',
    6: '理性笔记（声乐）',
    7: '理性笔记（舞蹈）',
    8: '理性笔记（形象）',
    9: '非凡笔记（声乐）',
    10: '非凡笔记（舞蹈）',
    11: '非凡笔记（形象）',
    12: '重新挑战券',
    13: '记录钥匙',
    14: '倉本千奈 WonderScale 碎片',
    15: '篠泽广 光景 碎片',
    16: '紫云清夏 Tame-Lie-One-Step 碎片',
    17: '葛城リーリヤ 白線 碎片',
    18: '姫崎薪波 clumsy trick 碎片',
    19: '花海咲季 FightingMyWay 碎片',
    20: '藤田ことね 世界一可愛い私 碎片',
    21: '花海佑芽 The Rolling Riceball 碎片',
    22: '月村手毬 Luna say maybe 碎片',
    23: '有村麻央 Fluorite 碎片',
  };

  const dailyMoneyItemValueByToken: Record<string, number> = Object.fromEntries(
    Object.entries(dailyMoneyItemLabelByValue).map(([k, v]) => [v.replace(/\s+/g, ''), Number(k)])
  );

  const parseDailyMoneyItems = (text: string): number[] => {
    const tokens = parseCsvTokens(text);
    const values: number[] = [];
    for (const rawToken of tokens) {
      const token = rawToken.replace(/\s+/g, '');
      const asInt = /^-?\d+$/.test(token) ? Number(token) : undefined;
      const val = asInt !== undefined ? asInt : dailyMoneyItemValueByToken[token];
      if (typeof val === 'number' && Number.isFinite(val)) {
        values.push(val);
      }
    }
    // de-dupe while keeping order
    return Array.from(new Set(values));
  };

  const apItemLabelByValue: Record<number, string> = {
    0: '获取支援强化 Pt 提升',
    1: '获取笔记数提升',
    2: '再挑战券',
    3: '回忆再生成券',
  };
  const apItemValueByToken: Record<string, number> = Object.fromEntries(
    Object.entries(apItemLabelByValue).map(([k, v]) => [v.replace(/\s+/g, ''), Number(k)])
  );
  const parseApItems = (text: string): number[] => {
    const tokens = parseCsvTokens(text);
    const values: number[] = [];
    for (const rawToken of tokens) {
      const token = rawToken.replace(/\s+/g, '');
      const asInt = /^\d+$/.test(token) ? Number(token) : undefined;
      const val = asInt !== undefined ? asInt : apItemValueByToken[token];
      if (typeof val === 'number' && val >= 0 && val <= 3) {
        values.push(val);
      }
    }
    return Array.from(new Set(values));
  };

  // Auto-save: debounce changes and save only when there are dirty fields.
  useEffect(() => {
    const dirty = extractDirtyValues(allValues, methods.formState.dirtyFields);
    if (!dirty) return;

    const timer = setTimeout(() => {
      onSave(dirty, allValues);
    }, 800);

    return () => clearTimeout(timer);
  }, [allValues, methods.formState.dirtyFields]);

  return (
    <FormProvider {...methods}>
      {/* Basic Settings */}
      <View style={styles.formContainer} onLayout={(e) => { onSectionLayout('basic', e); onSectionLayout('basic_emulator', e); }}>
        <Text variant="titleMedium" style={styles.sectionTitle}>模拟器设置</Text>
        <FormSegmented name="backend.type" options={EMULATOR_TYPES} style={styles.segmentedButton} label="模拟器类型" />
        <FormSegmented
          name="backend.screenshot_impl"
          options={(() => {
            if (emulatorType === 'dmm') {
              return [
                { value: 'windows', label: 'windows' },
                { value: 'remote_windows', label: 'remote_windows' },
              ];
            }
            if (emulatorType === 'mumu12' || emulatorType === 'mumu12v5') {
              return [
                { value: 'adb', label: 'adb' },
                { value: 'adb_raw', label: 'adb_raw' },
                { value: 'uiautomator2', label: 'uiautomator2' },
                { value: 'nemu_ipc', label: 'nemu_ipc' },
              ];
            }
            if (emulatorType && ANDROID_EMULATOR_VALUES.includes(emulatorType)) {
              return [
                { value: 'adb', label: 'adb' },
                { value: 'adb_raw', label: 'adb_raw' },
                { value: 'uiautomator2', label: 'uiautomator2' },
              ];
            }
            return [
              { value: 'adb', label: 'adb' },
              { value: 'adb_raw', label: 'adb_raw' },
              { value: 'uiautomator2', label: 'uiautomator2' },
            ];
          })()}
          style={styles.segmentedButton}
          label="截图方法"
          description="必须与当前模拟器类型匹配，否则后端会拒绝保存。"
        />
        <FormInput name="backend.target_screenshot_interval" label="最小截图间隔 (秒)" keyboardType="numeric" description="设置截图的最小时间间隔，单位为秒。通常无需修改。建议值为低于 0.2 秒。" />
        
        {showInstanceId && (
          <View>
            <FormInput name="backend.instance_id" label="多开实例 ID" />
            {isMuMu && (
              <FormSwitch name="backend.mumu_background_mode" label="MuMu 模拟器后台保活模式" />
            )}
          </View>
        )}

        {emulatorType === 'custom' && (
          <View>
            <FormInput name="backend.adb_ip" label="ADB IP 地址" />
            <FormInput name="backend.adb_port" label="ADB 端口" keyboardType="numeric" />
          </View>
        )}

        {isDmm && (
          <FormInput name="options.start_game.dmm_game_path" label="DMM 版游戏路径 (可选)" />
        )}

        {screenshotMethod && emulatorType === 'dmm' && screenshotMethod !== 'windows' && screenshotMethod !== 'remote_windows' && (
          <Text variant="bodySmall" style={styles.noteText}>DMM 版仅支持 windows / remote_windows。</Text>
        )}
      </View>

      <View style={styles.formContainer} onLayout={(e) => onSectionLayout('basic_launch', e)}>
        <Text variant="titleMedium" style={styles.sectionTitle}>启动游戏设置</Text>
        <FormSwitch name="options.start_game.enabled" label="启用自动启动游戏" />
        {autoLaunchGame && (
          <>
            {isDmm && (
              <>
                <FormSwitch name="options.start_game.disable_gakumas_localify" label="自动禁用 Gakumas Localify 汉化" />
                <FormSwitch name="options.start_game.dmm_bypass" label="跳过 DMM 启动器" />
              </>
            )}
            {isAndroid && (
              <>
                <FormSwitch name="backend.check_emulator" label="自动启动模拟器" />
                <FormSwitch name="options.start_game.start_through_kuyo" label="通过Kuyo来启动游戏" />
                <FormInput name="options.start_game.game_package_name" label="游戏包名" />
                <FormInput name="options.start_game.kuyo_package_name" label="Kuyo 包名" />
                <FormInput name="backend.emulator_path" label="模拟器 exe 文件路径" />
                <FormInput name="backend.adb_emulator_name" label="ADB 模拟器名称" />
                <FormInput name="backend.emulator_args" label="模拟器启动参数" />
              </>
            )}
          </>
        )}
      </View>

      <View style={styles.formContainer} onLayout={(e) => onSectionLayout('basic_after', e)}>
        <Text variant="titleMedium" style={styles.sectionTitle}>全部任务结束后</Text>
        <Text variant="bodySmall" style={styles.noteText}>注: 执行单个任务不会触发下面这些，只有状态页的启动按钮才会触发</Text>
        <FormSwitch name="options.end_game.exit_kaa" label="退出 kaa" />
        <FormSwitch name="options.end_game.kill_game" label="关闭游戏" />
        <FormSwitch name="options.end_game.kill_dmm" label="关闭 DMMGamePlayer" />
        <FormSwitch name="options.end_game.kill_emulator" label="关闭模拟器" />
        <FormSwitch name="options.end_game.shutdown" label="关闭系统" />
        <FormSwitch name="options.end_game.hibernate" label="休眠系统" />
        <FormSwitch name="options.end_game.restore_gakumas_localify" label="恢复 Gakumas Localify 汉化状态" />
      </View>
      
      {/* Daily Settings */}
      <View style={styles.formContainer} onLayout={(e) => { onSectionLayout('daily', e); onSectionLayout('daily_store', e); }}>
        <Text variant="titleMedium" style={styles.sectionTitle}>商店购买设置</Text>
        <FormSwitch name="options.purchase.enabled" label="启用商店购买" />
        {enableStorePurchase && (
          <View>
            <FormSwitch name="options.purchase.money_enabled" label="启用金币购买" />
            {enableGoldPurchase && (
              <Controller
                control={control}
                name="options.purchase.money_items"
                render={({ field: { onChange, onBlur, value } }) => {
                  const arr = Array.isArray(value) ? value : [];
                  const display = arr
                    .map((v) => dailyMoneyItemLabelByValue[Number(v)] ?? String(v))
                    .join(', ');
                  return (
                    <MD3Input
                      label="金币商店购买物品"
                      value={display}
                      onChangeText={(text) => onChange(parseDailyMoneyItems(text))}
                      onBlur={onBlur}
                      mode="flat"
                      multiline
                      description="支持输入：中文名称或数字 ID（逗号/换行分隔）。例如：所有推荐商品, 非凡笔记（形象） 或 -1, 11"
                      style={{ marginBottom: 12, backgroundColor: 'transparent' }}
                    />
                  );
                }}
              />
            )}
            <FormSwitch name="options.purchase.money_refresh" label="每日一次免费刷新金币商店" />
            <FormSwitch name="options.purchase.ap_enabled" label="启用AP购买" />
            {enableApPurchase && (
              <Controller
                control={control}
                name="options.purchase.ap_items"
                render={({ field: { onChange, onBlur, value } }) => {
                  const arr = Array.isArray(value) ? value : [];
                  const display = arr
                    .map((v) => apItemLabelByValue[Number(v)] ?? String(v))
                    .join(', ');
                  return (
                    <MD3Input
                      label="AP 商店购买物品"
                      value={display}
                      onChangeText={(text) => onChange(parseApItems(text))}
                      onBlur={onBlur}
                      mode="flat"
                      multiline
                      description="启用 AP 购买时必须填写。可输入数字 0-3 或中文名称（逗号/换行分隔）。"
                      style={{ marginBottom: 12, backgroundColor: 'transparent' }}
                    />
                  );
                }}
              />
            )}
            <FormSwitch name="options.purchase.weekly_enabled" label="启用每周免费礼包购买" />
          </View>
        )}
      </View>

      <View style={styles.formContainer} onLayout={(e) => onSectionLayout('daily_work', e)}>
        <Text variant="titleMedium" style={styles.sectionTitle}>工作设置</Text>
        <FormSwitch name="options.assignment.enabled" label="启用工作" />
        {enableWork && (
          <View>
            <FormSwitch name="options.assignment.mini_live_reassign_enabled" label="启用重新分配 MiniLive" />
            {enableReassignMiniLive && (
              <FormSegmented<number>
                name="options.assignment.mini_live_duration"
                options={ASSIGNMENT_DURATION_OPTIONS}
                style={styles.segmentedButton}
                label="MiniLive 工作时长"
              />
            )}
            <FormSwitch name="options.assignment.online_live_reassign_enabled" label="启用重新分配 OnlineLive" />
            {enableReassignOnlineLive && (
              <FormSegmented<number>
                name="options.assignment.online_live_duration"
                options={ASSIGNMENT_DURATION_OPTIONS}
                style={styles.segmentedButton}
                label="OnlineLive 工作时长"
              />
            )}
          </View>
        )}
      </View>

      <View style={styles.formContainer} onLayout={(e) => onSectionLayout('daily_contest', e)}>
        <Text variant="titleMedium" style={styles.sectionTitle}>竞赛设置</Text>
        <FormSwitch name="options.contest.enabled" label="启用竞赛" />
        {enableContest && (
          <View>
            <FormSegmented<number>
              name="options.contest.select_which_contestant"
              options={SELECT_CONTESTANT_OPTIONS}
              style={styles.segmentedButton}
              label="选择第几位挑战者"
            />
            <FormSegmented
              name="options.contest.when_no_set"
              options={CONTEST_WHEN_NO_SET_OPTIONS}
              style={styles.segmentedButton}
              label="竞赛队伍未编成时"
            />
          </View>
        )}
      </View>

      <View style={styles.formContainer} onLayout={(e) => onSectionLayout('daily_rewards', e)}>
        <Text variant="titleMedium" style={styles.sectionTitle}>奖励领取设置</Text>
        <FormSwitch name="options.mission_reward.enabled" label="领取任务奖励" />
        <FormSwitch name="options.club_reward.enabled" label="领取社团奖励" />
        {/* 社团奖励：后端需要一个笔记枚举值 */}
        {enableClubReward && (
          <FormSegmented<number>
            name="options.club_reward.selected_note"
            options={CLUB_REWARD_NOTE_OPTIONS}
            style={styles.segmentedButton}
            label="社团奖励笔记偏好"
            description="只在启用社团奖励时生效。"
          />
        )}
        <FormSwitch name="options.presents.enabled" label="收取礼物" />
        <FormSwitch name="options.activity_funds.enabled" label="收取活动费" />

        <FormSwitch name="options.upgrade_support_card.enabled" label="支援卡升级" />
        <FormSwitch name="options.capsule_toys.enabled" label="扭蛋机" />
        {enableCapsuleToys && (
          <View>
            <FormInput name="options.capsule_toys.friend_capsule_toys_count" label="好友扭蛋机次数" keyboardType="numeric" />
            <FormInput name="options.capsule_toys.sense_capsule_toys_count" label="感性扭蛋机次数" keyboardType="numeric" />
            <FormInput name="options.capsule_toys.logic_capsule_toys_count" label="理性扭蛋机次数" keyboardType="numeric" />
            <FormInput name="options.capsule_toys.anomaly_capsule_toys_count" label="非凡扭蛋机次数" keyboardType="numeric" />
          </View>
        )}
      </View>
      

      {/* Training Settings */}
      <View style={styles.formContainer} onLayout={(e) => onSectionLayout('training', e)}>
        <Text variant="titleMedium" style={styles.sectionTitle}>培育设置</Text>
        <FormSwitch name="options.produce.enabled" label="启用培育" />
        {enableTraining && (
          <View>
            <FormInput name="options.produce.selected_solution_id" label="当前使用的培育方案" />
            <FormInput name="options.produce.produce_count" label="培育次数" keyboardType="numeric" />
            <FormInput name="options.produce.produce_timeout_cd" label="推荐卡检测用时上限" keyboardType="numeric" />
            <FormInput name="options.produce.interrupt_timeout" label="检测超时时间" keyboardType="numeric" />
            <FormSegmented
              name="options.produce.enable_fever_month"
              options={FEVER_MONTH_OPTIONS}
              style={styles.segmentedButton}
              label="培育活动模式"
            />
          </View>
        )}
      </View>
      

      {/* Misc Settings */}
      <View style={styles.formContainer} onLayout={(e) => { onSectionLayout('misc', e); onSectionLayout('misc_general', e); }}>
        <Text variant="titleMedium" style={styles.sectionTitle}>杂项设置</Text>
        <FormSegmented name="options.misc.check_update" options={[{ value: 'never', label: '从不' }, { value: 'startup', label: '启动时' }]} style={styles.segmentedButton} label="检查更新时机" />
        <FormSwitch name="options.misc.auto_install_update" label="自动安装更新" />
        <FormSwitch name="options.misc.expose_to_lan" label="允许局域网访问 Web 界面" />
        <FormSegmented name="options.misc.update_channel" options={[{ value: 'release', label: '稳定版' }, { value: 'beta', label: '测试版' }]} style={styles.segmentedButton} label="更新通道" />
        <FormSegmented name="options.misc.log_level" options={[{ value: 'debug', label: '普通' }, { value: 'verbose', label: '详细' }]} style={styles.segmentedButton} label="日志等级" />
      </View>

      <View style={styles.formContainer} onLayout={(e) => onSectionLayout('misc_idle', e)}>
        <Text variant="titleMedium" style={styles.sectionTitle}>闲置挂机设置</Text>
        <FormSwitch name="options.idle.enabled" label="启用闲置挂机" />
        {enableIdle && (
          <View>
            <FormInput name="options.idle.idle_seconds" label="闲置秒数" keyboardType="numeric" />
            <FormSwitch name="options.idle.minimize_on_pause" label="按键暂停时最小化窗口" />
          </View>
        )}
      </View>

      <View style={styles.formContainer} onLayout={(e) => onSectionLayout('misc_debug', e)}>
        <Text variant="titleMedium" style={styles.sectionTitle}>调试设置</Text>
        <Text style={{color: 'red', marginBottom: 8}}>仅供调试使用。正常运行时务必关闭下面所有的选项。</Text>
        <FormSwitch name="keep_screenshots" label="保留截图数据" />
        <FormSwitch name="options.trace.recommend_card_detection" label="跟踪推荐卡检测" />
      </View>
      
    </FormProvider>
  );
};

const styles = StyleSheet.create({
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
    // maxWidth: '100%',
    width: 'auto',
    flexGrow: 0
  },
  noteText: {
    marginBottom: 12,
    color: '#666',
    fontStyle: 'italic',
  },
});
