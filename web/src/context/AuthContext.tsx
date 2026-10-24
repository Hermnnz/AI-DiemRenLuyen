import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../api/client';
import { User, Role, AuthResponse, ErrorResponse } from '../api/types';

interface AuthContextType {
  user: User | null;
  role: Role | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<User | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshUser = async (): Promise<User | null> => {
    try {
      const res = await api.get<AuthResponse>('/auth/me');
      if (res && res.user) {
        api.setCsrfToken(res.csrf_token);
        setUser(res.user);
        return res.user;
      }
      setUser(null);
      return null;
    } catch {
      api.setCsrfToken(null);
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();

    // Lắng nghe sự kiện 401 Unauthorized từ api client để xóa phiên
    const handleUnauthorized = () => {
      api.setCsrfToken(null);
      setUser(null);
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
    };
  }, []);

  const login = async (username: string, password: string): Promise<User> => {
    const res = await api.post<AuthResponse>('/auth/login', { username, password });
    if (!res || !res.user) {
      throw { error: { code: 'AUTH_FAILED', message: 'Đăng nhập không thành công', fields: {} } } as ErrorResponse;
    }
    api.setCsrfToken(res.csrf_token);
    setUser(res.user);
    return res.user;
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // Bỏ qua lỗi mạng khi logout
    } finally {
      api.setCsrfToken(null);
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role: user?.role || null,
        loading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
