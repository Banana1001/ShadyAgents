'use client';

import { useState } from 'react';
import Timeline from './components/Timeline';
import Card, {CardProps} from './components/Card';

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
}

export default function Home() {
  const [input, setInput] = useState('');
  const [cards, setCards] = useState<CardProps[]>([]);
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [projects, setProjects] = useState<Project[]>([
    { 
      id: '1', 
      name: 'Project Alpha', 
      createdAt: new Date(),
      timelineType: 'hours'
    },
    { 
      id: '2', 
      name: 'Project Beta', 
      createdAt: new Date(),
      timelineType: 'days'
    },
    { 
      id: '3', 
      name: 'Project Gamma', 
      createdAt: new Date(),
      timelineType: 'months'
    },
  ]);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectTimelineType, setNewProjectTimelineType] = useState<'hours' | 'days' | 'months' | 'custom'>('hours');
  const [customTicks, setCustomTicks] = useState<Array<{ position: number; label?: string; isMajor?: boolean }>>([]);

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

  const handleCreateProject = () => {
    if (newProjectName.trim()) {
      const newProject: Project = {
        id: Date.now().toString(),
        name: newProjectName.trim(),
        createdAt: new Date(),
        timelineType: newProjectTimelineType,
        ...(newProjectTimelineType === 'custom' && { customTicks })
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

  return (
    <div className="flex h-screen bg-gray-100">
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
              <div className="flex-1 bg-white border-b border-gray-200">
              </div>

              {/* Timeline axis */}
              <Timeline 
                {...getTimelineConfig()}
                leftMargin={60}
                rightMargin={60}
              />

              {/* Bottom canvas area */}
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={async (e) => {
                  e.preventDefault();
                  const data = e.dataTransfer.getData('text/plain');
                  try {
                    const droppedCard = JSON.parse(data);
                    // Optional: store or visualize the dropped card

                    // Trigger LLM response
                    const newCards = await fakeAgentCall(`Dropped card: ${droppedCard.content}`);
                    setCards(newCards);
                  } catch (err) {
                    console.error('Invalid drop payload:', err);
                  }
                }}
                className="flex-1 bg-white border-t border-gray-200"
              >
                {/* This area is now a drop target */}
              </div>
            </div>

            {/* Chat section */}
            <div className="border-t border-gray-200">
              {/* Display response */}
              {/* Horizontal action card row */}
              <div className="px-4 pb-3">
                <div className="flex gap-4 justify-center flex-wrap">
                  {cards.map((card, index) => (
                    <Card key={index} type={card.type} content={card.content} />
                  ))}
                </div>
              </div>

              {/* Input box */}
              <div className="p-3 flex gap-2 px-10">
                <input
                  className="flex-1 border text-black rounded-md px-3 py-2 text-sm outline-none"
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
