import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/solid';
import 'katex/dist/katex.min.css';

interface Tick {
  position: number; // 0 to 1 representing position on timeline
  label?: string;
  isMajor?: boolean;
}

interface TimelineEvent {
  id: string;
  position: number; // 0 to 1 representing position on timeline
  time: string;
  content: string;
  type: 'action' | 'idea' | 'combine';
  placement: 'above' | 'below';
  cost?: number; // Added cost property
  cards?: Array<{
    id: string;
    content: string;
    type: 'action' | 'idea' | 'combine';
  }>;
}

interface TimelineProps {
  className?: string;
  ticks?: Tick[];
  events?: TimelineEvent[];
  leftMargin?: number;
  rightMargin?: number;
  onEventDrop?: (eventId: string, card: { type: 'action' | 'idea' | 'combine', content: string }) => void;
  dragOverTarget?: {
    type: 'card' | 'event' | 'timeline' | null;
    id?: string;
  };
  onEventDragOver?: (e: React.DragEvent, eventId: string) => void;
  onEventDragLeave?: () => void;
}

export default function Timeline({ 
  className = '', 
  ticks = [],
  events = [],
  leftMargin = 40,
  rightMargin = 40,
  onEventDrop,
  dragOverTarget,
  onEventDragOver,
  onEventDragLeave
}: TimelineProps) {
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent, eventId: string) => {
    e.preventDefault();
    try {
      const cardData = JSON.parse(e.dataTransfer.getData('text/plain'));
      onEventDrop?.(eventId, cardData);
    } catch (error) {
      console.error('Invalid card data');
    }
  };

  const toggleEvent = (eventId: string) => {
    setExpandedEvents(prev => {
      const newSet = new Set(prev);
      if (newSet.has(eventId)) {
        newSet.delete(eventId);
      } else {
        newSet.add(eventId);
      }
      return newSet;
    });
  };

  const getEventTypeColor = (type: 'action' | 'idea' | 'combine') => {
    switch (type) {
      case 'action':
        return 'bg-blue-500';
      case 'idea':
        return 'bg-purple-500';
      case 'combine':
        return 'bg-green-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <div className={`h-16 bg-gradient-to-b from-gray-800 to-gray-900 relative w-full rounded-2xl ${className}`}>
      {/* Main timeline line */}
      <div 
        className="absolute h-0.5 bg-gradient-to-r from-blue-500 via-purple-500 to-blue-500 top-1/2 transform -translate-y-1/2"
        style={{ 
          left: `${leftMargin}px`,
          right: `${rightMargin}px`
        }}
      ></div>
      
      {/* Tick marks */}
      {ticks.map((tick, index) => (
        <div
          key={index}
          className="absolute top-1/2 transform -translate-y-1/2"
          style={{ 
            left: `calc(${leftMargin}px + ${tick.position * (100 - (leftMargin + rightMargin) / 16)}%)`
          }}
        >
          {/* Tick line */}
          <div className={`w-0.5 bg-gray-600 ${tick.isMajor ? 'h-6' : 'h-3'}`}></div>
          
          {/* Label */}
          {tick.label && (
            <div className="absolute top-6 left-1/2 transform -translate-x-1/2 text-xs text-gray-400">
              {tick.label}
            </div>
          )}
        </div>
      ))}

      {/* Event cards */}
      {events.map((event) => (
        <div
          key={event.id}
          className="absolute top-1/2 transform -translate-y-1/2 -translate-x-1/2 z-10"
          style={{ 
            left: `calc(${leftMargin}px + ${event.position * (100 - (leftMargin + rightMargin) / 16)}%)`,
            top: event.placement === 'above' ? '50%' : '50%'
          }}
        >
          <div 
            className={`bg-white shadow-md rounded-lg w-[320px] ${
              event.placement === 'above' ? '-mt-20' : 'mt-32'
            } transition-all duration-200 hover:shadow-xl hover:scale-105 overflow-hidden ${
              dragOverTarget?.type === 'event' && dragOverTarget?.id === event.id ? 'ring-4 ring-green-500 scale-105' : ''
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onEventDragOver?.(e, event.id);
            }}
            onDragLeave={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onEventDragLeave?.();
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              handleDrop(e, event.id);
            }}
          >
            {/* Event header */}
            <div 
              className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50/80 transition-colors"
              onClick={() => toggleEvent(event.id)}
            >
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${getEventTypeColor(event.type)}`} />
                <p className="text-gray-800 text-sm font-medium">{event.content.split('\n')[0]}</p>
              </div>
              {expandedEvents.has(event.id) ? (
                <ChevronUpIcon className="w-4 h-4 text-gray-500" />
              ) : (
                <ChevronDownIcon className="w-4 h-4 text-gray-500" />
              )}
            </div>
            
            {/* Expanded content */}
            {expandedEvents.has(event.id) && (
              <div className="p-3 pt-0 border-t border-gray-100">
                {/* Event description with markdown */}
                <div className="prose prose-sm max-w-none text-gray-600">
                  <ReactMarkdown
                    remarkPlugins={[remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                  >
                    {event.content}
                  </ReactMarkdown>
                </div>

                <div className="text-xs text-gray-400 mt-2">
                  Time: {new Date(event.time).toLocaleString()}
                </div>

                <div className="text-xs text-gray-400 mt-2">
                  Cost: {new String(event.cost).toLocaleString()}
                </div>
                
                {/* Event cards */}
                {event.cards && event.cards.length > 0 && (
                  <div className="space-y-2 mt-3 pt-3 border-t border-gray-100">
                    {event.cards.map((card) => (
                      <div 
                        key={card.id}
                        className="bg-gray-50 rounded p-2 text-sm text-gray-600 hover:bg-gray-100 transition-colors"
                      >
                        <div className="prose prose-sm max-w-none">
                          <ReactMarkdown
                            remarkPlugins={[remarkMath]}
                            rehypePlugins={[rehypeKatex]}
                          >
                            {card.content}
                          </ReactMarkdown>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      ))}

      {/* Glow effect */}
      <div 
        className="absolute h-1 bg-blue-500/20 blur-sm top-1/2 transform -translate-y-1/2"
        style={{ 
          left: `${leftMargin}px`,
          right: `${rightMargin}px`
        }}
      ></div>
    </div>
  );
} 