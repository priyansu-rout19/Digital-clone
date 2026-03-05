import type { ChatRequest, WSMessage, WSResponseMessage } from './types';

export type WSCallbacks = {
  onProgress: (node: string) => void;
  onResponse: (response: WSResponseMessage) => void;
  onError: (message: string) => void;
  onClose: () => void;
};

export function createChatSocket(slug: string, callbacks: WSCallbacks) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${window.location.host}/chat/ws/${slug}`);

  ws.onmessage = (event) => {
    const msg: WSMessage = JSON.parse(event.data);

    switch (msg.type) {
      case 'progress':
        callbacks.onProgress(msg.node);
        break;
      case 'response':
        callbacks.onResponse(msg);
        break;
      case 'error':
        callbacks.onError(msg.message);
        break;
    }
  };

  ws.onerror = () => {
    callbacks.onError('WebSocket connection error');
  };

  ws.onclose = () => {
    callbacks.onClose();
  };

  return {
    send(request: ChatRequest) {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(request));
      }
    },
    close() {
      ws.close();
    },
    get ws() {
      return ws;
    },
  };
}
