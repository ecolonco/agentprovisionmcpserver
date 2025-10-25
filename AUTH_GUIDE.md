# 🔐 Guía de Autenticación y Gestión de Usuarios

## Sistema Completo de Autenticación en MCP Server

**El MCP Server incluye un sistema completo de autenticación** con registro, login, verificación de email y recuperación de contraseña.

### ✨ Características

- ✅ **Registro de usuarios** con validación de email
- ✅ **Login con JWT** tokens
- ✅ **Verificación de email** obligatoria
- ✅ **Recuperación de contraseña** (forgot password / reset)
- ✅ **Cambio de contraseña** para usuarios autenticados
- ✅ **Multi-tenant** - Usuarios separados por proyecto (TalleresIA, Eunacom, etc.)
- ✅ **Validación fuerte de contraseñas** (mayúscula, minúscula, número, 8+ caracteres)
- ✅ **Emails automáticos** con Gmail SMTP
- ✅ **Tokens con expiración** (24h para verificación, 1h para reset)
- ✅ **Audit logs** completos

---

## 🚀 Cliente TypeScript para TalleresIA

### **Paso 1: Crear Cliente de Autenticación**

Crea o actualiza `src/lib/auth-client.ts`:

```typescript
// src/lib/auth-client.ts

const MCP_API_URL = process.env.NEXT_PUBLIC_MCP_API_URL || 'http://localhost:8000/api/v1';
const TENANT = 'talleresia';

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    full_name: string;
    role: string;
    tenant: string;
    is_verified: boolean;
  };
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  phone: string | null;
  is_verified: boolean;
  is_active: boolean;
  role: string;
  tenant: string;
  created_at: string;
}

class AuthClient {
  private baseURL: string;
  private tenant: string;

  constructor(baseURL: string, tenant: string) {
    this.baseURL = baseURL;
    this.tenant = tenant;
  }

  /**
   * Registrar un nuevo usuario
   */
  async register(data: RegisterRequest): Promise<{ message: string; user_id: string; email: string }> {
    const response = await fetch(`${this.baseURL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant': this.tenant,
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registration failed');
    }

    return response.json();
  }

  /**
   * Login de usuario
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await fetch(`${this.baseURL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant': this.tenant,
      },
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    const data = await response.json();

    // Guardar token en localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
    }

    return data;
  }

  /**
   * Verificar email con token
   */
  async verifyEmail(token: string): Promise<{ message: string }> {
    const response = await fetch(`${this.baseURL}/auth/verify-email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ token }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Email verification failed');
    }

    return response.json();
  }

  /**
   * Reenviar email de verificación
   */
  async resendVerification(email: string): Promise<{ message: string }> {
    const response = await fetch(`${this.baseURL}/auth/resend-verification`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant': this.tenant,
      },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to resend verification');
    }

    return response.json();
  }

  /**
   * Solicitar recuperación de contraseña
   */
  async forgotPassword(email: string): Promise<{ message: string }> {
    const response = await fetch(`${this.baseURL}/auth/forgot-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant': this.tenant,
      },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to send password reset email');
    }

    return response.json();
  }

  /**
   * Resetear contraseña con token
   */
  async resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
    const response = await fetch(`${this.baseURL}/auth/reset-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ token, new_password: newPassword }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Password reset failed');
    }

    return response.json();
  }

  /**
   * Cambiar contraseña (usuario autenticado)
   */
  async changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${this.baseURL}/auth/change-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Password change failed');
    }

    return response.json();
  }

  /**
   * Obtener información del usuario actual
   */
  async getCurrentUser(): Promise<User> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${this.baseURL}/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch user');
    }

    return response.json();
  }

  /**
   * Logout (limpiar token local)
   */
  logout(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
    }
  }

  /**
   * Obtener token del localStorage
   */
  getToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('access_token');
    }
    return null;
  }

  /**
   * Verificar si el usuario está autenticado
   */
  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  /**
   * Obtener usuario guardado en localStorage
   */
  getStoredUser(): any | null {
    if (typeof window !== 'undefined') {
      const userStr = localStorage.getItem('user');
      return userStr ? JSON.parse(userStr) : null;
    }
    return null;
  }
}

// Exportar instancia configurada
export const authClient = new AuthClient(MCP_API_URL, TENANT);
```

---

## 💡 Ejemplos de Uso en TalleresIA

### **Ejemplo 1: Página de Registro**

```typescript
// src/app/register/page.tsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { authClient } from '@/lib/auth-client';

export default function RegisterPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    phone: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const result = await authClient.register(formData);
      setSuccess(result.message);

      // Redirigir a página de verificación
      setTimeout(() => {
        router.push('/verify-email');
      }, 2000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container mx-auto max-w-md p-8">
      <h1 className="text-3xl font-bold mb-6">Crear Cuenta</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
          {success}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Nombre Completo</label>
          <input
            type="text"
            required
            value={formData.full_name}
            onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
            className="w-full px-4 py-2 border rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Email</label>
          <input
            type="email"
            required
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            className="w-full px-4 py-2 border rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Contraseña</label>
          <input
            type="password"
            required
            minLength={8}
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            className="w-full px-4 py-2 border rounded-lg"
          />
          <p className="text-xs text-gray-500 mt-1">
            Mínimo 8 caracteres, debe incluir mayúscula, minúscula y número
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Teléfono (opcional)</label>
          <input
            type="tel"
            value={formData.phone}
            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
            className="w-full px-4 py-2 border rounded-lg"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg disabled:opacity-50"
        >
          {loading ? 'Registrando...' : 'Crear Cuenta'}
        </button>
      </form>

      <p className="text-center mt-4 text-sm text-gray-600">
        ¿Ya tienes cuenta?{' '}
        <a href="/login" className="text-blue-600 hover:underline">
          Inicia sesión
        </a>
      </p>
    </div>
  );
}
```

### **Ejemplo 2: Página de Login**

```typescript
// src/app/login/page.tsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { authClient } from '@/lib/auth-client';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const result = await authClient.login({ email, password });
      console.log('Login successful:', result.user);

      // Redirigir al dashboard
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container mx-auto max-w-md p-8">
      <h1 className="text-3xl font-bold mb-6">Iniciar Sesión</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-2 border rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Contraseña</label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-2 border rounded-lg"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg disabled:opacity-50"
        >
          {loading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
        </button>
      </form>

      <div className="mt-4 space-y-2 text-center text-sm">
        <p className="text-gray-600">
          ¿No tienes cuenta?{' '}
          <a href="/register" className="text-blue-600 hover:underline">
            Regístrate
          </a>
        </p>
        <p>
          <a href="/forgot-password" className="text-blue-600 hover:underline">
            ¿Olvidaste tu contraseña?
          </a>
        </p>
      </div>
    </div>
  );
}
```

### **Ejemplo 3: Verificación de Email**

```typescript
// src/app/verify-email/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { authClient } from '@/lib/auth-client';

export default function VerifyEmailPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');

    if (token) {
      // Verificar email con token de la URL
      authClient
        .verifyEmail(token)
        .then((result) => {
          setStatus('success');
          setMessage(result.message);

          // Redirigir al login después de 3 segundos
          setTimeout(() => {
            router.push('/login');
          }, 3000);
        })
        .catch((err) => {
          setStatus('error');
          setMessage(err.message);
        });
    } else {
      // No hay token, mostrar formulario para reenviar
      setStatus('error');
      setMessage('No se encontró token de verificación');
    }
  }, [searchParams, router]);

  if (status === 'loading') {
    return (
      <div className="container mx-auto max-w-md p-8 text-center">
        <div className="text-4xl mb-4">⏳</div>
        <p>Verificando tu email...</p>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="container mx-auto max-w-md p-8 text-center">
        <div className="text-6xl mb-4">✅</div>
        <h1 className="text-2xl font-bold mb-4">¡Email Verificado!</h1>
        <p className="text-gray-600 mb-4">{message}</p>
        <p className="text-sm text-gray-500">Serás redirigido al login...</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-md p-8">
      <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
        {message}
      </div>

      <p className="text-center">
        <a href="/register" className="text-blue-600 hover:underline">
          Volver al registro
        </a>
      </p>
    </div>
  );
}
```

### **Ejemplo 4: Recuperación de Contraseña**

```typescript
// src/app/forgot-password/page.tsx

'use client';

import { useState } from 'react';
import { authClient } from '@/lib/auth-client';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const result = await authClient.forgotPassword(email);
      setSuccess(result.message);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container mx-auto max-w-md p-8">
      <h1 className="text-3xl font-bold mb-6">Recuperar Contraseña</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
          {success}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-2 border rounded-lg"
            placeholder="tu@email.com"
          />
          <p className="text-xs text-gray-500 mt-1">
            Te enviaremos un enlace para restablecer tu contraseña
          </p>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg disabled:opacity-50"
        >
          {loading ? 'Enviando...' : 'Enviar Enlace de Recuperación'}
        </button>
      </form>

      <p className="text-center mt-4 text-sm text-gray-600">
        <a href="/login" className="text-blue-600 hover:underline">
          Volver al login
        </a>
      </p>
    </div>
  );
}
```

### **Ejemplo 5: Proteger Rutas (Middleware)**

```typescript
// src/middleware.ts

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token')?.value;

  // Rutas que requieren autenticación
  const protectedPaths = ['/dashboard', '/profile', '/settings'];

  const isProtectedPath = protectedPaths.some((path) =>
    request.nextUrl.pathname.startsWith(path)
  );

  if (isProtectedPath && !token) {
    // Redirigir al login si no está autenticado
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/profile/:path*', '/settings/:path*'],
};
```

---

## 🔄 Flujo Completo de Autenticación

```
┌──────────────────────────────────────────────────────────────┐
│           FLUJO COMPLETO DE AUTENTICACIÓN                     │
└──────────────────────────────────────────────────────────────┘

1. REGISTRO
   Usuario → TalleresIA → MCP Server
   │
   ▼
   MCP crea usuario (is_verified=false)
   │
   ▼
   MCP genera token de verificación (24h)
   │
   ▼
   MCP envía email con link: talleresia.cl/verify-email?token=abc123
   │
   ▼
2. VERIFICACIÓN
   Usuario hace clic en link del email
   │
   ▼
   TalleresIA → MCP /auth/verify-email
   │
   ▼
   MCP valida token y marca is_verified=true
   │
   ▼
3. LOGIN
   Usuario ingresa email + password
   │
   ▼
   TalleresIA → MCP /auth/login
   │
   ▼
   MCP valida credenciales y is_verified=true
   │
   ▼
   MCP retorna JWT token
   │
   ▼
   TalleresIA guarda token en localStorage
   │
   ▼
4. USO DE LA APP
   Usuario autenticado accede a recursos
   │
   ▼
   TalleresIA envía token en header Authorization
   │
   ▼
   MCP valida token y procesa request

RECUPERACIÓN DE CONTRASEÑA:
   Usuario → /forgot-password
   │
   ▼
   MCP genera token reset (1h) y envía email
   │
   ▼
   Usuario hace clic en link del email
   │
   ▼
   TalleresIA → MCP /reset-password
   │
   ▼
   MCP actualiza contraseña ✅
```

---

## ⚠️ Validación de Contraseñas

El sistema valida que las contraseñas cumplan:
- ✅ Mínimo 8 caracteres
- ✅ Al menos una mayúscula
- ✅ Al menos una minúscula
- ✅ Al menos un número

---

## 🧪 Testing con curl

### Registrar Usuario
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "X-Tenant: talleresia" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234",
    "full_name": "Usuario Prueba"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "X-Tenant: talleresia" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234"
  }'
```

### Obtener Usuario Actual
```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## ✅ Checklist de Implementación

- [ ] El MCP Server está corriendo
- [ ] Gmail SMTP está configurado
- [ ] Copiar `auth-client.ts` a TalleresIA
- [ ] Crear páginas de registro y login
- [ ] Crear página de verificación de email
- [ ] Crear página de recuperación de contraseña
- [ ] Configurar middleware para proteger rutas
- [ ] Probar flujo completo end-to-end
- [ ] Deploy en producción

---

¡El sistema de autenticación está listo para TalleresIA! 🔐✨
