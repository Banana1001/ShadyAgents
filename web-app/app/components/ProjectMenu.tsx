'use client';
import { useState, useRef, useEffect } from 'react';
import { downloadCalendar } from '../utils/calendar';
import { TimelineEvent } from '../types';
import { useAuth } from '../../contexts/AuthContext';
import { saveProjectStructure } from '../../services/firebase';

interface ProjectMenuProps {
  projectName: string;
  events: TimelineEvent[];
  projects: any[];
}

export default function ProjectMenu({ projectName, events, projects }: ProjectMenuProps) {
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleExportCalendar = () => {
    downloadCalendar(events, projectName);
    setIsOpen(false);
  };

  const handleSave = async () => {
    if (!user) return;
    setIsSaving(true);
    try {
      await saveProjectStructure(user.uid, projects);
    } catch (error) {
      console.error('Error saving:', error);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="relative flex items-center gap-4">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 hover:bg-gray-100 rounded-full transition-colors"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-600" viewBox="0 0 20 20" fill="currentColor">
          <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50">
          <button
            onClick={handleExportCalendar}
            className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
            </svg>
            Export Calendar
          </button>
        </div>
      )}

      <button
        onClick={handleSave}
        disabled={isSaving}
        className={`px-4 py-2 rounded-lg text-sm transition-all duration-200 ${
          isSaving
            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
            : 'bg-gradient-to-r from-blue-500 to-purple-500 text-white hover:from-blue-600 hover:to-purple-600 transform hover:-translate-y-0.5 shadow-lg hover:shadow-xl'
        }`}
      >
        {isSaving ? 'Saving...' : 'Save'}
      </button>
    </div>
  );
} 