import { useState, useRef } from 'react';
import { ScrollView, LayoutChangeEvent, NativeSyntheticEvent, NativeScrollEvent } from 'react-native';

export const useScrollSpy = (sectionIds: string[]) => {
  const [activeSection, setActiveSection] = useState(sectionIds[0]);
  const scrollViewRef = useRef<ScrollView>(null);
  const sectionPositions = useRef<{ [key: string]: number }>({});
  const isScrollingRef = useRef(false);
  const targetSectionRef = useRef<string | null>(null);
  const scrollTimeoutRef = useRef<number | null>(null);

  // 注册锚点位置（单层函数：onSectionLayout(id, event)）
  const onSectionLayout = (id: string, event: LayoutChangeEvent) => {
    sectionPositions.current[id] = event.nativeEvent.layout.y;
  };

  const findCurrentSectionByScroll = (scrollY: number) => {
    let current = sectionIds[0];
    for (const id of sectionIds) {
      const pos = sectionPositions.current[id];
      if (pos !== undefined && scrollY >= pos - 100) {
        current = id;
      }
    }
    return current;
  };

  // 点击侧边栏跳转 — 标记目标 section，并在滚动结束时才更新 active
  const scrollToSection = (id: string) => {
    const y = sectionPositions.current[id];
    if (y !== undefined && scrollViewRef.current) {
      // 清除之前的 timeout
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
      
      isScrollingRef.current = true;
      targetSectionRef.current = id;
      // 先乐观性地 setActiveSection 为目标（界面立即反馈），但在滚动过程中不要被 handleScroll 覆盖
      setActiveSection(id);
      scrollViewRef.current.scrollTo({ y, animated: true });
      
      // Fallback timeout for Web or platforms where scroll end events don't fire reliably
      scrollTimeoutRef.current = setTimeout(() => {
        isScrollingRef.current = false;
        targetSectionRef.current = null;
      }, 800);
    }
  };

  // 滚动监听
  const handleScroll = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    if (isScrollingRef.current) return;
    const scrollY = event.nativeEvent.contentOffset.y;
    const current = findCurrentSectionByScroll(scrollY);
    if (current !== activeSection) setActiveSection(current);
  };

  const handleScrollEnd = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    // 清除 fallback timeout（如果还在运行）
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
      scrollTimeoutRef.current = null;
    }
    
    const scrollY = event.nativeEvent.contentOffset.y;
    const current = findCurrentSectionByScroll(scrollY);
    // 当用户触发滚动结束或者动量结束时，解除锁定并把 activeSection 校准到实际位置
    isScrollingRef.current = false;
    targetSectionRef.current = null;
    if (current !== activeSection) setActiveSection(current);
  };

  return {
    activeSection,
    scrollViewRef,
    onSectionLayout,
    scrollToSection,
    handleScroll,
    handleScrollEnd,
  };
};
