import { TimelineEvent } from '../types';

export const generateICS = (events: TimelineEvent[], projectName: string) => {
  const icsEvents = events.map(event => {
    const startDate = new Date(event.time);
    const endDate = new Date(startDate.getTime() + 60 * 60 * 1000); // 1 hour duration by default
    
    return [
      'BEGIN:VEVENT',
      `DTSTART:${startDate.toISOString().replace(/[-:]/g, '').split('.')[0]}Z`,
      `DTEND:${endDate.toISOString().replace(/[-:]/g, '').split('.')[0]}Z`,
      `SUMMARY:${event.content.split('\n')[0]}`,
      `DESCRIPTION:${event.content.replace(/\n/g, '\\n')}`,
      'END:VEVENT'
    ].join('\r\n');
  }).join('\r\n');

  const icsContent = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//PlanCrafter//EN',
    `X-WR-CALNAME:${projectName}`,
    icsEvents,
    'END:VCALENDAR'
  ].join('\r\n');

  return icsContent;
};

export const downloadCalendar = (events: TimelineEvent[], projectName: string) => {
  const icsContent = generateICS(events, projectName);
  const blob = new Blob([icsContent], { type: 'text/calendar;charset=utf-8' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${projectName.toLowerCase().replace(/\s+/g, '-')}-calendar.ics`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}; 