// frontend/middleware.ts

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Define role-based routes
const roleRoutes = {
  admin: ['/dashboard', '/pc/', '/admin'],
  staff: ['/dashboard', '/pc/', '/admin'],
  player: ['/dashboard', '/reservations'],
};

const publicRoutes = ['/login', '/register', '/'];

export function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token')?.value;
  const role = request.cookies.get('role')?.value || 'player';
  const pathname = request.nextUrl.pathname;

  // Allow public routes
  if (publicRoutes.includes(pathname) || pathname === '/') {
    return NextResponse.next();
  }

  // Check if user is authenticated
  if (!token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Role-based access control
  if (pathname.startsWith('/pc/') || pathname.startsWith('/admin')) {
    if (role !== 'admin' && role !== 'staff') {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }
  }

  // Player specific routes
  if (pathname.startsWith('/reservations')) {
    if (role === 'admin' || role === 'staff') {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};