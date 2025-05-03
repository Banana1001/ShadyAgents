'use client';

import { useState } from 'react';
import Timeline from './components/Timeline';
import Card, {CardProps} from './components/Card';
import {
  ChevronDownIcon,
  ArrowLeftCircleIcon,
  ArrowRightCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/solid';

// Example timeline configurations
const timelineConfigs = {
  hours: {
    ticks: Array.from({ length: 24 }, (_, i) => ({
      position: i / 23,
      label: i % 6 === 0 ? `${i}:00` : undefined,
      isMajor: i % 6 === 0
    }))
  },
  days: {
    ticks: Array.from({ length: 7 }, (_, i) => ({
      position: i / 6,
      label: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][i],
      isMajor: true
    }))
  },
  months: {
    ticks: Array.from({ length: 12 }, (_, i) => ({
      position: i / 11,
      label: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][i],
      isMajor: true
    }))
  }
};

interface TimelineEvent {
  id: string;
  position: number;
  content: string;
  type: 'action' | 'idea' | 'generated';
  placement: 'above' | 'below';
  cards: Array<{
    id: string;
    content: string;
    type: 'action' | 'idea' | 'generated';
  }>;
}

interface Project {
  id: string;
  name: string;
  createdAt: Date;
  timelineType: 'hours' | 'days' | 'months' | 'custom';
  customTicks?: Array<{
    position: number;
    label?: string;
    isMajor?: boolean;
  }>;
  cards: CardProps[];
  placedCards: PlacedCard[];
  timelineEvents: TimelineEvent[];
}

interface PlacedCard extends CardProps {
  id: string;
  position: {
    x: number;
    y: number;
  };
  canvas: 'top' | 'bottom';
  combinedCards?: string[]; // Track IDs of cards that were combined
}

export default function Home() {
  const [input, setInput] = useState('');
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [projects, setProjects] = useState<Project[]>([
    { 
      id: '1', 
      name: 'Project Alpha', 
      createdAt: new Date(),
      timelineType: 'hours',
      cards: [],
      placedCards: [],
      timelineEvents: [
        {
          id: '1',
          position: 0.25,
          content: 'Morning Meeting',
          type: 'action',
          placement: 'above',
          cards: []
        },
        {
          id: '2',
          position: 0.5,
          content: 'Lunch Break',
          type: 'action',
          placement: 'below',
          cards: []
        },
        {
          id: '3',
          position: 0.75,
          content: 'Project Review',
          type: 'action',
          placement: 'above',
          cards: []
        }
      ]
    },
    { 
      id: '2', 
      name: 'Project Beta', 
      createdAt: new Date(),
      timelineType: 'days',
      cards: [],
      placedCards: [],
      timelineEvents: [
        {
          id: '1',
          position: 0.2,
          content: 'Team Sync',
          type: 'action',
          placement: 'above',
          cards: []
        },
        {
          id: '2',
          position: 0.6,
          content: 'Client Call',
          type: 'action',
          placement: 'below',
          cards: []
        }
      ]
    },
    { 
      id: '3', 
      name: 'Project Gamma', 
      createdAt: new Date(),
      timelineType: 'months',
      cards: [],
      placedCards: [],
      timelineEvents: [
        {
          id: '1',
          position: 0.3,
          content: 'Q1 Review',
          type: 'action',
          placement: 'above',
          cards: []
        },
        {
          id: '2',
          position: 0.7,
          content: 'Q2 Planning',
          type: 'action',
          placement: 'below',
          cards: []
        }
      ]
    },
  ]);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectTimelineType, setNewProjectTimelineType] = useState<'hours' | 'days' | 'months' | 'custom'>('hours');
  const [customTicks, setCustomTicks] = useState<Array<{ position: number; label?: string; isMajor?: boolean }>>([]);
  const [draggedCard, setDraggedCard] = useState<CardProps | null>(null);
  const [isDraggingPlacedCard, setIsDraggingPlacedCard] = useState(false);
  const [draggedPlacedCardId, setDraggedPlacedCardId] = useState<string | null>(null);

  const COMBINE_DISTANCE = 50; // Distance in pixels to trigger combination
  const AXIS_ZONE_HEIGHT = 40; // Height of the detection zone around the axis

  const sendMessage = async () => {
    if (!input.trim() || !selectedProject) return;

    const messageToSend = input;
    setInput(''); // Clear input immediately

    // TODO: Replace this with real agent call
    const newCards = await fakeAgentCall(messageToSend);

    // Update cards for the selected project
    setProjects(prevProjects => 
      prevProjects.map(project => 
        project.id === selectedProject
          ? { ...project, cards: newCards }
          : project
      )
    );
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

  // Fake server call for demo purposes
  const fakeServerCall = async(msg: string) => {
    const res = await fetch('http://localhost:8000/generate-plan', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message: msg }),
    });

    const data = await res.json();
    return (data.cards);
  };

  const handleCreateProject = () => {
    if (newProjectName.trim()) {
      const newProject: Project = {
        id: Date.now().toString(),
        name: newProjectName.trim(),
        createdAt: new Date(),
        timelineType: newProjectTimelineType,
        ...(newProjectTimelineType === 'custom' && { customTicks }),
        cards: [],
        placedCards: [],
        timelineEvents: []
      };
      setProjects([...projects, newProject]);
      setSelectedProject(newProject.id);
      setNewProjectName('');
      setNewProjectTimelineType('hours');
      setCustomTicks([]);
      setIsCreatingProject(false);
    }
  };

  const handleDeleteProject = (projectId: string) => {
    setProjects(projects.filter(p => p.id !== projectId));
    if (selectedProject === projectId) {
      setSelectedProject(null);
    }
  };

  // Get timeline configuration based on selected project
  const getTimelineConfig = () => {
    if (!selectedProject) return { ticks: [] };
    const project = projects.find(p => p.id === selectedProject);
    if (!project) return { ticks: [] };

    if (project.timelineType === 'custom' && project.customTicks) {
      return { ticks: project.customTicks };
    }

    if (project.timelineType in timelineConfigs) {
      return timelineConfigs[project.timelineType as keyof typeof timelineConfigs];
    }

    return { ticks: [] };
  };

  const handleDragStart = (card: CardProps) => {
    setDraggedCard(card);
  };

  const handleDragEnd = () => {
    setDraggedCard(null);
  };

  const canCombineCards = (card1: PlacedCard, card2: PlacedCard) => {
    const dx = card1.position.x - card2.position.x;
    const dy = card1.position.y - card2.position.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    return distance < COMBINE_DISTANCE;
  };

  const combineCards = (card1: PlacedCard, card2: PlacedCard): PlacedCard => {
    const combinedContent = `${card1.content}\n\n${card2.content}`;
    const combinedIds = [
      ...(card1.combinedCards || [card1.id]),
      ...(card2.combinedCards || [card2.id])
    ];

    return {
      id: Date.now().toString(),
      type: 'action',
      content: combinedContent,
      position: {
        x: (card1.position.x + card2.position.x) / 2,
        y: (card1.position.y + card2.position.y) / 2
      },
      canvas: card1.canvas,
      combinedCards: combinedIds
    };
  };

  const isNearAxis = (y: number, canvasHeight: number, isTopCanvas: boolean) => {
    if (isTopCanvas) {
      return y > canvasHeight - AXIS_ZONE_HEIGHT;
    } else {
      return y < AXIS_ZONE_HEIGHT;
    }
  };

  const handleEventDrop = (eventId: string, card: { type: 'action' | 'idea' | 'generated', content: string }) => {
    if (!selectedProject) return;

    setProjects(prevProjects => 
      prevProjects.map(project => 
        project.id === selectedProject
          ? {
              ...project,
              timelineEvents: project.timelineEvents.map(event => 
                event.id === eventId
                  ? {
                      ...event,
                      cards: [...event.cards, { ...card, id: Date.now().toString() }]
                    }
                  : event
              )
            }
          : project
      )
    );
  };

  const handleAxisDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    if (!selectedProject) return;

    const currentProject = projects.find(p => p.id === selectedProject);
    if (!currentProject) return;

    const cardContent = draggedCard 
      ? draggedCard.content 
      : currentProject.placedCards.find(card => card.id === draggedPlacedCardId)?.content;

    if (cardContent) {
      // Find if there's an existing event near the drop position
      const dropPosition = (e.clientX - e.currentTarget.getBoundingClientRect().left) / e.currentTarget.getBoundingClientRect().width;
      const existingEvent = currentProject.timelineEvents.find(event => 
        Math.abs(event.position - dropPosition) < 0.1
      );

      if (existingEvent) {
        // Get new action cards from the agent
        const newCards = await fakeAgentCall(`Card placed on timeline event: ${cardContent}`);
        
        // Update the existing event while preserving its cards
        setProjects(prevProjects => 
          prevProjects.map(project => 
            project.id === selectedProject
              ? {
                  ...project,
                  timelineEvents: project.timelineEvents.map(event => 
                    event.id === existingEvent.id
                      ? {
                          ...existingEvent,
                          content: cardContent,
                          type: draggedCard?.type || 'action'
                        }
                      : event
                  ),
                  cards: newCards,
                  placedCards: project.placedCards.filter(card => card.id !== draggedPlacedCardId)
                }
              : project
          )
        );
      } else {
        // Create a new event
        const newEvent: TimelineEvent = {
          id: Date.now().toString(),
          position: dropPosition,
          content: cardContent,
          type: draggedCard?.type || 'action',
          placement: 'above',
          cards: []
        };

        // Get new action cards from the agent
        const newCards = await fakeAgentCall(`Card placed on timeline: ${cardContent}`);

        setProjects(prevProjects => 
          prevProjects.map(project => 
            project.id === selectedProject
              ? {
                  ...project,
                  timelineEvents: [...project.timelineEvents, newEvent],
                  cards: newCards,
                  placedCards: project.placedCards.filter(card => card.id !== draggedPlacedCardId)
                }
              : project
          )
        );
      }

      // Clear drag states
      setDraggedCard(null);
      setDraggedPlacedCardId(null);
      setIsDraggingPlacedCard(false);
    }
  };

  const handleDrop = async (e: React.DragEvent, canvas: 'top' | 'bottom') => {
    e.preventDefault();
    if (!draggedCard || !selectedProject) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const currentProject = projects.find(p => p.id === selectedProject);
    if (!currentProject) return;

    const newCard: PlacedCard = {
      ...draggedCard,
      id: Date.now().toString(),
      position: { x, y },
      canvas
    };

    // Check for potential combinations
    const cardToCombine = currentProject.placedCards.find(card => 
      canCombineCards(newCard, card)
    );

    setProjects(prevProjects => 
      prevProjects.map(project => 
        project.id === selectedProject
          ? {
              ...project,
              placedCards: cardToCombine
                ? [
                    ...project.placedCards.filter(card => card.id !== cardToCombine.id),
                    combineCards(newCard, cardToCombine)
                  ]
                : [...project.placedCards, newCard]
            }
          : project
      )
    );

    setDraggedCard(null);
  };

  const handlePlacedCardDragStart = (e: React.DragEvent, cardId: string) => {
    setIsDraggingPlacedCard(true);
    setDraggedPlacedCardId(cardId);
    // Set a custom drag image to make it look better
    const dragImage = e.currentTarget.cloneNode(true) as HTMLElement;
    dragImage.style.position = 'absolute';
    dragImage.style.top = '-1000px';
    document.body.appendChild(dragImage);
    e.dataTransfer.setDragImage(dragImage, 0, 0);
    setTimeout(() => document.body.removeChild(dragImage), 0);
  };

  const handlePlacedCardDragEnd = () => {
    setIsDraggingPlacedCard(false);
    setDraggedPlacedCardId(null);
  };

  const handlePlacedCardDrop = async (e: React.DragEvent, canvas: 'top' | 'bottom') => {
    e.preventDefault();
    if (!draggedPlacedCardId || !selectedProject) return;

    const currentProject = projects.find(p => p.id === selectedProject);
    if (!currentProject) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const draggedCard = currentProject.placedCards.find(card => card.id === draggedPlacedCardId);
    if (!draggedCard) return;

    const newPosition = { x, y };

    // Check for potential combinations
    const cardToCombine = currentProject.placedCards.find(card => 
      card.id !== draggedPlacedCardId && 
      canCombineCards({ ...draggedCard, position: newPosition }, card)
    );

    setProjects(prevProjects => 
      prevProjects.map(project => 
        project.id === selectedProject
          ? {
              ...project,
              placedCards: cardToCombine
                ? [
                    ...project.placedCards.filter(card => 
                      card.id !== draggedPlacedCardId && card.id !== cardToCombine.id
                    ),
                    combineCards({ ...draggedCard, position: newPosition }, cardToCombine)
                  ]
                : project.placedCards.map(card => 
                    card.id === draggedPlacedCardId
                      ? { ...card, position: newPosition, canvas }
                      : card
                  )
            }
          : project
      )
    );

    setIsDraggingPlacedCard(false);
    setDraggedPlacedCardId(null);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  // Get current project's cards and placed cards
  const getCurrentProjectCards = () => {
    if (!selectedProject) return { cards: [], placedCards: [] };
    const project = projects.find(p => p.id === selectedProject);
    return {
      cards: project?.cards || [],
      placedCards: project?.placedCards || []
    };
  };

  const { cards, placedCards } = getCurrentProjectCards();

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Left Sidebar */}
      <div 
        className={`${isSidebarCollapsed ? 'w-16' : 'w-64'} bg-gray-800 text-white flex flex-col transition-all duration-300 ease-in-out`}
      >
        <div className="p-4 border-b border-gray-700 flex items-center justify-between">
          {!isSidebarCollapsed && <h2 className="text-xl font-semibold">Projects</h2>}
          <button 
            onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            className="p-1 hover:bg-gray-700 rounded"
          >
            {isSidebarCollapsed ? '→' : '←'}
          </button>
        </div>
        
        {/* New Project Button */}
        {!isSidebarCollapsed && (
          <button 
            className="m-4 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm flex items-center justify-center gap-2"
            onClick={() => setIsCreatingProject(true)}
          >
            <span>+</span> New Project
          </button>
        )}

        {/* Project Creation Modal */}
        {isCreatingProject && !isSidebarCollapsed && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white p-6 rounded-lg w-96">
              <h3 className="text-xl font-semibold mb-4 text-gray-800">Create New Project</h3>
              <input
                type="text"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="Project Name"
                className="w-full p-2 border rounded mb-4 text-gray-800"
              />
              
              {/* Timeline Type Selection */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Timeline Type
                </label>
                <select
                  value={newProjectTimelineType}
                  onChange={(e) => setNewProjectTimelineType(e.target.value as any)}
                  className="w-full p-2 border rounded text-gray-800"
                >
                  <option value="hours">Hours (24-hour)</option>
                  <option value="days">Days of Week</option>
                  <option value="months">Months</option>
                  <option value="custom">Custom Timeline</option>
                </select>
              </div>

              {/* Custom Timeline Configuration */}
              {newProjectTimelineType === 'custom' && (
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Custom Timeline Points
                  </label>
                  <div className="space-y-2">
                    {customTicks.map((tick, index) => (
                      <div key={index} className="flex gap-2">
                        <input
                          type="number"
                          value={tick.position}
                          onChange={(e) => {
                            const newTicks = [...customTicks];
                            newTicks[index].position = parseFloat(e.target.value);
                            setCustomTicks(newTicks);
                          }}
                          placeholder="Position (0-1)"
                          className="w-24 p-2 border rounded text-gray-800"
                          min="0"
                          max="1"
                          step="0.1"
                        />
                        <input
                          type="text"
                          value={tick.label || ''}
                          onChange={(e) => {
                            const newTicks = [...customTicks];
                            newTicks[index].label = e.target.value;
                            setCustomTicks(newTicks);
                          }}
                          placeholder="Label"
                          className="flex-1 p-2 border rounded text-gray-800"
                        />
                        <button
                          onClick={() => {
                            setCustomTicks(customTicks.filter((_, i) => i !== index));
                          }}
                          className="px-2 text-red-500 hover:text-red-700"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                    <button
                      onClick={() => {
                        setCustomTicks([...customTicks, { position: 0, label: '', isMajor: true }]);
                      }}
                      className="text-blue-500 hover:text-blue-700 text-sm"
                    >
                      + Add Point
                    </button>
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setIsCreatingProject(false)}
                  className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateProject}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Create
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Project List */}
        <div className="flex-1 overflow-y-auto">
          {!isSidebarCollapsed && (
            <div className="px-4 py-2">
              <div className="text-sm text-gray-400 mb-2">Recent Projects</div>
              {projects.map((project) => (
                <div 
                  key={project.id}
                  className="group relative"
                >
                  <div 
                    className={`p-2 rounded-md cursor-pointer hover:bg-gray-700 ${selectedProject === project.id ? 'bg-gray-700' : ''}`}
                    onClick={() => setSelectedProject(project.id)}
                  >
                    {project.name}
                  </div>
                  <button
                    onClick={() => handleDeleteProject(project.id)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Title */}
        <header className="text-3xl font-bold text-gray-800 mt-4 ml-6">
          {selectedProject ? projects.find(p => p.id === selectedProject)?.name : 'Planner App'}
        </header>

        {selectedProject ? (
          <>
            {/* Main content area with timeline and canvases */}
            <div className="flex-1 flex flex-col">
              {/* Top canvas area */}
              <div 
                className="flex-1 bg-white border-b border-gray-200 shadow-inner relative"
                onDragOver={handleDragOver}
                onDrop={(e) => isDraggingPlacedCard ? handlePlacedCardDrop(e, 'top') : handleDrop(e, 'top')}
              >
                {placedCards
                  .filter(card => card.canvas === 'top')
                  .map(card => (
                    <div
                      key={card.id}
                      draggable
                      onDragStart={(e) => handlePlacedCardDragStart(e, card.id)}
                      onDragEnd={handlePlacedCardDragEnd}
                      className={`absolute cursor-move transition-shadow ${
                        draggedPlacedCardId === card.id ? 'opacity-50' : 'hover:shadow-lg'
                      } ${card.combinedCards ? 'ring-2 ring-blue-500' : ''}`}
                      style={{
                        left: card.position.x,
                        top: card.position.y,
                        transform: 'translate(-50%, -50%)'
                      }}
                    >
                      <Card type={card.type} content={card.content} />
                    </div>
                  ))}
              </div>

              {/* Timeline axis with drop zone */}
              <div 
                className="relative"
                onDragOver={handleDragOver}
                onDrop={handleAxisDrop}
              >
                <div className="absolute inset-0 bg-blue-50 opacity-0 hover:opacity-20 transition-opacity pointer-events-none" />
                <Timeline 
                  {...getTimelineConfig()}
                  leftMargin={60}
                  rightMargin={60}
                  events={projects.find(p => p.id === selectedProject)?.timelineEvents || []}
                  onEventDrop={handleEventDrop}
                />
              </div>

              {/* Bottom canvas area */}
              <div
                className="flex-1 bg-white border-t border-gray-200 shadow-inner relative"
                onDragOver={handleDragOver}
                onDrop={(e) => isDraggingPlacedCard ? handlePlacedCardDrop(e, 'bottom') : handleDrop(e, 'bottom')}
              >
                {placedCards
                  .filter(card => card.canvas === 'bottom')
                  .map(card => (
                    <div
                      key={card.id}
                      draggable
                      onDragStart={(e) => handlePlacedCardDragStart(e, card.id)}
                      onDragEnd={handlePlacedCardDragEnd}
                      className={`absolute cursor-move transition-shadow ${
                        draggedPlacedCardId === card.id ? 'opacity-50' : 'hover:shadow-lg'
                      } ${card.combinedCards ? 'ring-2 ring-blue-500' : ''}`}
                      style={{
                        left: card.position.x,
                        top: card.position.y,
                        transform: 'translate(-50%, -50%)'
                      }}
                    >
                      <Card type={card.type} content={card.content} />
                    </div>
                  ))}
              </div>
            </div>

            {/* Chat section */}
            <div className="border-t border-gray-200 bg-white shadow-lg">
              {/* Horizontal action card row */}
              <div className="px-4 pb-3">
                <div className="flex gap-4 overflow-x-auto py-4">
                  {cards.map((card, index) => (
                    <div
                      key={index}
                      draggable
                      onDragStart={() => handleDragStart(card)}
                      onDragEnd={handleDragEnd}
                      className="cursor-move"
                    >
                      <Card type={card.type} content={card.content} />
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Dropdown menu with actions */}
              <div className="flex justify-end px-10 pb-1 relative">
                <details className="group relative">
                  <summary className="flex items-center gap-1 cursor-pointer select-none text-sm text-gray-700 hover:text-gray-900">
                    Actions
                    <ChevronDownIcon className="w-4 h-4" />
                  </summary>

                  {/* Dropdown menu positioned above the button */}
                  <div className="absolute right-0 bottom-full mb-2 w-48 bg-white border border-gray-200 rounded-md shadow-lg z-50">
                    <button
                      onClick={() => console.log('Go Back')}
                      className="flex items-center gap-2 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <ArrowLeftCircleIcon className="w-5 h-5 text-blue-500" />
                      Go Back
                    </button>
                    <button
                      onClick={() => console.log('Go Forward')}
                      className="flex items-center gap-2 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <ArrowRightCircleIcon className="w-5 h-5 text-green-500" />
                      Go Forward
                    </button>
                    <button
                      onClick={() => console.log('Shuffle')}
                      className="flex items-center gap-2 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <ArrowPathIcon className="w-5 h-5 text-purple-500" />
                      Shuffle
                    </button>
                  </div>
                </details>
              </div>


              {/* Input box */}
              <div className="p-3 flex gap-2 px-10 border-t border-gray-100">
                <input
                  className="flex-1 border border-gray-200 text-black rounded-md px-4 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  placeholder="Type your message..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                />
                <button
                  className="bg-blue-600 text-white px-6 py-2 rounded-md text-sm hover:bg-blue-700 transition-colors shadow-md"
                  onClick={sendMessage}
                >
                  Send
                </button>
              </div>
            </div>
          </>
        ) : (
          // Landing Page
          <div className="flex-1 flex flex-col items-center justify-center p-8">
            <div className="max-w-2xl w-full text-center">
              <h1 className="text-4xl font-bold text-gray-800 mb-6">
                Welcome to Planner App
              </h1>
              <p className="text-gray-600 mb-8 text-lg">
                Create a new project or select an existing one to get started with your planning journey.
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Create New Project Card */}
                <div 
                  className="bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow cursor-pointer border-2 border-dashed border-gray-300 hover:border-blue-500"
                  onClick={() => setIsCreatingProject(true)}
                >
                  <div className="text-4xl mb-4 text-blue-500">+</div>
                  <h3 className="text-xl font-semibold text-gray-800 mb-2">Create New Project</h3>
                  <p className="text-gray-600">Start fresh with a new planning project</p>
                </div>

                {/* Recent Projects Card */}
                <div className="bg-white p-6 rounded-lg shadow-md">
                  <h3 className="text-xl font-semibold text-gray-800 mb-4">Recent Projects</h3>
                  <div className="space-y-3">
                    {projects.slice(0, 3).map((project) => (
                      <div
                        key={project.id}
                        className="p-3 rounded-md hover:bg-gray-50 cursor-pointer flex items-center justify-between"
                        onClick={() => setSelectedProject(project.id)}
                      >
                        <span className="text-gray-800">{project.name}</span>
                        <span className="text-gray-400 text-sm">
                          {project.createdAt.toLocaleDateString()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
