import React from 'react';
import { StyleSheet } from 'react-native';
import { useFormContext, Controller } from 'react-hook-form';
import { SegmentedButtons } from 'react-native-paper';
import MD3SwitchItem from './MD3SwitchItem';
import MD3Input, { Md3InputProps } from './MD3Input';
import MD3MultiSelect, { SelectOption } from './MD3MultiSelect';

interface FormInputProps extends Omit<Md3InputProps, 'value' | 'onChangeText' | 'onBlur'> {
  name: string;
}

export const FormInput: React.FC<FormInputProps> = ({ name, label, ...props }) => {
  const { control } = useFormContext();
  return (
    <Controller
      control={control}
      name={name}
      render={({ field: { onChange, onBlur, value } }) => (
        <MD3Input
          label={label}
          value={value}
          onChangeText={onChange}
          onBlur={onBlur}
          mode="flat"
          style={{ marginBottom: 12, backgroundColor: 'transparent' }}
          {...props}
        />
      )}
    />
  );
};

interface FormSwitchProps {
  name: string;
  label: string;
  disabled?: boolean;
}

export const FormSwitch: React.FC<FormSwitchProps> = ({ name, label, disabled }) => {
  const { control } = useFormContext();
  return (
    <Controller
      control={control}
      name={name}
      render={({ field: { onChange, value } }) => {
        return (
          <MD3SwitchItem
            label={label}
            value={value}
            onValueChange={onChange}
            disabled={disabled}
            size="small"
          />
        );
      }}
    />
  );
};

type SegmentedButtonsButtons = React.ComponentProps<typeof SegmentedButtons>['buttons'];
type SegmentedButtonsStyle = React.ComponentProps<typeof SegmentedButtons>['style'];

interface FormSegmentedProps<T = any> {
  name: string;
  options: SelectOption<T>[];
  style?: SegmentedButtonsStyle;
  label?: string;
  description?: string;
}

export function FormSegmented<T = any>(props: FormSegmentedProps<T>) {
  const { name, options, style, label, description } = props;
  const { control } = useFormContext();
  return (
    <Controller
      control={control}
      name={name}
      render={({ field: { onChange, value } }) => (
        <MD3MultiSelect
          value={value}
          onValueChange={onChange}
          options={options}
          style={style}
          label={label}
          description={description}
        />
      )}
    />
  );
};

const styles = StyleSheet.create({
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 4,
    marginBottom: 4,
  },
  switchRowMobile: {
    justifyContent: 'space-between',
    paddingVertical: 10,
    marginBottom: 8,
  },
  switchLabel: {
    marginLeft: 12,
    fontSize: 14,
    flex: 1,
  },
  switchContainerMobile: {
    // scale up the switch visually on mobile
    transform: [{ scale: 1.35 }],
    alignSelf: 'center',
  },
  pressable: {
    borderRadius: 6,
  },
  pressableMobile: {
    borderRadius: 8,
  },
  pressed: {
    opacity: 0.85,
  },
});
