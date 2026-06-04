import { ComponentType, ReactNode, SVGProps } from 'react';

export type Citation = {
  id: string;
  title: string;
  type: 'document' | 'data';
};

export type Action = {
  id: string;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  primary?: boolean;
};

export type Message = {
  id: string;
  role: 'user' | 'agent';
  content: string | ReactNode;
  timestamp?: string;
  citations?: Citation[];
  actions?: Action[];
  feedback?: 'like' | 'dislike' | null;
  showFeedbackInput?: boolean;
  feedbackText?: string;
  reported?: boolean;
};
