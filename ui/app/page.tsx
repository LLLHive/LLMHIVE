'use client';

import { useState, useRef, useEffect } from 'react';

interface Message {
  text: string;
  isUser: boolean;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<null | HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = { text: input, isUser: true };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // API call to our Python backend will be implemented here
      // For now, we'll simulate a streaming response
      const simulatedResponse = "This is a simulated streaming response from the LLMHive engine. In the real implementation, this text would stream in token by token from our powerful, multi-protocol AI backend.".split(' ');
      
      let streamedText = '';
      setMessages((prev) => [...prev, { text: '', isUser: false }]);

      for (const word of simulatedResponse) {
        await new Promise(resolve => setTimeout(resolve, 50)); // Simulate network latency
        streamedText += word + ' ';
        setMessages((prev) => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1].text = streamedText;
          return newMessages;
        });
      }

    } catch (error) {
      console.error("Error fetching response:", error);
      setMessages((prev) => [...prev, { text: 'Sorry, something went wrong.', isUser: false }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 p-4 shadow-md">
        <h1 className="text-xl font-bold text-center">LLMHive</h1>
      </header>
      <main className="flex-1 overflow-y-auto p-4">
        <div className="space-y-4">
          {messages.map((msg, index) => (
            <div key={index} className={`flex ${msg.isUser ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-2xl p-3 rounded-lg ${msg.isUser ? 'bg-blue-600' : 'bg-gray-700'}`}>
                <p style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</p>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="max-w-2xl p-3 rounded-lg bg-gray-700">
                <p>Thinking...</p>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </main>
      <footer className="p-4 bg-gray-800">
        <form onSubmit={handleSubmit} className="flex">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="flex-1 p-2 rounded-l-lg bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Ask LLMHive..."
            disabled={isLoading}
          />
          <button
            type="submit"
            className="bg-blue-600 text-white p-2 rounded-r-lg hover:bg-blue-700 disabled:bg-gray-500"
            disabled={isLoading}
          >
            Send
          </button>
        </form>
      </footer>
    </div>
  );
}
