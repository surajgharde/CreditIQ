import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

/** What the assistant is currently looking at. Empty on pages with no borrower. */
export interface ChatScope {
  /** Grounds answers in this analysis. Omitted for demo reports, which have
   *  no row in the backend for /api/chat to read. */
  analysisId?: number;
  companyName?: string;
}

interface ChatScopeValue {
  scope: ChatScope;
  setScope: (scope: ChatScope) => void;
}

const ChatScopeContext = createContext<ChatScopeValue>({ scope: {}, setScope: () => {} });

/** Lets the single app-level Chatbot know which borrower the open page is
 *  about, without every page having to mount its own copy of the widget. */
export const ChatScopeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [scope, setScope] = useState<ChatScope>({});
  const value = useMemo(() => ({ scope, setScope }), [scope]);
  return <ChatScopeContext.Provider value={value}>{children}</ChatScopeContext.Provider>;
};

export const useChatScope = () => useContext(ChatScopeContext);

/** Publish the page's borrower to the global assistant, and clear it on exit.
 *  Call it unconditionally, above any early return. */
export const usePublishChatScope = (analysisId?: number, companyName?: string) => {
  const { setScope } = useChatScope();
  useEffect(() => {
    setScope({ analysisId, companyName });
    return () => setScope({});
  }, [analysisId, companyName, setScope]);
};
