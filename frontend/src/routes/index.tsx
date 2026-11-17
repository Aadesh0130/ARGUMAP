import { createBrowserRouter, Navigate } from 'react-router-dom';
import { RootLayout } from '../layouts/RootLayout';
import { LandingPage } from '../pages/LandingPage';
import { AnalyzePage } from '../pages/AnalyzePage';
import { ProcessingPage } from '../pages/ProcessingPage';
import { ResultsPage } from '../pages/ResultsPage';
import { HowItWorksPage } from '../pages/HowItWorksPage';
import { TechnologyPage } from '../pages/TechnologyPage';
import { AboutPage } from '../pages/AboutPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    children: [
      {
        index: true,
        element: <LandingPage />,
      },
      {
        path: 'analyze',
        element: <AnalyzePage />,
      },
      {
        path: 'processing',
        element: <ProcessingPage />,
      },
      {
        path: 'results',
        element: <ResultsPage />,
      },
      {
        path: 'how-it-works',
        element: <HowItWorksPage />,
      },
      {
        path: 'technology',
        element: <TechnologyPage />,
      },
      {
        path: 'about',
        element: <AboutPage />,
      },
      {
        path: '*',
        element: <Navigate to="/" replace />,
      },
    ],
  },
]);
