import React from 'react';
import { View, StyleSheet, Linking, TouchableOpacity } from 'react-native';
import { Text } from 'react-native-paper';
import Constants from 'expo-constants';

export const AboutScreen = () => {
  const version = Constants.expoConfig?.version || '1.0.0';

  const openLink = (url: string) => {
    Linking.openURL(url).catch(err => console.error("Couldn't load page", err));
  };

  return (
    <View style={styles.container}>
      <Text variant="headlineLarge" style={styles.title}>
        琴音小助手 v{version}
      </Text>
      
      <Text variant="titleMedium" style={styles.subtitle}>
        Powered by kotonebot
      </Text>
      
      <Text variant="bodyMedium" style={styles.license}>
        以 GPLv3 协议开源
      </Text>

      <View style={styles.linksContainer}>
        <TouchableOpacity onPress={() => openLink('https://space.bilibili.com/3546393396263062')}>
          <Text variant="titleMedium" style={styles.link}>Bilibili</Text>
        </TouchableOpacity>
        
        <TouchableOpacity onPress={() => openLink('https://github.com/kotonebot/KotonesAutoAssistant')}>
          <Text variant="titleMedium" style={styles.link}>Github</Text>
        </TouchableOpacity>
        
        <TouchableOpacity onPress={() => openLink('https://qm.qq.com/q/8K0Z0Z0Z0Z')}>
           <Text variant="titleMedium" style={styles.link}>QQ群</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  title: {
    color: '#1A1A1A',
    fontWeight: 'bold',
    marginBottom: 16,
  },
  subtitle: {
    color: '#666666',
    marginBottom: 4,
  },
  license: {
    color: '#666666',
    marginBottom: 48,
  },
  linksContainer: {
    flexDirection: 'row',
    gap: 40,
  },
  link: {
    color: '#1A1A1A',
    fontWeight: 'bold',
  },
});
