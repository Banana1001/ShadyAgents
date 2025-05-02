interface TimelineProps {
  className?: string;
}

export default function Timeline({ className = '' }: TimelineProps) {
  return (
    <div className={`h-16 bg-gradient-to-b from-gray-800 to-gray-900 relative w-full ${className}`}>
      {/* Main timeline line */}
      <div className="absolute left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 via-purple-500 to-blue-500 top-1/2 transform -translate-y-1/2"></div>
      
      {/* Center marker */}
      <div className="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2">
        <div className="w-4 h-4 bg-blue-500 rounded-full border-2 border-white shadow-lg"></div>
      </div>

      {/* Glow effect */}
      <div className="absolute left-0 right-0 h-1 bg-blue-500/20 blur-sm top-1/2 transform -translate-y-1/2"></div>
    </div>
  );
} 