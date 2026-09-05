// frontend/middleware.ts

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Public routes (no authentication required)
const publicRoutes = ['/login', '/register', '/'];

export function middleware(request: NextRequest) {
  const token = request.cookies.get('cloud_access_token')?.value;
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

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico|.*\\.png$|.*\\.svg$).*)'],
};