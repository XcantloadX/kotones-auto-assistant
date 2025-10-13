import React, { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { Modal, Button } from 'react-bootstrap';

type MessageBoxAction<T> = [string, T, string?]; // label, value, variant

interface MessageBoxOptions<T> {
  title: string;
  content: string | ReactNode;
  actions: Array<MessageBoxAction<T>>;
}

interface MessageBoxState<T> extends MessageBoxOptions<T> {
  resolve: (value: T | PromiseLike<T>) => void;
}

export interface MessageBoxContextType {
  show: <T>(options: MessageBoxOptions<T>) => Promise<T>;
  ok: (content: string, title?: string) => Promise<void>;
  ask: (content: string, title?: string) => Promise<boolean>;
}

const MessageBoxContext = createContext<MessageBoxContextType | null>(null);

export function useMessageBox(): MessageBoxContextType {
  const ctx = useContext(MessageBoxContext);
  if (!ctx) {
    throw new Error('useMessageBox must be used within a MessageBoxProvider');
  }
  return ctx;
}

export function MessageBoxProvider({ children }: React.PropsWithChildren) {
  const [options, setOptions] = useState<MessageBoxState<any> | null>(null);
  const [isModalVisible, setModalVisible] = useState(false);

  const handleAction = <T,>(value: T) => {
    if (options) {
      options.resolve(value);
      setModalVisible(false);
    }
  };

  const showMessageBox = useCallback(<T,>(opts: MessageBoxOptions<T>): Promise<T> => {
    return new Promise((resolve) => {
      setOptions({ ...opts, resolve: resolve as (value: any) => void });
      setModalVisible(true);
    });
  }, []);

  const ok = useCallback(async (content: string, title: string = '提示') => {
    await showMessageBox<void>({
      title,
      content,
      actions: [['确定', undefined, 'primary']],
    });
  }, [showMessageBox]);

  const ask = useCallback((content: string, title: string = '请确认') => {
    return showMessageBox<boolean>({
      title,
      content,
      actions: [['是', true, 'primary'], ['否', false]],
    });
  }, [showMessageBox]);

  const contextValue = useMemo<MessageBoxContextType>(() => ({
    show: showMessageBox,
    ok,
    ask,
  }), [showMessageBox, ok, ask]);

  return (
    <MessageBoxContext.Provider value={contextValue}>
      {children}
      {options && (
        <Modal show={isModalVisible} onHide={() => { /* Clicking outside disabled */ }} onExited={() => setOptions(null)} centered>
            <Modal.Header>
                <Modal.Title>{options.title}</Modal.Title>
            </Modal.Header>
            <Modal.Body>{options.content}</Modal.Body>
            <Modal.Footer>
                {options.actions.map(([label, value, variant]) => (
                    <Button 
                        key={label} 
                        variant={variant || 'secondary'} 
                        onClick={() => handleAction(value)}>
                        {label}
                    </Button>
                ))}
            </Modal.Footer>
        </Modal>
      )}
    </MessageBoxContext.Provider>
  );
};
