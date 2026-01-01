import React, { useEffect, useRef } from 'react';
import { Pressable, Animated, Easing, ViewStyle } from 'react-native';
import { useTheme, Icon } from 'react-native-paper';

type Props = {
  value: boolean;
  onValueChange?: (val: boolean) => void;
  disabled?: boolean;
  size?: 'small' | 'medium';
  style?: ViewStyle;
};

export const MD3Switch = ({ value, onValueChange, disabled, size = 'medium', style }: Props) => {
  const theme = useTheme();
  const anim = useRef(new Animated.Value(value ? 1 : 0)).current;

  useEffect(() => {
    Animated.timing(anim, {
      toValue: value ? 1 : 0,
      duration: 200,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: false,
    }).start();
  }, [value]);

  const isSmall = size === 'small';

  // Dimensions
  const trackWidth = isSmall ? 36 : 52;
  const trackHeight = isSmall ? 22 : 32;
  const thumbSizeUnchecked = isSmall ? 12 : 16;
  const thumbSizeChecked = isSmall ? 18 : 24;
  const padding = isSmall ? 3 : 4; // Reduced padding for off state

  const trackOnColor = theme.colors.primary;
  const trackOffColor = theme.colors.surfaceVariant;
  const trackBorderColor = theme.colors.outline;
  const thumbOnColor = theme.colors.onPrimary;
  const thumbOffColor = theme.colors.outline;
  const checkIconColor = theme.colors.primary;

  const trackBackgroundColor = anim.interpolate({
    inputRange: [0, 1],
    outputRange: [trackOffColor, trackOnColor]
  });

  const trackBorderColorAnim = anim.interpolate({
    inputRange: [0, 1],
    outputRange: [trackBorderColor, trackOnColor]
  });

  const thumbColor = anim.interpolate({
    inputRange: [0, 1],
    outputRange: [thumbOffColor, thumbOnColor]
  });

  const currentThumbSize = anim.interpolate({
    inputRange: [0, 1],
    outputRange: [thumbSizeUnchecked, thumbSizeChecked]
  });
  
  const currentBorderRadius = anim.interpolate({
      inputRange: [0, 1],
      outputRange: [thumbSizeUnchecked / 2, thumbSizeChecked / 2]
  });

  // Calculate translation
  // Unchecked: Left = padding
  // Checked: Left = trackWidth - padding - thumbSizeChecked
  const translateXUnchecked = padding;
  const translateXChecked = trackWidth - padding - thumbSizeChecked;

  const translateX = anim.interpolate({
    inputRange: [0, 1],
    outputRange: [translateXUnchecked, translateXChecked]
  });

  return (
    <Pressable onPress={() => onValueChange && !disabled && onValueChange(!value)} disabled={disabled} style={style}>
      <Animated.View style={{
        width: trackWidth,
        height: trackHeight,
        borderRadius: trackHeight / 2,
        backgroundColor: trackBackgroundColor,
        borderWidth: 2,
        borderColor: trackBorderColorAnim,
        justifyContent: 'center',
        opacity: disabled ? 0.5 : 1
      }}>
        <Animated.View style={{
          width: currentThumbSize,
          height: currentThumbSize,
          borderRadius: currentBorderRadius,
          backgroundColor: thumbColor,
          transform: [{ translateX }],
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <Animated.View style={{ opacity: anim, transform: [{ scale: anim }] }}>
             <Icon source="check" size={isSmall ? 12 : 16} color={checkIconColor} />
          </Animated.View>
        </Animated.View>
      </Animated.View>
    </Pressable>
  );
};
