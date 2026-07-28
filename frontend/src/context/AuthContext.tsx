import React, { createContext, useContext, useState, useEffect } from 'react';

const ADMIN_EMAIL = 'admin@gmail.com';
const ADMIN_PASSWORD = 'admin123';

const AuthContext = createContext<any>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Restore session from localStorage on page refresh
    console.log("AuthProvider mounted");
    try {
      const storedUser = localStorage.getItem('admin_user');
      console.log("Stored user found:", !!storedUser);
      if (storedUser) {
        setUser(JSON.parse(storedUser));
      }
    } catch (e) {
      console.error("Failed to parse stored user", e);
      localStorage.removeItem('admin_user');
    }
    console.log("Setting loading to false");
    setLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    if (email === ADMIN_EMAIL && password === ADMIN_PASSWORD) {
      const adminUser = { email: ADMIN_EMAIL, role: 'admin', name: 'Administrator' };
      localStorage.setItem('admin_user', JSON.stringify(adminUser));
      setUser(adminUser);
      return adminUser;
    } else {
      throw new Error('Invalid credentials. Access denied.');
    }
  };

  const logout = () => {
    localStorage.removeItem('admin_user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
