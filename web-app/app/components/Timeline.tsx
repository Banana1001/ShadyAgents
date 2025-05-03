interface Tick {
  position: number; // 0 to 1 representing position on timeline
  label?: string;
  isMajor?: boolean;
}

interface TimelineEvent {
  id: string;
  position: number; // 0 to 1 representing position on timeline
  content: string;
  type: 'action' | 'idea' | 'generated';
  placement: 'above' | 'below';
  cards?: Array<{
    id: string;
    content: string;
    type: 'action' | 'idea' | 'generated';
  }>;
}

interface TimelineProps {
  className?: string;
  ticks?: Tick[];
  events?: TimelineEvent[];
  leftMargin?: number;
  rightMargin?: number;
  onEventDrop?: (eventId: string, card: { type: 'action' | 'idea' | 'generated', content: string }) => void;
}

export default function Timeline({ 
  className = '', 
  ticks = [],
  events = [],
  leftMargin = 40,
  rightMargin = 40,
  onEventDrop
}: TimelineProps) {
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

  return (
    <div className={`h-16 bg-gradient-to-b from-gray-800 to-gray-900 relative w-full ${className}`}>
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
            className={`bg-white shadow-md rounded-lg p-2 w-[200px] ${
              event.placement === 'above' ? '-mt-20' : 'mt-32'
            } transition-all hover:shadow-lg`}
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(e, event.id)}
          >
            <div className="flex flex-col">
              <p className="text-gray-800 text-xs font-medium">{event.content}</p>
              
              {/* Event cards */}
              {event.cards && event.cards.length > 0 && (
                <div className="space-y-1.5 mt-2 pt-2 border-t border-gray-100">
                  {event.cards.map((card) => (
                    <div 
                      key={card.id}
                      className="bg-gray-50 rounded p-1.5 text-xs text-gray-600 hover:bg-gray-100 transition-colors"
                    >
                      {card.content}
                    </div>
                  ))}
                </div>
              )}
            </div>
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