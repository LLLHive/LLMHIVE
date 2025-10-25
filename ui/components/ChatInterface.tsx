'use client';

import { useState, useRef, useEffect } from 'react';
import Header from './Header';
import Sidebar from './Sidebar';

interface Message {
  text: string;
  isUser: boolean;
}

interface ChatInterfaceProps {
  user: {
    name?: string | null;
    email?: string | null;
    image?: string | null;
  };
}

export default function ChatInterface({ user }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<null | HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const handleNewChat = () => {
    setMessages([]);
    setInput('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { text: input, isUser: true };
    setMessages((prev) => [...prev, userMessage]);
    const currentInput = input;
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/prompt', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.email || 'authenticated-user',
          prompt: currentInput,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`API error ${response.status}: ${errorData.detail || response.statusText}`);
      }

      setMessages((prev) => [...prev, { text: '', isUser: false }]);
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value);
          setMessages((prev) => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];
            lastMessage.text += chunk;
            return newMessages;
          });
        }
      }
    } catch (error) {
      console.error("Error fetching streaming response:", error);
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred.';
      setMessages((prev) => [...prev, { text: `Sorry, something went wrong: ${errorMessage}`, isUser: false }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-900">
      {/* Sidebar */}
      <Sidebar user={user} onNewChat={handleNewChat} />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        <Header />

        {/* Messages Area */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto p-6">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-20">
                <h2 className="text-3xl font-semibold text-white mb-4">
                  Welcome to LLMHive
                </h2>
                <p className="text-gray-400 text-lg">
                  Start a conversation with your AI agents
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {messages.map((msg, index) => (
                  <div
                    key={index}
                    className={`flex ${msg.isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-3xl p-4 rounded-2xl ${
                        msg.isUser
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-800 text-gray-100'
                      }`}
                    >
                      <p style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</p>
                    </div>
                  </div>
                ))}
                {isLoading && messages[messages.length - 1]?.isUser && (
                  <div className="flex justify-start">
                    <div className="max-w-3xl p-4 rounded-2xl bg-gray-800 text-gray-100">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-pulse" />
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-pulse delay-75" />
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-pulse delay-150" />
                        <span className="ml-2">Thinking...</span>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </main>

        {/* Input Area */}
        <footer className="border-t border-gray-800 bg-gray-900">
          <div className="max-w-4xl mx-auto p-4">
            <form onSubmit={handleSubmit} className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                className="flex-1 p-4 rounded-xl bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Message LLMHive..."
                disabled={isLoading}
              />
              <button
                type="submit"
                className="px-6 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold disabled:bg-gray-700 disabled:cursor-not-allowed transition-colors"
                disabled={isLoading || !input.trim()}
              >
                Send
              </button>
            </form>
          </div>
        </footer>
      </div>
    </div>
  );
}
