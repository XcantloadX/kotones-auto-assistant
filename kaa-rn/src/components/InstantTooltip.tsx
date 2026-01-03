import React, { useEffect, useRef, useState } from 'react';
import {
  Animated,
  Easing,
  Platform,
  Pressable,
  StyleSheet,
  View,
} from 'react-native';
import { Text, useTheme } from 'react-native-paper';

export interface InstantTooltipProps {
  content: string;
  children: React.ReactNode;
}

// 优化版 Tooltip (PC)
// - 默认：内容自适应宽度 + maxWidth 限制
// - Web：用 width=max-content 避免绝对定位时被压成触发器宽度
const InstantTooltip: React.FC<InstantTooltipProps> = ({ content, children }) => {
  const theme = useTheme();
  const [visible, setVisible] = useState(false);
  const animValue = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(animValue, {
      toValue: visible ? 1 : 0,
      duration: visible ? 200 : 150,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: false,
    }).start();
  }, [animValue, visible]);

  const tooltipStyle = {
    opacity: animValue,
    transform: [
      { scale: animValue.interpolate({ inputRange: [0, 1], outputRange: [0.9, 1] }) },
      { translateX: animValue.interpolate({ inputRange: [0, 1], outputRange: [-5, 0] }) },
    ],
  };

  const bubbleWebStyle =
    Platform.OS === 'web'
      ? (
          {
            width: 'max-content',
          } as const
        )
      : undefined;

  return (
    <View style={styles.container}>
      <Pressable
        onHoverIn={() => setVisible(true)}
        onHoverOut={() => setVisible(false)}
        // @ts-expect-error: Web only style for cursor
        style={() => [styles.trigger, Platform.OS === 'web' && { cursor: 'help' }]}
      >
        {children}
      </Pressable>

      <Animated.View
        style={[
          styles.bubble,
          { backgroundColor: theme.colors.inverseSurface },
          bubbleWebStyle,
          tooltipStyle,
        ]}
        pointerEvents="none"
      >
        <Text variant="bodySmall" style={{ color: theme.colors.inverseOnSurface }}>
          {content}
        </Text>
      </Animated.View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'relative',
    zIndex: 100,
  },
  trigger: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  bubble: {
    position: 'absolute',
    left: 30,
    top: -6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 4,
    maxWidth: 400,
    zIndex: 99000,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
  },
});

export default InstantTooltip;
