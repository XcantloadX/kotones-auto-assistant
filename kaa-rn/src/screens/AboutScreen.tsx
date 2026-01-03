import React from 'react';
import { View, StyleSheet, Linking, TouchableOpacity } from 'react-native';
import { Text, Surface, IconButton } from 'react-native-paper';
import Constants from 'expo-constants';
import useBackendVersion from '../hooks/useBackendVersion';
import { useDeviceType } from '../hooks/useDeviceType';

export const AboutScreen = () => {
  const { data: version } = useBackendVersion();
  const { isMobile } = useDeviceType();
  const isNarrow = isMobile;

  const openLink = (url: string) => {
    Linking.openURL(url).catch(err => console.error("Couldn't load page", err));
  };

  const onFeedbackPress = () => {
    openLink('https://github.com/kotonebot/KotonesAutoAssistant/issues');
  };

  const onUpdatePress = () => {
    openLink('https://github.com/kotonebot/KotonesAutoAssistant/releases');
  };

  return (
    <View style={[styles.container, isNarrow && styles.containerNarrow]}>
      <Text variant="headlineLarge" style={styles.title}>
        琴音小助手 {version ? `v${version}` : ''}
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

      <View style={[styles.surfacesContainer, isNarrow && styles.surfacesContainerNarrow]}>
        <Surface style={[styles.surface, isNarrow && styles.surfaceNarrow]}>
          <TouchableOpacity onPress={onFeedbackPress} style={styles.surfaceTouchable}>
            <IconButton icon="message-outline" size={28} />
            <Text variant="titleMedium" style={styles.surfaceLabel}>反馈</Text>
          </TouchableOpacity>
        </Surface>

        <Surface style={[styles.surface, isNarrow && styles.surfaceNarrow]}>
          <TouchableOpacity onPress={onUpdatePress} style={styles.surfaceTouchable}>
            <IconButton icon="update" size={28} />
            <Text variant="titleMedium" style={styles.surfaceLabel}>更新</Text>
          </TouchableOpacity>
        </Surface>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'flex-start',
    alignItems: 'center',
    backgroundColor: '#fff',
    paddingTop: 120,
  },
  title: {
    color: '#1A1A1A',
    fontWeight: 'bold',
    marginBottom: 16,
    textAlign: 'center',
    alignSelf: 'center',
    maxWidth: '95%',
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
  surfacesContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 32,
  },
  surface: {
    width: 220,
    height: 88,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 8,
    elevation: 2,
    borderRadius: 6,
    marginHorizontal: 24,
  },
  surfaceTouchable: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  surfaceLabel: {
    fontWeight: 'bold',
  },
  surfacesContainerNarrow: {
    flexDirection: 'column',
    alignItems: 'center',
    width: '100%',
  },
  surfaceNarrow: {
    alignSelf: 'center',
    width: '90%',
    marginVertical: 12,
  },
  containerNarrow: {
    paddingTop: 40,
  },
});
