import React, { useRef, useState, useMemo, Fragment } from 'react';
import styled from '@emotion/styled';
import { Updater, useImmer } from 'use-immer';
import { Tool, Point, RectPoints, Annotation, AnnotationType, Optional } from './types';
import { RectBoxProps } from './RectBox';
import NativeDiv from '../NativeDiv';
import useLatestCallback from '../../hooks/useLatestCallback';
import { registry } from './core/registry';
import { ToolContext } from './core/types';
import RectTool from './tools/RectTool';
import DragTool from './tools/DragTool';
import CrosshairOverlay from './overlays/CrosshairOverlay';
import RectMaskOverlay from './overlays/RectMaskOverlay';
import PointTool from './tools/PointTool';
import RectAnnotation from './RectAnnotation';
import PointAnnotation from './PointAnnotation';

registry.registerTool(DragTool); 
registry.registerTool(RectTool);
registry.registerTool(PointTool);
registry.registerOverlay(CrosshairOverlay);
registry.registerOverlay(RectMaskOverlay);

const EditorContainer = styled(NativeDiv)<{ isDragging: boolean }>`
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background: #f0f0f0;
  user-select: none;
  cursor: ${props => props.isDragging ? 'grabbing' : 'grab'};
`;

const EditorImage = styled.img<{ scale: number; x: number; y: number }>`
  image-rendering: pixelated;
  position: absolute;
  transform: translate(${props => props.x}px, ${props => props.y}px) scale(${props => props.scale});
  transform-origin: left top;
  pointer-events: none;
`;


export type AnnotationChangeType = 'add' | 'remove' | 'update';
export interface AnnotationChangedEvent {
  currentTool: Tool;
  type: AnnotationChangeType;
  annotationType: AnnotationType;
  annotation: Annotation;
}

export interface ImageEditorProps {
  image: string;
  tool?: Tool;
  initialScale?: number;
  showCrosshair?: boolean;
  annotations: Annotation[];
  onAnnotationChanged?: (e: AnnotationChangedEvent) => void;
  onAnnotationSelected?: (annotation: Annotation | null) => void;
  enableMask?: boolean;
  maskAlpha?: number;
  imageSize?: {
    width: number;
    height: number;
  };
  /**
   * 编辑器的缩放模式。默认为 `wheel`。
   * 
   * * `wheel` - 使用滚轮缩放，Ctrl + 滚轮上下移动，Shift + 滚轮左右移动
   * * `ctrlWheel` - 使用 Ctrl + 滚轮缩放，滚轮上下移动，Shift + 滚轮左右移动
   */
  scaleMode?: 'wheel' | 'ctrlWheel'
  onNativeKeyDown?: (e: KeyboardEvent) => void;
}

export interface ImageEditorRef {
  reset: () => void;
  setScale: (scale: number) => void;
  getScale: () => number;
}

export interface EditorState {
  /** 图片的缩放比例 */
  imageScale: number;
  /** 图片相对于容器的偏移量/坐标 */
  imagePosition: Point;
  /** 图片相对于视口的偏移量/坐标 */
  imageClientPosition: Point;
  isDragging: boolean;
  dragStart: Point;
  mousePosition: Point;
}

export interface PostionConvertor {
  posContainer2Image: (pos: Point) => Point;
  posImage2Container: (pos: Point) => Point;
  rectImage2Container: (rect: RectPoints) => RectPoints;
  rectContainer2Image: (rect: RectPoints) => RectPoints;
}

export interface ToolHandlerProps {
  editorState: [EditorState, Updater<EditorState>];
  editorProps: ImageEditorProps;
  containerRef: React.RefObject<HTMLDivElement>;
  renderAnnotation: (annotations?: Annotation[], props?: Optional<RectBoxProps>) => React.ReactNode;
  addAnnotation: (annotation: Annotation) => void;
  updateAnnotation: (type: AnnotationType, annotation: Annotation) => void;
  queryAnnotation: (id: string) => Annotation | null | undefined;
  Convertor: PostionConvertor;
}

const ImageEditor = React.forwardRef<ImageEditorRef, ImageEditorProps>((props, ref) => {
  const {
    image,
    initialScale = 1,
    onAnnotationChanged,
    annotations = [],
  } = props;

  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  // 预加载图片以获取尺寸
  const onImageLoad = () => {
    const img = imageRef.current;
    if (!img) return;

    const fitResult = calculateImageFit();
    if (fitResult) {
      updateState(draft => {
        draft.imageScale = fitResult.scale;
        draft.imagePosition = fitResult.position;
        draft.imageClientPosition = fitResult.clientPosition;
      });
    }

    setImageSize({
      width: img.naturalWidth,
      height: img.naturalHeight
    });
  };

  const [state, updateState] = useImmer<EditorState>({
    imageScale: initialScale,
    imagePosition: { x: 0, y: 0 },
    imageClientPosition: { x: 0, y: 0 },
    isDragging: false,
    dragStart: { x: 0, y: 0 },
    mousePosition: { x: 0, y: 0 }
  });

  const [imageSize, setImageSize] = useState<{ width: number; height: number }>({ width: 0, height: 0 });

  /**
   * 计算图像在容器中的居中位置和缩放比例
   * @returns 返回图像的缩放比例和位置信息
   */
  const calculateImageFit = () => {
    const img = imageRef.current;
    const container = containerRef.current;
    if (!img || !container) return null;

    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;
    const imageRatio = img.naturalWidth / img.naturalHeight;
    const containerRatio = containerWidth / containerHeight;

    let scale = initialScale;
    if (imageRatio > containerRatio) {
      // 图片更宽，以容器宽度为基准
      scale = containerWidth / img.naturalWidth * 0.9;
    } else {
      // 图片更高，以容器高度为基准
      scale = containerHeight / img.naturalHeight * 0.9;
    }

    // 计算居中位置
    const scaledWidth = img.naturalWidth * scale;
    const scaledHeight = img.naturalHeight * scale;
    const x = (containerWidth - scaledWidth) / 2;
    const y = (containerHeight - scaledHeight) / 2;

    return {
      scale,
      position: { x, y },
      clientPosition: {
        x: container.getBoundingClientRect().left + x,
        y: container.getBoundingClientRect().top + y
      }
    };
  };

  const Convertor = useMemo(() => ({
    /**
     * 从容器坐标转换到图片坐标
     * @param pos 容器坐标
     * @returns 图片坐标
     */
    posContainer2Image: (pos: Point) => {
      return {
        x: Math.round((pos.x - state.imagePosition.x) / state.imageScale),
        y: Math.round((pos.y - state.imagePosition.y) / state.imageScale)
      };
    },
    /**
     * 从图片坐标转换到容器坐标
     * @param pos 图片坐标
     * @returns 容器坐标
     */
    posImage2Container: (pos: Point) => {
      return {
        x: pos.x * state.imageScale + state.imagePosition.x,
        y: pos.y * state.imageScale + state.imagePosition.y
      };
    },
    /**
     * 从图片坐标转换到容器坐标
     * @param rect 图片坐标
     * @returns 容器坐标
     */
    rectImage2Container: (rect: RectPoints) => {
      return {
        x1: Convertor.posImage2Container({ x: rect.x1, y: rect.y1 }).x,
        y1: Convertor.posImage2Container({ x: rect.x1, y: rect.y1 }).y,
        x2: Convertor.posImage2Container({ x: rect.x2, y: rect.y2 }).x,
        y2: Convertor.posImage2Container({ x: rect.x2, y: rect.y2 }).y
      };
    },
    /**
     * 从容器坐标转换到图片坐标
     * @param rect 容器坐标
     * @returns 图片坐标
     */
    rectContainer2Image: (rect: RectPoints) => {
      return {
        x1: Convertor.posContainer2Image({ x: rect.x1, y: rect.y1 }).x,
        y1: Convertor.posContainer2Image({ x: rect.x1, y: rect.y1 }).y,
        x2: Convertor.posContainer2Image({ x: rect.x2, y: rect.y2 }).x,
        y2: Convertor.posContainer2Image({ x: rect.x2, y: rect.y2 }).y
      };
    }
  }), [state.imageScale, state.imagePosition]);

  const addAnnotation = (annotation: Annotation) => {
    console.log('Add annotation: ', annotation);
    onAnnotationChanged?.({
      currentTool: Tool.Rect,
      type: 'add',
      annotationType: 'rect',
      annotation: annotation
    });
  };
  const updateAnnotation = (type: AnnotationType, annotation: Annotation) => {
    console.log('Update rect: ', annotation);
    onAnnotationChanged?.({
      currentTool: Tool.Rect,
      type: 'update',
      annotationType: type,
      annotation: annotation
    });
  };

  const queryAnnotation = (id: string) => {
    let ret = null;
    if (annotations) {
      ret = annotations.find(annotation => annotation.id === id);
    }
    return ret;
  };

  // 处理鼠标滚轮缩放
  const handleWheel = useLatestCallback((e: WheelEvent) => {
    e.preventDefault();
    const delta = -e.deltaY;
    const scaleMode = props.scaleMode || 'wheel';

    // 判断缩放还是滚动
    const shouldScale = 
      (scaleMode === 'wheel' && !e.ctrlKey && !e.shiftKey) || 
      (scaleMode === 'ctrlWheel' && e.ctrlKey);

    if (shouldScale) {
      const scaleChange = delta > 0 ? 1.1 : 0.9;

      // 获取鼠标相对于容器的坐标
      const container = containerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      // 计算鼠标位置在图片上的相对位置
      const mouseImageX = (mouseX - state.imagePosition.x) / state.imageScale;
      const mouseImageY = (mouseY - state.imagePosition.y) / state.imageScale;

      updateState(draft => {
        draft.imageScale = Math.max(0.1, Math.min(10, draft.imageScale * scaleChange));
        
        // 计算新的图片位置，保持鼠标指向的图片位置不变
        draft.imagePosition.x = mouseX - mouseImageX * draft.imageScale;
        draft.imagePosition.y = mouseY - mouseImageY * draft.imageScale;
      });
    } else {
      const moveX = e.shiftKey ? delta : 0;
      const moveY = !e.shiftKey ? delta : 0;

      updateState(draft => {
        draft.imagePosition.x += moveX;
        draft.imagePosition.y += moveY;
      });
    }
  });

  // 暴露组件方法
  React.useImperativeHandle(ref, () => ({
    reset: () => {
      updateState(draft => {
        draft.imageScale = initialScale;
        draft.imagePosition = { x: 0, y: 0 };
      });
    },
    setScale: (newScale: number) => {
      updateState(draft => {
        draft.imageScale = newScale;
      });
    },
    getScale: () => state.imageScale
  }));

  const toolContext: ToolContext = {
    editorState: [state, updateState],
    containerRef,
    imageSize,
    Convertor,
    updateAnnotation,
    addAnnotation,
    queryAnnotation,
    editorProps: props
  };

  const currentTool = registry.getTool(props.tool || Tool.Drag);
  const overlays = registry.getOverlays();

  return (
    <EditorContainer
      ref={containerRef}
      isDragging={state.isDragging}
      style={{ cursor: currentTool?.cursor }}
      onNativeKeyDown={props.onNativeKeyDown}
      onNativeMouseWheel={handleWheel}
    >
      <EditorImage
        ref={imageRef}
        src={image}
        scale={state.imageScale}
        x={state.imagePosition.x}
        y={state.imagePosition.y}
        onLoad={onImageLoad}
      />

      {/* 渲染已有标注 */}
      {annotations.map(annotation => (
        <Fragment key={annotation.id}>
          {annotation.type === 'rect' && (
            <RectAnnotation
              annotation={annotation}
              Convertor={Convertor}
            />
          )}
          {annotation.type === 'point' && (
            <PointAnnotation
              annotation={annotation}
              Convertor={Convertor}
            />
          )}
        </Fragment>
      ))}

      {/* 渲染覆盖层 */}
      {overlays.map(overlay => (
        <Fragment key={overlay.name}>
          <overlay.component
            {...toolContext}
            tool={props.tool || Tool.Drag}
          />
        </Fragment>
      ))}

      {/* 渲染当前工具 */}
      {currentTool && <currentTool.Component {...toolContext} />}
    </EditorContainer>
  );
});
ImageEditor.displayName = 'ImageEditor';

export default ImageEditor;
