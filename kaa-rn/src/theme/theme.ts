import { MD3LightTheme as DefaultTheme } from 'react-native-paper';

export const theme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: '#FF9800', // Orange
    onPrimary: '#FFFFFF',
    primaryContainer: '#FFE0B2',
    onPrimaryContainer: '#E65100',
    secondary: '#FFC107', // Amber
    onSecondary: '#000000',
    secondaryContainer: '#FFECB3',
    onSecondaryContainer: '#FF6F00',
    background: '#F5F5F5',
    surface: '#FFFFFF',
    surfaceVariant: '#FFFFFF',
    onSurface: '#333333',
    elevation: {
        level0: 'transparent',
        level1: '#FFFFFF',
        level2: '#FFFFFF',
        level3: '#FFFFFF',
        level4: '#FFFFFF',
        level5: '#FFFFFF',
    }
  },
};
