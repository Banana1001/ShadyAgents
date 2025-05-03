export interface TimelineEvent {
  id: string;
  position: number;
  content: string;
  time: string;
  type: 'action' | 'idea' | 'combine';
  placement: 'above' | 'below';
  cards: Array<{
    id: string;
    content: string;
    type: 'action' | 'idea' | 'combine';
    time?: string;
  }>;
} 