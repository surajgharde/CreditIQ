import React from 'react';
import { useSearchParams } from 'react-router-dom';
import Chatbot from './Chatbot';
import { useChatScope } from '../context/ChatScopeContext';
import { findDemoAccount } from '../services/demoAccounts';

/** The one assistant instance for the whole app. Mounted once in App so it is
 *  reachable from every route and keeps its transcript across navigation.
 *
 *  Scope resolution, most specific first:
 *    1. whatever the open page published via usePublishChatScope
 *    2. the ?id= / ?demo= query params, which most report routes already carry
 *  so pages that never loaded borrower data still get a grounded assistant. */
const GlobalChatbot: React.FC = () => {
  const { scope } = useChatScope();
  const [searchParams] = useSearchParams();

  const demoParam = searchParams.get('demo');
  const rawId = Number(searchParams.get('id'));
  // Demo reports exist only in the frontend, so there is no analysis row for
  // /api/chat to read — leave the id off and let the assistant answer generally.
  const urlAnalysisId = !demoParam && Number.isFinite(rawId) && rawId > 0 ? rawId : undefined;
  const demoCompany = demoParam ? findDemoAccount(demoParam)?.results.company.company_name : undefined;

  return (
    <Chatbot
      analysisId={scope.analysisId ?? urlAnalysisId}
      companyName={scope.companyName ?? demoCompany}
    />
  );
};

export default GlobalChatbot;
