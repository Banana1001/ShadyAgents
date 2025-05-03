import { initializeApp, getApps } from 'firebase/app';
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut } from 'firebase/auth';
import { getFirestore, doc, setDoc, getDoc } from 'firebase/firestore';
import { getAnalytics } from 'firebase/analytics';

const firebaseConfig = {
  apiKey: "AIzaSyA4opkqjkHbgenYEKXzXdW6VOj7w-5TGiw",
  authDomain: "shadyshades-a0891.firebaseapp.com",
  projectId: "shadyshades-a0891",
  storageBucket: "shadyshades-a0891.firebasestorage.app",
  messagingSenderId: "797276233107",
  appId: "1:797276233107:web:816adb5723fea6cce89c66",
  measurementId: "G-4EXLQ0ZCS8"
};

console.log('Initializing Firebase...');
// Initialize Firebase
const app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
console.log('Firebase app initialized:', app.name);

const analytics = typeof window !== 'undefined' ? getAnalytics(app) : null;
console.log('Analytics initialized:', analytics ? 'yes' : 'no');

export const auth = getAuth(app);
console.log('Auth initialized');

export const provider = new GoogleAuthProvider();
export const db = getFirestore(app);
console.log('Firestore initialized');

// Auth functions
export const loginWithGoogle = () => {
  console.log('Starting Google login...');
  return signInWithPopup(auth, provider);
};

export const logout = () => {
  console.log('Starting logout...');
  return signOut(auth);
};

// Helper to safely convert to ISO string
function safeToISOString(val: any) {
  if (val instanceof Date && !isNaN(val.getTime())) return val.toISOString();
  if (typeof val === 'string') {
    const d = new Date(val);
    if (!isNaN(d.getTime())) return d.toISOString();
  }
  return new Date().toISOString();
}

// Project functions
export async function saveProjectStructure(uid: string, projects: any) {
  try {
    console.log('Saving project structure for user:', uid);
    // Convert dates to ISO strings before saving
    const serializedProjects = projects.map((project: any) => ({
      ...project,
      createdAt: safeToISOString(project.createdAt),
      // Also handle any dates in timeline events
      timelineEvents: project.timelineEvents?.map((event: any) => ({
        ...event,
        time: safeToISOString(event.time)
      }))
    }));
    
    await setDoc(doc(db, 'users', uid), { projects: serializedProjects });
    console.log('Project structure saved successfully');
    return true;
  } catch (error) {
    console.error('Error saving project:', error);
    return false;
  }
}

export async function getProjectStructure(uid: string) {
  try {
    console.log('Getting project structure for user:', uid);
    const docSnap = await getDoc(doc(db, 'users', uid));
    console.log('Project structure retrieved:', docSnap.exists() ? 'exists' : 'not found');
    if (docSnap.exists()) {
      const projects = docSnap.data().projects;
      // Convert createdAt timestamps to Date objects
      return projects.map((project: any) => ({
        ...project,
        createdAt: project.createdAt ? new Date(project.createdAt) : new Date()
      }));
    }
    return [];
  } catch (error) {
    console.error('Error loading project:', error);
    return [];
  }
} 