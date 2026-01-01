import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import { MainScreen } from '../screens/MainScreen';

const Stack = createStackNavigator();

export default function AppNavigator() {
  return (
    <Stack.Navigator screenOptions={{
      headerShown: false, cardStyle: {
        flex: 1
      }
    }}>
      <Stack.Screen name="Main" component={MainScreen} />
    </Stack.Navigator>
  );
}
