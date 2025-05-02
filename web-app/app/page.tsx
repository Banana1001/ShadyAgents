'use client';

import { useState } from 'react';

export default function Home() {
  const [input, setInput] = useState('');
  const [response, setResponse] = useState<string | null>(null);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const messageToSend = input;
    setInput(''); // Clear input immediately

    // TODO: Replace this with real agent call
    const agentReply = await fakeAgentCall(messageToSend);

    setResponse(agentReply);
  };

  // Fake agent for demo purposes
  const fakeAgentCall = async (msg: string): Promise<string> => {
    return new Promise((res) =>
      setTimeout(() => res(`Echo: ${msg}`), 1000)
    );
  };

  return (
    <div className="flex flex-col h-screen bg-gray-100">

      {/* Title */}
      <header className="text-3xl font-bold text-gray-800 mt-4 ml-6">
        Planner App
      </header>


      {/* Display response */}
      <div className="flex-1 overflow-y-auto py-3 text-base">
        {response && (
          <div className="bg-gray-200 px-4 py-3 rounded-lg max-w-xl mx-auto mb-4 text-center">
            {response}
          </div>
        )}
      </div>

      {/* Input box */}
      <div className="p-3 border-t flex gap-2 bg-white px-10">
        <input
          className="flex-1 border rounded-md px-3 py-2 text-sm outline-none"
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
        />
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm hover:bg-blue-700"
          onClick={sendMessage}
        >
          Send
        </button>
      </div>
    </div>
  );
}
