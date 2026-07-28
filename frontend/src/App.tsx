import { useState } from 'react';
import Landing from '@/pages/Landing';
import Dashboard from '@/pages/Dashboard';

export default function App() {
  const [route, setRoute] = useState<'/' | '/dashboard'>('/');

  if (route === '/dashboard') {
    return <Dashboard onHome={() => setRoute('/')} />;
  }
  return <Landing onEnter={() => setRoute('/dashboard')} />;
}
