import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, X, Send, Bot } from 'lucide-react';
import './Chatbot.css';

interface Message {
  id: string;
  text: string;
  isBot: boolean;
  lang?: Language;
}

type Language = 'en' | 'hi' | 'mr';

// Predefined translations
const botResponses: Record<string, Record<Language, string>> = {
  greeting: {
    en: "Hello! I am your AI assistant. You can ask me about risk, fraud, reports, or loans.",
    hi: "नमस्ते! मैं आपका एआई (AI) सहायक हूँ। आप मुझसे रिस्क, फ्रॉड, रिपोर्ट या लोन के बारे में पूछ सकते हैं।",
    mr: "नमस्कार! मी तुमचा एआय (AI) असिस्टंट आहे. तुम्ही मला रिस्क, फ्रॉड, रिपोर्ट किंवा कर्जाविषयी विचारू शकता."
  },
  risk: {
    en: "The risk score is calculated using financial data, transaction patterns, and fraud signals.",
    hi: "रिस्क स्कोर वित्तीय डेटा, लेन-देन पैटर्न और फ्रॉड संकेतों के आधार पर निकाला जाता है।",
    mr: "रिस्क स्कोअर हा आर्थिक डेटा, व्यवहार पॅटर्न आणि फसवणूक संकेतांवर आधारित असतो."
  },
  fraud: {
    en: "Fraud detection works by identifying unusual transaction patterns and circular trading.",
    hi: "फ्रॉड डिटेक्शन असामान्य लेन-देन और सर्कुलर ट्रेडिंग की पहचान करके किया जाता है।",
    mr: "फसवणूक शोध प्रणाली असामान्य व्यवहार आणि सर्क्युलर ट्रेडिंग ओळखून कार्य करते."
  },
  report: {
    en: "This report summarizes the borrower’s financial health and risk level.",
    hi: "यह रिपोर्ट उधारकर्ता की वित्तीय स्थिति और जोखिम स्तर को दर्शाती है।",
    mr: "हा अहवाल कर्जदाराची आर्थिक स्थिती आणि जोखीम पातळी दर्शवतो."
  },
  loan: {
    en: "Loan approval depends on risk score, fraud checks, and financial stability.",
    hi: "लोन स्वीकृति रिस्क स्कोर, फ्रॉड जांच और वित्तीय स्थिरता पर निर्भर करती है।",
    mr: "कर्ज मंजुरी रिस्क स्कोअर, फसवणूक तपासणी आणि आर्थिक स्थिरतेवर अवलंबून असते."
  },
  help: {
    en: "I can help you understand risk scores, fraud detection, financial reports, and loan decisions.",
    hi: "मैं आपको रिस्क स्कोर, फ्रॉड डिटेक्शन, वित्तीय रिपोर्ट और लोन निर्णयों को समझने में मदद कर सकता हूँ।",
    mr: "मी तुम्हाला रिस्क स्कोअर, फ्रॉड डिटेक्शन, आर्थिक अहवाल आणि कर्जाचे निर्णय समजून घेण्यास मदत करू शकतो."
  },
  delay: {
    en: "Late payments negatively impact the credit score and increase the assigned risk profile.",
    hi: "देर से भुगतान क्रेडिट स्कोर को नकारात्मक रूप से प्रभावित करते हैं और जोखिम प्रोफ़ाइल बढ़ाते हैं।",
    mr: "उशिरा पेमेंट केल्याने क्रेडिट स्कोअरवर नकारात्मक परिणाम होतो आणि जोखीम पातळी वाढते."
  },
  document: {
    en: "Required documents include GST returns, bank statements, and audited financial filings.",
    hi: "आवश्यक दस्तावेजों में जीएसटी रिटर्न, बैंक स्टेटमेंट और ऑडिट किए गए वित्तीय विवरण शामिल हैं।",
    mr: "आवश्यक कागदपत्रांमध्ये जीएसटी रिटर्न, बँक स्टेटमेंट आणि ऑडिट केलेले आर्थिक तपशील समाविष्ट आहेत."
  },
  interest: {
    en: "Interest rates are determined dynamically based on the final calculated risk probability.",
    hi: "ब्याज दरें अंतिम गणना की गई जोखिम संभावना के आधार पर गतिशील रूप से निर्धारित की जाती हैं।",
    mr: "अंतिम जोखीम संभाव्यतेच्या आधारावर व्याजदर गतिशीलपणे निश्चित केले जातात."
  },
  default: {
    en: "Please ask about risk, fraud, reports, loans, or documents.",
    hi: "कृपया रिस्क, फ्रॉड, रिपोर्ट, लोन या दस्तावेज़ों के बारे में पूछें।",
    mr: "कृपया रिस्क, फ्रॉड, रिपोर्ट, कर्ज किंवा कागदपत्रांबद्दल विचारा."
  }
};

const Chatbot: React.FC = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [input, setInput] = useState('');
    const [lang, setLang] = useState<Language>('en');
    const [isTyping, setIsTyping] = useState(false);
    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            text: botResponses.greeting.en,
            isBot: true,
            lang: 'en'
        }
    ]);
    
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping, isOpen]);

    // Handle language change explicitly
    const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const newLang = e.target.value as Language;
        setLang(newLang);
        
        // Add a greeting in the new language to acknowledge the switch
        setMessages(prev => [
            ...prev,
            {
               id: Date.now().toString(),
               text: botResponses.greeting[newLang],
               isBot: true,
               lang: newLang
            }
        ]);
    };

    const handleSend = () => {
        if (!input.trim()) return;

        const userText = input.trim();
        const userMsg: Message = { id: Date.now().toString(), text: userText, isBot: false };
        
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setIsTyping(true);

        setTimeout(() => {
            const lowerText = userText.toLowerCase();
            let intentKey = 'default';

            // Match keywords regardless of language
            if (lowerText.match(/(risk|रिस्क|जोखिम|जोखीम)/)) intentKey = 'risk';
            else if (lowerText.match(/(fraud|फ्रॉड|फसवणूक)/)) intentKey = 'fraud';
            else if (lowerText.match(/(report|रिपोर्ट|अहवाल)/)) intentKey = 'report';
            else if (lowerText.match(/(loan|लोन|कर्ज)/)) intentKey = 'loan';
            else if (lowerText.match(/(hello|hi|hey|नमस्ते|नमस्कार)/)) intentKey = 'greeting';
            else if (lowerText.match(/(help|मदद|मदत)/)) intentKey = 'help';
            else if (lowerText.match(/(late|delay|देर|उशिरा)/)) intentKey = 'delay';
            else if (lowerText.match(/(doc|document|दस्तावेज़|कागदपत्र)/)) intentKey = 'document';
            else if (lowerText.match(/(interest|rate|ब्याज|व्याज)/)) intentKey = 'interest';

            const botResponse = botResponses[intentKey][lang];

            const botMsg: Message = { id: (Date.now() + 1).toString(), text: botResponse, isBot: true, lang };
            setMessages(prev => [...prev, botMsg]);
            setIsTyping(false);
        }, 800);
    };

    const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            handleSend();
        }
    };

    // UI labels translation
    const uiLabels = {
        title: { en: 'CreditIQ AI Assistant', hi: 'CreditIQ AI सहायक', mr: 'CreditIQ AI असिस्टंट' },
        placeholder: { en: 'Type a message...', hi: 'एक संदेश टाइप करें...', mr: 'येथे संदेश लिहा...' }
    };

    return (
        <div className="chatbot-container">
            <div className={`chatbot-panel ${isOpen ? 'open' : ''}`}>
                <div className="chatbot-header">
                    <div className="chatbot-title">
                        <Bot size={20} />
                        {uiLabels.title[lang]}
                    </div>
                    <div className="chatbot-controls">
                        <select 
                            className="chatbot-lang-select" 
                            value={lang} 
                            onChange={handleLanguageChange}
                            aria-label="Select Language"
                        >
                            <option value="en">English</option>
                            <option value="hi">हिंदी</option>
                            <option value="mr">मराठी</option>
                        </select>
                        <button className="chatbot-close" onClick={() => setIsOpen(false)} aria-label="Close Chat">
                            <X size={20} />
                        </button>
                    </div>
                </div>
                
                <div className="chatbot-messages-container">
                    {messages.map((msg) => (
                        <div key={msg.id} className={`chat-bubble ${msg.isBot ? 'bot' : 'user'}`}>
                            {msg.text}
                        </div>
                    ))}
                    {isTyping && (
                        <div className="typing-indicator">
                            <div className="typing-dot"></div>
                            <div className="typing-dot"></div>
                            <div className="typing-dot"></div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
                
                <div className="chatbot-input-area">
                    <input 
                        type="text" 
                        className="chatbot-input" 
                        placeholder={uiLabels.placeholder[lang]} 
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyPress={handleKeyPress}
                    />
                    <button 
                        className="chatbot-send-btn" 
                        onClick={handleSend}
                        disabled={!input.trim() || isTyping}
                        aria-label="Send Message"
                    >
                        <Send size={18} style={{ marginLeft: '2px' }} />
                    </button>
                </div>
            </div>

            {!isOpen && (
                <button 
                    className="chatbot-toggle-button" 
                    onClick={() => setIsOpen(true)}
                    aria-label="Open Chat"
                >
                    <MessageSquare size={26} />
                </button>
            )}
        </div>
    );
};

export default Chatbot;
