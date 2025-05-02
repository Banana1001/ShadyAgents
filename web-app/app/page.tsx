'use client';

import { useState } from 'react';
import Card, { CardProps } from './components/Card';

export default function Home() {
  const [input, setInput] = useState('');
  const [cards, setCards] = useState<CardProps[]>([]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const messageToSend = input;
    setInput(''); // Clear input immediately

    // TODO: Replace this with real agent call
    const cards = await fakeAgentCall(messageToSend);

    setCards(cards);
  };

  // Fake agent for demo purposes
  const fakeAgentCall = async (msg: string): Promise<CardProps[]> => {
    return new Promise((res) =>
      setTimeout(() => {
        res([
          { type: 'action', content: `Response to "${msg}"` },
          { type: 'action', content: `Another response to "${msg}"` },
          { type: 'action', content: `Yet another response to "${msg}"` },
        ]);
      }, 1000
    ));
  };

  return (
    <div className="flex flex-col h-screen bg-gray-100">

      {/* Title */}
      <header className="text-3xl font-bold text-gray-800 mt-4 ml-6">
        Planner App
      </header>


      {/* Horizontal action card row */}
      <div className="px-4 pb-3">
        <div className="flex gap-4 overflow-x-auto">
          {cards.map((card, index) => (
            <Card key={index} type={card.type} content={card.content} />
          ))}
        </div>
      </div>

      {/* Input box */}
      <div className="p-3 flex gap-2 px-10">
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
