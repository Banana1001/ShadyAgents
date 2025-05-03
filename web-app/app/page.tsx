'use client';

import { useState, useRef, useEffect } from 'react';
import Timeline from './components/Timeline';
import Card, {CardProps} from './components/Card';
import ProjectMenu from './components/ProjectMenu';

// Remove unused timeline configurations
interface TimelineEvent {
  id: string;
  position: number;
  content: string;
  time: string;
  type: 'action' | 'idea' | 'combine';
  placement: 'above' | 'below';
  cost?: number; // Added cost property
  cards: Array<{
    id: string;
    content: string;
    type: 'action' | 'idea' | 'combine';
    time?: string;
    cost?: number;
  }>;
}

interface Project {
  id: string;
  name: string;
  createdAt: Date;
  description: string;
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
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true);
  const [projects, setProjects] = useState<Project[]>([]);
 
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDescription, setNewProjectDescription] = useState('');
  const [customTicks, setCustomTicks] = useState<Array<{ position: number; label?: string; isMajor?: boolean }>>([]);
  const [draggedCard, setDraggedCard] = useState<CardProps | null>(null);
  const [isDraggingPlacedCard, setIsDraggingPlacedCard] = useState(false);
  const [draggedPlacedCardId, setDraggedPlacedCardId] = useState<string | null>(null);
  const [heldCardId, setHeldCardId] = useState<string | null>(null);
  const holdTimerRef = useRef<NodeJS.Timeout | null>(null);
  const [isDraggingOverTrash, setIsDraggingOverTrash] = useState(false);
  const TRASH_DELETE_DISTANCE = 100; // Distance in pixels to trigger deletion

  const COMBINE_DISTANCE = 50; // Distance in pixels to trigger combination
  const AXIS_ZONE_HEIGHT = 40; // Height of the detection zone around the axis

  const [dragOverTarget, setDragOverTarget] = useState<{
    type: 'card' | 'event' | 'timeline' | null;
    id?: string;
  }>({ type: null });

  const sendMessage = async () => {
    if (!input.trim() || !selectedProject) return;

    const messageToSend = input;
    setInput(''); // Clear input immediately

    const newCard: CardProps = {
      id: Date.now().toString(),
      type: 'action',
      content: messageToSend,
    };

    // Update cards for the selected project
    setProjects(prevProjects => 
      prevProjects.map(project => 
        project.id === selectedProject
          ? { ...project, cards: [newCard] }
          : project
      )
    );
  };

  // server call of generating a plan for demo purposes
  const generatePlan = async(input: any) => {
    const res = await fetch('http://localhost:8000/generate-plan', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(input),
    });

    const data = await res.json();
    return (data.cards);
  };

  // server call of combining cards for demo purposes
  const combineTwoCards = async(input: any) => {
    const res = await fetch('http://localhost:8000/combine-cards', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(input),
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
        description: newProjectDescription.trim(),
        cards: [],
        placedCards: [],
        timelineEvents: []
      };
      setProjects([...projects, newProject]);
      setSelectedProject(newProject.id);
      setNewProjectName('');
      setNewProjectDescription('');
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
    return {
      leftMargin: 60,
      rightMargin: 60
    };
  };



  const handleDragStart = (card: CardProps) => {
    setDraggedCard(card);
  };

  const handleDragEnd = () => {
    setDraggedCard(null);
    setDragOverTarget({ type: null });
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

  const handleEventDrop = async (eventId: string, card: { type: 'action' | 'idea' | 'combine', content: string }) => {
    if (!selectedProject) return;

    const currentProject = projects.find(p => p.id === selectedProject);
    if (!currentProject) return;

    const event = currentProject.timelineEvents.find(c => c.id === eventId);
    const card1 = event?.cards[0];
    const card2 = card;
    const inputPayload = {
      Card1: {
        id: card1?.id || '',
        description: card1?.content || '',
        budget: card1?.cost || '',
        card_type: 'IdeaCard',
        time: card1?.time || '',
      },
      Card2: {
        id: '',
        card_type: 'CustomCard',
        user_query: card2.content,
      }
    };
    // Get new action cards from the agent
    const newCards = await combineTwoCards(inputPayload);
    
    const returnedCard = newCards[0];

    // Step 1: Replace the existing event with the new one
    const newEvent: TimelineEvent = {
      id: eventId,
      time: returnedCard.time,
      content: returnedCard.content,
      type: returnedCard.type as 'combine' | 'idea' | 'action',
      placement: currentProject.timelineEvents.find(e => e.id === eventId)?.placement || 'above',
      cards: [returnedCard],
      position: 0 // temporary, will be recalculated
    };

    // Step 2: Build a list of all events with the new one in place
    const updatedEventsUnpositioned = currentProject.timelineEvents.map(event =>
      event.id === eventId ? newEvent : event
    );

    // Step 3: Recalculate time-based positions
    const allCardsWithTime = updatedEventsUnpositioned
      .map(e => e.cards[0])
      .filter(c => (c.type === 'idea' || c.type === 'combine') && !!c.time);

    const times = allCardsWithTime.map(c => new Date(c.time!).getTime());
    const minTime = Math.min(...times);
    const maxTime = Math.max(...times);
    const timeRange = maxTime - minTime || 1;

    const updatedEvents = updatedEventsUnpositioned.map(event => {
      const time = event.cards[0]?.time;
      if (!time) return event;
      const cardTime = new Date(time).getTime();
      return {
        ...event,
        position: (cardTime - minTime) / timeRange
      };
    });

    // Step 4: Update state
    setProjects(prevProjects =>
      prevProjects.map(project =>
        project.id === selectedProject
          ? {
            ...project,
            timelineEvents: updatedEvents,
            cards: [],
            placedCards: project.placedCards.filter(c => c.id !== draggedPlacedCardId),
          }
          : project
      )
    );

    // Clear drag states
    setDraggedCard(null);
    setDraggedPlacedCardId(null);
    setIsDraggingPlacedCard(false);
    setDragOverTarget({ type: null });
  };

  const handleAxisDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    if (!selectedProject) return;

    const currentProject = projects.find(p => p.id === selectedProject);
    if (!currentProject) return;

    const dragged = draggedCard 
      ? draggedCard 
      : currentProject.placedCards.find(card => card.id === draggedPlacedCardId);

    if (dragged) {
      // Find if there's an existing event near the drop position
      const dropPosition = (e.clientX - e.currentTarget.getBoundingClientRect().left) / e.currentTarget.getBoundingClientRect().width;
      const existingEvent = currentProject.timelineEvents.find(event => 
        Math.abs(event.position - dropPosition) < 0.1
      );

      if (existingEvent) {
        // Get new action cards from the agent
        const card1 = existingEvent.cards[0];
        const card2 = dragged;
        const inputPayload = {
          Card1: {
            id: card1.id,
            description: card1?.content || '',
            budget: card1?.cost || '',
            card_type: 'IdeaCard',
            time: card1?.time || '',
          },
          Card2: {
            id: card2.id,
            card_type: 'CustomCard',
            user_query: card2.content,
          }
        };
        const newCards = await combineTwoCards(inputPayload);
        
        const returnedCard = newCards[0];

        // Step 1: Replace the existing event with the new one
        const newEvent: TimelineEvent = {
          id: existingEvent.id,
          time: returnedCard.time,
          content: returnedCard.content,
          type: returnedCard.type as 'combine' | 'idea' | 'action',
          cost: returnedCard.cost,
          placement: existingEvent.placement,
          cards: [returnedCard],
          position: 0 // temporary, will be recalculated
        };

        // Step 2: Build a list of all events with the new one in place
        const updatedEventsUnpositioned = currentProject.timelineEvents.map(event =>
          event.id === existingEvent.id ? newEvent : event
        );

        // Step 3: Recalculate time-based positions
        const allCardsWithTime = updatedEventsUnpositioned
          .map(e => e.cards[0])
          .filter(c => (c.type === 'idea' || c.type === 'combine') && !!c.time);

        const times = allCardsWithTime.map(c => new Date(c.time!).getTime());
        const minTime = Math.min(...times);
        const maxTime = Math.max(...times);
        const timeRange = maxTime - minTime || 1;

        const updatedEvents = updatedEventsUnpositioned.map(event => {
          const time = event.cards[0]?.time;
          if (!time) return event;
          const cardTime = new Date(time).getTime();
          return {
            ...event,
            position: (cardTime - minTime) / timeRange
          };
        });

        // Step 4: Update state
        setProjects(prevProjects =>
          prevProjects.map(project =>
            project.id === selectedProject
              ? {
                ...project,
                timelineEvents: updatedEvents,
                cards: [],
                placedCards: project.placedCards.filter(c => c.id !== draggedPlacedCardId),
              }
              : project
          )
        );

      } else {
        // Create a new event
        const newEvent: TimelineEvent = {
          id: Date.now().toString(),
          position: dropPosition,
          time: new Date().toISOString(),
          content: dragged.content,
          type: draggedCard?.type || 'action',
          placement: 'above',
          cards: []
        };

        // Get new action cards from the agent
        const cardList = currentProject.timelineEvents.flatMap(event => event.cards);
        const inputPayload = {
          Card: {
            id: dragged.id,
            user_query: dragged.content,
            card_type: 'CustomCard',
            time: dragged.time || '',
            budget: dragged.cost || '',
          },
          CardList: cardList.map(card => ({
            id: card.id,
            description: card.content,
            card_type: 'IdeaCard',
            time: card.time || '',
            budget: card.cost || '',
          }))
        };
        console.log('inputPayload', inputPayload);

        const newCards = await generatePlan(inputPayload);

        // Replace all previous timeline events
        const allTimes = newCards
          .filter((c: CardProps) => c.time)
          .map((c: CardProps) => new Date(c.time!).getTime());

        const minTime = Math.min(...allTimes);
        const maxTime = Math.max(...allTimes);
        const timeRange = maxTime - minTime || 1;

        const newTimelineEvents: TimelineEvent[] = newCards
          .filter((card: CardProps) => card.type === 'idea' && card.time)
          .map((card: CardProps, index: number) => {
            const time = new Date(card.time!).getTime();
            return {
              id: Date.now().toString() + index,
              position: (time - minTime) / timeRange,
              time: card.time,
              content: card.content,
              type: 'idea',
              cost: card.cost,
              placement: index % 2 === 0 ? 'above' : 'below',
              cards: [card],
            };
          });

        setProjects(prevProjects =>
          prevProjects.map(project =>
            project.id === selectedProject
              ? {
                ...project,
                timelineEvents: newTimelineEvents, // ✅ clear & replace
                cards: [],                         // ✅ clear all cards
                placedCards: [],                   // ✅ clear placed cards
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

  const handlePlacedCardDragStart = (e: React.DragEvent<HTMLDivElement>, cardId: string) => {
    setIsDraggingPlacedCard(true);
    setDraggedPlacedCardId(cardId);
    
    // Create a custom drag image
    const dragImage = e.currentTarget.cloneNode(true) as HTMLElement;
    dragImage.style.position = 'absolute';
    dragImage.style.top = '-1000px';
    dragImage.style.width = '250px'; // Match the card width
    document.body.appendChild(dragImage);
    
    // Set the drag image offset to be at the cursor position
    const rect = e.currentTarget.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const offsetY = e.clientY - rect.top;
    e.dataTransfer.setDragImage(dragImage, offsetX, offsetY);
    
    // Hide the original card
    e.currentTarget.style.opacity = '0';
    
    setTimeout(() => document.body.removeChild(dragImage), 0);
  };

  const handlePlacedCardDragEnd = (e: React.DragEvent<HTMLDivElement>) => {
    setIsDraggingPlacedCard(false);
    setDraggedPlacedCardId(null);
    setDragOverTarget({ type: null });
    // Restore the original card's opacity
    e.currentTarget.style.opacity = '1';
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

  const handleTrashDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingOverTrash(true);
  };

  const handleTrashDragLeave = () => {
    setIsDraggingOverTrash(false);
  };

  const handleTrashDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingOverTrash(false);
    
    if (!selectedProject || !draggedPlacedCardId) return;

    setProjects(prevProjects =>
      prevProjects.map(project =>
        project.id === selectedProject
          ? {
              ...project,
              placedCards: project.placedCards.filter(card => card.id !== draggedPlacedCardId)
            }
          : project
      )
    );
    setDraggedPlacedCardId(null);
    setIsDraggingPlacedCard(false);
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

  const handleCardDoubleClick = (card: CardProps, canvas: 'top' | 'bottom') => {
    if (!selectedProject) return;

    const currentProject = projects.find(p => p.id === selectedProject);
    if (!currentProject) return;

    // Calculate a random position within the canvas
    const x = Math.random() * (window.innerWidth - 300) + 150; // Keep away from edges
    const y = Math.random() * (window.innerHeight / 2 - 100) + 50; // Keep away from edges

    const newCard: PlacedCard = {
      ...card,
      id: Date.now().toString(),
      position: { x, y },
      canvas
    };

    setProjects(prevProjects => 
      prevProjects.map(project => 
        project.id === selectedProject
          ? {
              ...project,
              placedCards: [...project.placedCards, newCard]
            }
          : project
      )
    );
  };

  const handleCardMouseDown = (cardId: string) => {
    holdTimerRef.current = setTimeout(() => {
      setHeldCardId(cardId);
    }, 500); // Show trash can after 500ms of holding
  };

  const handleCardMouseUp = () => {
    if (holdTimerRef.current) {
      clearTimeout(holdTimerRef.current);
      holdTimerRef.current = null;
    }
    setHeldCardId(null);
  };

  const handleCardDelete = (cardId: string) => {
    if (!selectedProject) return;

    setProjects(prevProjects =>
      prevProjects.map(project =>
        project.id === selectedProject
          ? {
              ...project,
              placedCards: project.placedCards.filter(card => card.id !== cardId)
            }
          : project
      )
    );
    setHeldCardId(null);
  };

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      if (holdTimerRef.current) {
        clearTimeout(holdTimerRef.current);
      }
    };
  }, []);

  const handleCardDragOver = (e: React.DragEvent, cardId: string) => {
    e.preventDefault();
    setDragOverTarget({ type: 'card', id: cardId });
  };

  const handleEventDragOver = (e: React.DragEvent, eventId: string) => {
    e.preventDefault();
    setDragOverTarget({ type: 'event', id: eventId });
  };

  const handleTimelineDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOverTarget({ type: 'timeline' });
  };

  const handleDragLeave = () => {
    setDragOverTarget({ type: null });
  };

  return (
    <div className="flex h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      {/* Left Sidebar */}
      <div 
        className={`${isSidebarCollapsed ? 'w-16' : 'w-64'} bg-gradient-to-b from-gray-900 to-gray-800 text-white flex flex-col transition-all duration-300 ease-in-out shadow-xl`}
      >
        <div className="p-4 border-b border-gray-700/50 flex items-center justify-between">
          {!isSidebarCollapsed && <h2 className="text-xl font-semibold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">PlanCrafter</h2>}
          <button 
            onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            className="p-1 hover:bg-gray-700/50 rounded-full transition-all duration-200 hover:scale-110"
          >
            {isSidebarCollapsed ? '→' : '←'}
          </button>
        </div>
        
        {/* New Project Button - Only show when expanded */}
        {!isSidebarCollapsed && (
          <button 
            className="m-4 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white px-4 py-2 rounded-lg text-sm flex items-center justify-center gap-2 shadow-lg hover:shadow-xl transition-all duration-200 transform hover:-translate-y-0.5"
            onClick={() => setIsCreatingProject(true)}
          >
            <span className="text-lg">+</span> New Project
          </button>
        )}

        {/* Project List */}
        <div className="flex-1 overflow-y-auto">
          {!isSidebarCollapsed && (
            <div className="px-4 py-2">
              <div className="text-sm text-gray-400 mb-2 font-medium">Recent Plans</div>
              {projects.map((project) => (
                <div 
                  key={project.id}
                  className="group relative"
                >
                  <div 
                    className={`p-2 rounded-lg cursor-pointer hover:bg-gray-700/50 transition-all duration-200 ${
                      selectedProject === project.id ? 'bg-gradient-to-r from-blue-500/20 to-purple-500/20' : ''
                    }`}
                    onClick={() => setSelectedProject(project.id)}
                  >
                    {project.name}
                  </div>
                  <button
                    onClick={() => handleDeleteProject(project.id)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 transition-all duration-200"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Project Creation Modal - Moved outside sidebar */}
      {isCreatingProject && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[9999]">
          <div className="bg-white p-8 rounded-2xl w-96 shadow-2xl transform transition-all duration-300 scale-100">
            <h3 className="text-2xl font-semibold mb-6 text-black">Create New Project</h3>
            <input
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              placeholder="Project Name"
              className="w-full px-4 py-2 mb-4 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 text-black"
            />
            <textarea
              value={newProjectDescription}
              onChange={(e) => setNewProjectDescription(e.target.value)}
              placeholder="Project Description"
              className="w-full px-4 py-2 mb-4 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 min-h-[100px] resize-y text-black"
            />
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setIsCreatingProject(false)}
                className="px-6 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-all duration-200"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateProject}
                className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all duration-200 transform hover:-translate-y-0.5 shadow-lg hover:shadow-xl"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Title and Menu */}
        <div className="flex items-center justify-between mt-6 mx-8">
          <header className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            {selectedProject ? projects.find(p => p.id === selectedProject)?.name : 'PlanCrafter'}
          </header>
          {selectedProject && (
            <ProjectMenu
              projectName={projects.find(p => p.id === selectedProject)?.name || ''}
              events={projects.find(p => p.id === selectedProject)?.timelineEvents || []}
            />
          )}
        </div>

        {selectedProject ? (
          <>
            {/* Fixed Trash Can */}
            {isDraggingPlacedCard && (
              <div 
                className={`fixed top-4 left-1/2 transform -translate-x-1/2 z-50 transition-all duration-300 ${
                  isDraggingOverTrash ? 'scale-110' : 'scale-100'
                }`}
                onDragOver={handleTrashDragOver}
                onDragLeave={handleTrashDragLeave}
                onDrop={handleTrashDrop}
              >
                <div className={`p-4 rounded-full shadow-xl ${
                  isDraggingOverTrash 
                    ? 'bg-gradient-to-r from-red-500 to-pink-500 text-white' 
                    : 'bg-white text-gray-400'
                } transition-all duration-300`}>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>
            )}

            {/* Main content area with timeline and canvases */}
            <div className="flex-1 flex flex-col p-4">
              {/* Top canvas area */}
              <div 
                className="flex-1 bg-white/50 backdrop-blur-sm border border-gray-200/50 rounded-2xl shadow-inner relative overflow-hidden"
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
                      onMouseDown={() => handleCardMouseDown(card.id)}
                      onMouseUp={handleCardMouseUp}
                      onMouseLeave={handleCardMouseUp}
                      onDragOver={(e) => handleCardDragOver(e, card.id)}
                      onDragLeave={handleDragLeave}
                      className={`absolute cursor-move transition-all duration-200 ${
                        draggedPlacedCardId === card.id ? 'opacity-50 scale-95' : 'hover:scale-105'
                      } ${card.combinedCards ? 'ring-2 ring-blue-500' : ''} ${
                        dragOverTarget.type === 'card' && dragOverTarget.id === card.id ? 'ring-4 ring-green-500 scale-105' : ''
                      }`}
                      style={{
                        left: card.position.x,
                        top: card.position.y,
                        transform: 'translate(-50%, -50%)'
                      }}
                    >
                      <Card
                        id={card.id}
                        type="action"
                        content={card.content}
                        onDoubleClick={() => handleCardDoubleClick(card, 'top')}
                      />
                    </div>
                  ))}
              </div>

              {/* Timeline axis with drop zone */}
              <div 
                className={`relative mx-6 my-4 rounded-2xl border border-gray-200/50 bg-white/50 backdrop-blur-sm shadow-lg z-50 transition-all duration-200 ${
                  dragOverTarget.type === 'timeline' ? 'ring-4 ring-green-500 scale-105' : ''
                }`}
                onDragOver={handleTimelineDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleAxisDrop}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-blue-50 to-purple-50 opacity-0 hover:opacity-100 transition-opacity pointer-events-none rounded-2xl" />
                <div className="relative">
                  <Timeline 
                    {...getTimelineConfig()}
                    events={projects.find(p => p.id === selectedProject)?.timelineEvents || []}
                    onEventDrop={handleEventDrop}
                    dragOverTarget={dragOverTarget}
                    onEventDragOver={handleEventDragOver}
                    onEventDragLeave={handleDragLeave}
                  />
                </div>
              </div>

              {/* Bottom canvas area */}
              <div
                className="flex-1 bg-white/50 backdrop-blur-sm border border-gray-200/50 rounded-2xl shadow-inner relative overflow-hidden"
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
                      onMouseDown={() => handleCardMouseDown(card.id)}
                      onMouseUp={handleCardMouseUp}
                      onMouseLeave={handleCardMouseUp}
                      onDragOver={(e) => handleCardDragOver(e, card.id)}
                      onDragLeave={handleDragLeave}
                      className={`absolute cursor-move transition-all duration-200 ${
                        draggedPlacedCardId === card.id ? 'opacity-50 scale-95' : 'hover:scale-105'
                      } ${card.combinedCards ? 'ring-2 ring-blue-500' : ''} ${
                        dragOverTarget.type === 'card' && dragOverTarget.id === card.id ? 'ring-4 ring-green-500 scale-105' : ''
                      }`}
                      style={{
                        left: card.position.x,
                        top: card.position.y,
                        transform: 'translate(-50%, -50%)'
                      }}
                    >
                      <Card
                        id={card.id}
                        type="idea"
                        content={card.content}
                        onDoubleClick={() => handleCardDoubleClick(card, 'bottom')}
                      />
                    </div>
                  ))}
              </div>
            </div>

            {/* Chat section */}
            <div className="bg-white/80 backdrop-blur-sm shadow-xl rounded-t-2xl">
              {/* Horizontal action card row */}
              <div className="px-6 pb-4">
                <div className="flex gap-4 overflow-x-auto py-4 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
                  {cards.map((card, index) => (
                    <div
                      key={index}
                      draggable
                      onDragStart={() => handleDragStart(card)}
                      onDragEnd={handleDragEnd}
                      className="cursor-move transition-transform duration-200 hover:scale-105"
                    >
                      <Card
                        id={card.id}
                        type="action"
                        content={card.content}
                        onDoubleClick={() => handleCardDoubleClick(card, 'top')}
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Input box */}
              <div className="p-4 flex gap-3 px-8 border-t border-gray-100">
                <input
                  className="flex-1 border border-gray-200 text-black rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 shadow-inner"
                  placeholder="Enter your input..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                />
                <button
                  className="bg-gradient-to-r from-blue-500 to-purple-500 text-white px-8 py-3 rounded-xl text-sm hover:from-blue-600 hover:to-purple-600 transition-all duration-200 transform hover:-translate-y-0.5 shadow-lg hover:shadow-xl"
                  onClick={sendMessage}
                >
                  Create
                </button>
              </div>
            </div>
          </>
        ) : (
          // Landing Page
          <div className="flex-1 flex flex-col items-center justify-center p-8">
            <div className="max-w-3xl w-full text-center">
              <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-6">
                Welcome to PlanCrafter
              </h1>
              <p className="text-gray-600 mb-12 text-xl">
                Create a new project or select an existing one to get started with your planning journey.
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Create New Project Card */}
                <div 
                  className="bg-white/80 backdrop-blur-sm p-8 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 cursor-pointer border-2 border-dashed border-gray-300 hover:border-blue-500 transform hover:-translate-y-1"
                  onClick={() => setIsCreatingProject(true)}
                >
                  <div className="text-5xl mb-6 text-blue-500">+</div>
                  <h3 className="text-2xl font-semibold text-gray-800 mb-3">Create New Project</h3>
                  <p className="text-gray-600 text-lg">Start fresh with a new planning project</p>
                </div>

                {/* Recent Projects Card */}
                <div className="bg-white/80 backdrop-blur-sm p-8 rounded-2xl shadow-xl">
                  <h3 className="text-2xl font-semibold text-gray-800 mb-6">Recent Projects</h3>
                  <div className="space-y-4">
                    {projects.slice(0, 3).map((project) => (
                      <div
                        key={project.id}
                        className="p-4 rounded-xl hover:bg-gray-50/50 cursor-pointer flex items-center justify-between transition-all duration-200 transform hover:-translate-y-0.5"
                        onClick={() => setSelectedProject(project.id)}
                      >
                        <span className="text-gray-800 font-medium">{project.name}</span>
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
