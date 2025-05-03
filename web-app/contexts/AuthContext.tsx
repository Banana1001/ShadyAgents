'use client';
import { createContext, useContext, useEffect, useState } from 'react';
import { onAuthStateChanged, User } from 'firebase/auth';
import { auth } from '../services/firebase';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => {},
  logout: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    console.log('AuthProvider mounted');
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      console.log('Auth state changed:', user ? 'User logged in' : 'No user');
      setUser(user);
      setLoading(false);
    });
    return () => {
      console.log('AuthProvider cleanup');
      unsubscribe();
    };
  }, []);

  const login = async () => {
    try {
      console.log('Attempting login...');
      const { loginWithGoogle } = await import('../services/firebase');
      await loginWithGoogle();
      console.log('Login successful');
    } catch (error) {
      console.error('Error logging in:', error);
    }
  };

  const logout = async () => {
    try {
      console.log('Attempting logout...');
      const { logout } = await import('../services/firebase');
      await logout();
      console.log('Logout successful');
    } catch (error) {
      console.error('Error logging out:', error);
    }
  };

  console.log('AuthProvider render - loading:', loading, 'user:', user ? 'exists' : 'null');

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext); 