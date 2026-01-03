import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  StyleProp,
  ViewStyle,
  TextStyle,
} from 'react-native';
import {
  TextInput,
  Text,
  useTheme,
  List,
  Portal,
  Dialog,
  Button,
  TextInputProps,
  IconButton
} from 'react-native-paper';
import { useDeviceType } from '../hooks/useDeviceType';
import InstantTooltip from './InstantTooltip';

export interface Md3InputProps extends Omit<TextInputProps, 'theme'> {
  label: string;
  labelStyle?: StyleProp<TextStyle>;
  containerStyle?: StyleProp<ViewStyle>;
  description?: string;
}

// ==========================================
// 1. PC 端组件
// ==========================================
const Md3InputPC: React.FC<Md3InputProps> = ({
  label,
  labelStyle,
  containerStyle,
  value,
  style,
  description,
  ...props
}) => {
  const theme = useTheme();

  return (
    <View style={[stylesPC.container, containerStyle]}>
      <View style={stylesPC.labelRow}>
        <Text
          variant="bodyMedium"
          style={[stylesPC.label, { color: theme.colors.onSurfaceVariant }, labelStyle]}
        >
          {label}
        </Text>

        {description && (
          <InstantTooltip content={description}>
            <IconButton
              icon="help-circle-outline"
              size={18}
              iconColor={theme.colors.onSurfaceVariant}
              style={stylesPC.helpIcon}
              rippleColor={'transparent'}
            />
          </InstantTooltip>
        )}
      </View>

      <TextInput
        {...props}
        value={value}
        mode="outlined"
        dense={true}
        label={undefined}
        style={[stylesPC.input, { backgroundColor: theme.colors.surface }, style]}
        contentStyle={stylesPC.inputContent}
        outlineStyle={{ borderRadius: 4 }}
      />
    </View>
  );
};

const stylesPC = StyleSheet.create({
  container: {
    zIndex: 1,
  },
  labelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
    zIndex: 2,
  },
  label: {
    fontSize: 13,
    marginLeft: 2,
  },
  helpIcon: {
    margin: 0,
    padding: 0,
    width: 24, // 增加触摸/hover热区大小，但图标本身保持 size={18}
    height: 24,
    marginLeft: 2,
  },
  input: {
    height: 36, // 稍微压扁一点，显得更像 Desktop UI
    fontSize: 13,
    zIndex: 1,
  },
  inputContent: {
    paddingVertical: 0,
    height: 36,
    textAlignVertical: 'center',
  },
});

// ==========================================
// 2. Mobile 端组件 (修正颜色)
// ==========================================
const Md3InputMobile: React.FC<Md3InputProps> = ({
  label,
  value,
  onChangeText,
  placeholder,
  description,
  ...props
}) => {
  const theme = useTheme();
  const [visible, setVisible] = useState(false);
  const [tempValue, setTempValue] = useState(value || '');

  useEffect(() => { setTempValue(value || ''); }, [value]);

  const showDialog = () => {
    setTempValue(value || '');
    setVisible(true);
  };
  const hideDialog = () => setVisible(false);
  const handleSave = () => {
    if (onChangeText) onChangeText(tempValue);
    hideDialog();
  };

  return (
    <>
      <List.Item
        title={label}
        description={value ? value : (placeholder || '未设置')}
        onPress={showDialog}
        titleStyle={{ fontSize: 16 }}
        
        descriptionStyle={{
          fontSize: 14,
          marginTop: 4,
          color: theme.colors.onSurfaceVariant
        }}
      />

      <Portal>
        <Dialog visible={visible} onDismiss={hideDialog} style={{ maxWidth: 400, alignSelf: 'center', width: '90%' }}>
          <Dialog.Title>{label}</Dialog.Title>
          <Dialog.Content>
            {description && (
              <Text
                variant="bodyMedium"
                style={{ color: theme.colors.onSurfaceVariant, marginBottom: 16, lineHeight: 20 }}
              >
                {description}
              </Text>
            )}
            <TextInput
              {...props}
              value={tempValue}
              onChangeText={setTempValue}
              mode="outlined"
              autoFocus
              placeholder={placeholder}
              style={{ backgroundColor: theme.colors.surface }}
            />
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={hideDialog}>取消</Button>
            <Button onPress={handleSave}>确定</Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </>
  );
};

// ==========================================
// 3. 主入口
// ==========================================
const Md3Input: React.FC<Md3InputProps> = (props) => {
  const { isMobile } = useDeviceType();
  if (isMobile) return <Md3InputMobile {...props} />;
  return <Md3InputPC {...props} />;
};

export default Md3Input;