interface Tick {
  position: number; // 0 to 1 representing position on timeline
  label?: string;
  isMajor?: boolean;
}

interface TimelineProps {
  className?: string;
  ticks?: Tick[];
  leftMargin?: number;
  rightMargin?: number;
}

export default function Timeline({ 
  className = '', 
  ticks = [],
  leftMargin = 40,
  rightMargin = 40
}: TimelineProps) {
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