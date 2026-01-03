import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import {
  List,
  Portal,
  Dialog,
  RadioButton,
  Button,
  Text,
  SegmentedButtons,
  useTheme,
  IconButton,
} from 'react-native-paper';
import { useDeviceType } from '../hooks/useDeviceType';
import InstantTooltip from './InstantTooltip';

type SegmentedButtonsStyle = React.ComponentProps<typeof SegmentedButtons>['style'];

export interface SelectOption<T = any> {
  value: T;
  label: string;
}

interface MD3MultiSelectProps<T = any> {
  label?: string;
  description?: string;
  value?: T | null;
  onValueChange?: (v: T) => void;
  options: SelectOption<T>[];
  style?: SegmentedButtonsStyle;
  placeholder?: string;
}

const MD3MultiSelect: React.FC<MD3MultiSelectProps> = ({
  label,
  description,
  value,
  onValueChange,
  options,
  style,
  placeholder = '未设置',
}) => {
  const { isMobile } = useDeviceType();
  const [visible, setVisible] = useState(false);
  const theme = useTheme();

  const selectedButton = options?.find(o => o.value === value as string);
  const selectedLabel = selectedButton ? (selectedButton.label ?? selectedButton.value) : undefined;

  if (!isMobile) {
    let descriptionNode: React.ReactNode = null;
    if (description) {
      if (label) {
        descriptionNode = (
          <InstantTooltip content={description}>
            <IconButton
              icon="help-circle-outline"
              size={18}
              iconColor={theme.colors.onSurfaceVariant}
              style={styles.helpIcon}
              rippleColor={'transparent'}
            />
          </InstantTooltip>
        );
      } else {
        descriptionNode = (
          <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 6 }}>
            {description}
          </Text>
        );
      }
    }

    return (
      <View style={[{ marginBottom: 8 }, styles.container, style as any]}>
        {label ? (
          <View style={styles.labelRow}>
            <Text variant="bodyMedium" style={[styles.label, { color: theme.colors.onSurfaceVariant }]}>
              {label}
            </Text>
            {descriptionNode}
          </View>
        ) : (
          descriptionNode
        )}
        <SegmentedButtons
          value={value}
          onValueChange={v => onValueChange && onValueChange(v)}
          buttons={options}
          style={{}}
        />
      </View>
    );
  }
  else {
    // Mobile: show a List.Item that opens a dialog with Radio buttons
    return (
      <>
        <List.Item
          title={label}
          description={selectedLabel ? String(selectedLabel) : placeholder}
          onPress={() => setVisible(true)}
          titleStyle={{ fontSize: 16 }}
          descriptionStyle={{ marginTop: 4 }}
        />

        <Portal>
          <Dialog visible={visible} onDismiss={() => setVisible(false)} style={{ maxWidth: 420, alignSelf: 'center', width: '92%' }}>
            {label && <Dialog.Title>{label}</Dialog.Title>}
            <Dialog.Content>
              {description && (
                <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 8 }}>
                  {description}
                </Text>
              )}

              <RadioButton.Group
                onValueChange={v => {
                  onValueChange && onValueChange(v);
                  setVisible(false);
                }}
                value={value ?? ''}
              >
                {options.map((o, idx) => (
                  <RadioButton.Item
                    key={String(o.value) + idx}
                    label={typeof o.label === 'string' ? o.label : String(o.value)}
                    value={o.value}
                  />
                ))}
              </RadioButton.Group>
            </Dialog.Content>
            <Dialog.Actions>
              <Button onPress={() => setVisible(false)}>取消</Button>
            </Dialog.Actions>
          </Dialog>
        </Portal>
      </>
    );
  }
};

const styles = StyleSheet.create({
  // desktop label container
  container: {
    marginBottom: 8,
  },
  labelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  label: {
    fontSize: 13,
    marginLeft: 2,
  },
  helpIcon: {
    margin: 0,
    padding: 0,
    width: 24,
    height: 24,
    marginLeft: 2,
  },
});

export default MD3MultiSelect;
