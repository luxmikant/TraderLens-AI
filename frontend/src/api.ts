import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

export interface NewsArticle {
  id: string;
  title: string;
  content: string;
  source: string;
  url?: string;
  published_at: string;
  entities?: {
    companies: { value: string; confidence: number }[];
    sectors: string[];
  };
  stock_impacts?: {
    stock_symbol: string;
    company_name: string;
    impact_type: string;
    confidence: number;
  }[];
  sentiment_label?: string;
  sentiment_score?: number;
}

export interface QueryResult {
  article: NewsArticle;
  relevance_score: number;
}

export interface QueryResponse {
  results: QueryResult[];
  total_count: number;
  analysis: {
    intent: string;
    entities_detected: string[];
  };
  // RAG synthesis (AI-generated answer)
  synthesized_answer?: string;
  rag_metadata?: {
    model: string;
    provider: string;
    sources_used: number;
    llm_latency_ms: number;
  };
}

export interface HealthStatus {
  status: string;
  version: string;
  timestamp: string;
  components?: Record<string, { healthy: boolean; latency_ms: number; message?: string }>;
}

export const fetchHealth = () => api.get<HealthStatus>('/health');

export const queryNews = (query: string, limit = 10) =>
  api.post<QueryResponse>('/query', { query, limit });

export const ingestArticle = (article: {
  title: string;
  content: string;
  source: string;
  url?: string;
}) => api.post('/ingest', article);

export const triggerRssFetch = () => api.post('/ingest/rss');

export default api;
