import { useState, useEffect, useCallback } from 'react';
import {
  Search,
  TrendingUp,
  TrendingDown,
  Minus,
  Bookmark,
  BookmarkCheck,
  Share2,
  ExternalLink,
  ChevronUp,
  Clock,
  Flame,
  Filter,
  Bell,
  Settings,
  Menu,
  RefreshCw,
  Activity,
  PieChart,
  Eye,
  MessageSquare,
  Building2,
  Globe,
  Sparkles,
  ChevronRight,
  ChevronLeft,
  User,
  Home,
  Newspaper,
  Target,
  History,
} from 'lucide-react';
import { queryNews, fetchHealth, triggerRssFetch, fetchLatestNews, fetchTrendingNews, fetchPersonalizedFeed, type QueryResponse, type NewsArticle, type QueryResult } from './api';
import api from './api';

// LocalStorage keys
const BOOKMARKS_KEY = 'tradl_bookmarks';
const HISTORY_KEY = 'tradl_history';
const LAST_REFRESH_KEY = 'tradl_last_refresh';

// Types for new features
interface HeatmapData {
  sector: string;
  attention_score: number;
  article_count: number;
  sentiment_avg: number;
  trending: boolean;
}

interface Narrative {
  id: string;
  name: string;
  description: string;
  article_count: number;
  stocks: string[];
  sentiment: string;
}

// Sector color mapping
const sectorColors: Record<string, string> = {
  banking: 'sector-banking',
  finance: 'sector-banking',
  it: 'sector-it',
  technology: 'sector-it',
  pharma: 'sector-pharma',
  healthcare: 'sector-pharma',
  auto: 'sector-auto',
  automobile: 'sector-auto',
  energy: 'sector-energy',
  oil: 'sector-energy',
  fmcg: 'sector-fmcg',
  consumer: 'sector-fmcg',
  metals: 'sector-metals',
  mining: 'sector-metals',
};

const getSectorClass = (sector: string): string => {
  const normalized = sector.toLowerCase();
  for (const [key, value] of Object.entries(sectorColors)) {
    if (normalized.includes(key)) return value;
  }
  return 'sector-default';
};

// Feed tabs configuration
const feedTabs = [
  { id: 'for-you', label: 'For You', icon: Sparkles },
  { id: 'trending', label: 'Trending', icon: Flame },
  { id: 'latest', label: 'Latest', icon: Clock },
  { id: 'bullish', label: 'Bullish', icon: TrendingUp },
  { id: 'bearish', label: 'Bearish', icon: TrendingDown },
];

// Sidebar menu items
const sidebarItems = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'explore', label: 'Explore', icon: Globe },
  { id: 'bookmarks', label: 'Bookmarks', icon: Bookmark },
  { id: 'history', label: 'History', icon: History },
  { id: 'alerts', label: 'Alerts', icon: Bell },
];

// Skeleton card component
const SkeletonCard = () => (
  <div className="glass-card rounded-xl p-4 animate-fade-in">
    <div className="flex gap-3 mb-3">
      <div className="skeleton w-10 h-10 rounded-lg" />
      <div className="flex-1">
        <div className="skeleton h-4 w-24 mb-2" />
        <div className="skeleton h-3 w-16" />
      </div>
    </div>
    <div className="skeleton h-5 w-full mb-2" />
    <div className="skeleton h-5 w-3/4 mb-3" />
    <div className="skeleton h-16 w-full mb-3" />
    <div className="flex gap-2">
      <div className="skeleton h-6 w-16 rounded-full" />
      <div className="skeleton h-6 w-20 rounded-full" />
    </div>
  </div>
);

// Sentiment badge component
const SentimentBadge = ({ sentiment, score }: { sentiment: string; score?: number }) => {
  const config = {
    positive: { icon: TrendingUp, bgClass: 'bg-emerald-500/15', textClass: 'text-emerald-400', label: 'Bullish' },
    negative: { icon: TrendingDown, bgClass: 'bg-rose-500/15', textClass: 'text-rose-400', label: 'Bearish' },
    neutral: { icon: Minus, bgClass: 'bg-amber-500/15', textClass: 'text-amber-400', label: 'Neutral' },
  };
  const { icon: Icon, bgClass, textClass, label } = config[sentiment as keyof typeof config] || config.neutral;
  
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${bgClass} ${textClass}`}>
      <Icon size={12} />
      {label}
      {score !== undefined && <span className="opacity-75">({Math.round(score * 100)}%)</span>}
    </span>
  );
};

// Impact score ring component
const ImpactScoreRing = ({ score }: { score: number }) => {
  const circumference = 2 * Math.PI * 16;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 70 ? '#f43f5e' : score >= 40 ? '#fbbf24' : '#10b981';
  
  return (
    <div className="relative w-10 h-10">
      <svg className="transform -rotate-90 w-10 h-10">
        <circle cx="20" cy="20" r="16" stroke="#27272a" strokeWidth="3" fill="none" />
        <circle
          cx="20" cy="20" r="16"
          stroke={color}
          strokeWidth="3"
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="score-ring"
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-zinc-200">{score}</span>
    </div>
  );
};

// News card component
const NewsCard = ({ 
  article, 
  onBookmark, 
  isBookmarked,
  onUpvote,
  upvotes,
  hasUpvoted
}: { 
  article: NewsArticle; 
  relevance?: number;
  onBookmark: () => void;
  isBookmarked: boolean;
  onUpvote: () => void;
  upvotes: number;
  hasUpvoted: boolean;
}) => {
  const timeAgo = (date: string) => {
    const seconds = Math.floor((Date.now() - new Date(date).getTime()) / 1000);
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  const sector = article.entities?.sectors?.[0] || 'general';
  const impactScore = Math.round((article.sentiment_score || 0.5) * 100);

  return (
    <article className="glass-card card-lift rounded-xl p-4 group animate-slide-up">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center border ${getSectorClass(sector)}`}>
            <Building2 size={18} />
          </div>
          <div>
            <p className="text-sm font-medium text-zinc-300">{article.source}</p>
            <p className="text-xs text-zinc-500 flex items-center gap-1">
              <Clock size={10} />
              {timeAgo(article.published_at)}
            </p>
          </div>
        </div>
        <ImpactScoreRing score={impactScore} />
      </div>

      {/* Title */}
      <h3 className="text-base font-semibold text-zinc-100 mb-2 line-clamp-2 group-hover:text-cyan-400 transition-colors">
        {article.title}
      </h3>

      {/* Content preview */}
      <p className="text-sm text-zinc-400 line-clamp-3 mb-3">
        {article.content.substring(0, 200)}...
      </p>

      {/* Tags & sentiment */}
      <div className="flex flex-wrap gap-2 mb-3">
        <SentimentBadge sentiment={article.sentiment_label || 'neutral'} score={article.sentiment_score} />
        {article.entities?.sectors?.slice(0, 2).map((s) => (
          <span key={s} className={`px-2 py-0.5 rounded-full text-xs border ${getSectorClass(s)}`}>
            {s}
          </span>
        ))}
        {article.stock_impacts?.slice(0, 2).map((impact) => (
          <span 
            key={impact.stock_symbol}
            className="px-2 py-0.5 rounded-full text-xs bg-zinc-800 text-zinc-300 border border-zinc-700"
          >
            ${impact.stock_symbol}
          </span>
        ))}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between pt-3 border-t border-zinc-800">
        <div className="flex items-center gap-1">
          <button
            onClick={onUpvote}
            className={`upvote-btn flex items-center gap-1 px-2 py-1 rounded-lg text-sm ${hasUpvoted ? 'active' : 'text-zinc-400 hover:text-cyan-400'}`}
          >
            <ChevronUp size={18} />
            <span>{upvotes}</span>
          </button>
          <button className="p-2 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors">
            <MessageSquare size={16} />
          </button>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onBookmark}
            className={`bookmark-btn p-2 rounded-lg transition-colors ${isBookmarked ? 'active' : 'text-zinc-400 hover:text-zinc-200'}`}
          >
            {isBookmarked ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}
          </button>
          <button className="p-2 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors">
            <Share2 size={16} />
          </button>
          {article.url && (
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-lg text-zinc-400 hover:text-cyan-400 hover:bg-zinc-800 transition-colors"
            >
              <ExternalLink size={16} />
            </a>
          )}
        </div>
      </div>
    </article>
  );
};

// Heatmap card component
const HeatmapCard = ({ data }: { data: HeatmapData }) => {
  return (
    <div 
      className={`glass-card rounded-xl p-4 card-lift border ${getSectorClass(data.sector)}`}
      style={{ borderWidth: data.trending ? 2 : 1 }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-sm capitalize">{data.sector}</span>
        {data.trending && (
          <span className="flex items-center gap-1 text-xs text-amber-400">
            <Flame size={12} className="live-dot" />
            Hot
          </span>
        )}
      </div>
      <div className="text-2xl font-bold mb-1">{data.attention_score}%</div>
      <div className="flex items-center gap-2 text-xs text-zinc-400">
        <span>{data.article_count} articles</span>
        <span>•</span>
        <span className={data.sentiment_avg > 0 ? 'text-emerald-400' : data.sentiment_avg < 0 ? 'text-rose-400' : 'text-amber-400'}>
          {data.sentiment_avg > 0 ? '+' : ''}{(data.sentiment_avg * 100).toFixed(0)}% sentiment
        </span>
      </div>
    </div>
  );
};

// RAG Answer component
const RAGAnswer = ({ answer, metadata }: { answer: string; metadata?: QueryResponse['rag_metadata'] }) => (
  <div className="glass-card rounded-xl p-5 mb-6 border-l-4 border-cyan-500 animate-fade-in">
    <div className="flex items-center gap-2 mb-3">
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
        <Sparkles size={16} className="text-white" />
      </div>
      <div>
        <h3 className="font-semibold text-zinc-100">AI Analysis</h3>
        {metadata && (
          <p className="text-xs text-zinc-500">
            Powered by {metadata.provider} • {metadata.sources_used} sources • {metadata.llm_latency_ms}ms
          </p>
        )}
      </div>
    </div>
    <p className="text-zinc-300 leading-relaxed whitespace-pre-wrap">{answer}</p>
  </div>
);

// Main App
function App() {
  // State
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState('for-you');
  const [activePage, setActivePage] = useState('home');
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<QueryResult[]>([]);
  const [ragAnswer, setRagAnswer] = useState<string | null>(null);
  const [ragMetadata, setRagMetadata] = useState<QueryResponse['rag_metadata']>();
  const [bookmarks, setBookmarks] = useState<Set<string>>(new Set());
  const [searchHistory, setSearchHistory] = useState<QueryResult[]>([]);
  const [upvotes, setUpvotes] = useState<Record<string, number>>({});
  const [userUpvotes, setUserUpvotes] = useState<Set<string>>(new Set());
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [healthMessage, setHealthMessage] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
  const [lastRefreshTime, setLastRefreshTime] = useState<Date | null>(null);
  
  // Heatmap and narratives
  const [heatmapData, setHeatmapData] = useState<HeatmapData[]>([]);
  const [narratives, setNarratives] = useState<Narrative[]>([]);

  // Load bookmarks and history from localStorage
  useEffect(() => {
    const savedBookmarks = localStorage.getItem(BOOKMARKS_KEY);
    if (savedBookmarks) {
      setBookmarks(new Set(JSON.parse(savedBookmarks)));
    }
    const savedHistory = localStorage.getItem(HISTORY_KEY);
    if (savedHistory) {
      setSearchHistory(JSON.parse(savedHistory));
    }
    const savedRefreshTime = localStorage.getItem(LAST_REFRESH_KEY);
    if (savedRefreshTime) {
      setLastRefreshTime(new Date(savedRefreshTime));
    }
  }, []);

  // Save bookmarks to localStorage
  useEffect(() => {
    localStorage.setItem(BOOKMARKS_KEY, JSON.stringify(Array.from(bookmarks)));
  }, [bookmarks]);

  // Save history to localStorage
  useEffect(() => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(searchHistory.slice(0, 100)));
  }, [searchHistory]);

  // Health check
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetchHealth();
        setIsHealthy(response.data.status === 'healthy' || response.data.status === 'ok');
        setHealthMessage(`v${response.data.version}`);
      } catch (error: any) {
        setIsHealthy(false);
        setHealthMessage(error.response?.data?.detail || 'Backend unavailable');
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Fetch insights data
  useEffect(() => {
    const fetchInsights = async () => {
      try {
        // Fetch heatmap
        const heatmapRes = await api.get('/insights/heatmap');
        if (heatmapRes.data?.sectors) {
          setHeatmapData(heatmapRes.data.sectors);
        }
        // Fetch narratives
        const narrativesRes = await api.get('/insights/narratives');
        if (narrativesRes.data?.narratives) {
          setNarratives(narrativesRes.data.narratives);
        }
      } catch (error) {
        // Insights endpoints might not be available
        console.log('Insights not available:', error);
      }
    };
    fetchInsights();
  }, []);

  // Load feed based on active tab
  const loadFeed = useCallback(async (tab: string) => {
    setIsSearching(true);
    setRagAnswer(null);
    
    try {
      let response;
      switch (tab) {
        case 'for-you':
          response = await fetchPersonalizedFeed(20);
          break;
        case 'trending':
          response = await fetchTrendingNews(20);
          break;
        case 'latest':
          response = await fetchLatestNews(20);
          break;
        case 'bullish':
          response = await fetchLatestNews(20, 'positive');
          break;
        case 'bearish':
          response = await fetchLatestNews(20, 'negative');
          break;
        default:
          response = await fetchLatestNews(20);
      }
      
      setResults(response.data.results || []);
      if (response.data.synthesized_answer) {
        setRagAnswer(response.data.synthesized_answer);
        setRagMetadata(response.data.rag_metadata);
      }
      
      // Initialize upvotes
      const initialUpvotes: Record<string, number> = {};
      response.data.results?.forEach((r) => {
        initialUpvotes[r.article.id] = Math.floor(Math.random() * 50) + 5;
      });
      setUpvotes(initialUpvotes);
    } catch (error) {
      console.error('Feed load failed:', error);
    } finally {
      setIsSearching(false);
    }
  }, []);

  // Auto-refresh every 5 minutes
  useEffect(() => {
    if (!autoRefreshEnabled) return;
    
    const interval = setInterval(() => {
      if (activePage === 'home' && !searchQuery) {
        loadFeed(activeTab);
        setLastRefreshTime(new Date());
        localStorage.setItem(LAST_REFRESH_KEY, new Date().toISOString());
      }
    }, 5 * 60 * 1000); // 5 minutes
    
    return () => clearInterval(interval);
  }, [autoRefreshEnabled, activePage, activeTab, searchQuery, loadFeed]);

  // Load initial feed when tab changes
  useEffect(() => {
    if (activePage === 'home' && !searchQuery) {
      loadFeed(activeTab);
    }
  }, [activeTab, activePage, loadFeed, searchQuery]);

  // Search handler
  const handleSearch = useCallback(async (query: string = searchQuery) => {
    if (!query.trim()) return;
    
    setIsSearching(true);
    setRagAnswer(null);
    setActivePage('home'); // Switch to home when searching
    
    try {
      const response = await queryNews(query, 20);
      setResults(response.data.results || []);
      
      // Add to history
      if (response.data.results && response.data.results.length > 0) {
        setSearchHistory((prev) => {
          const newHistory = [...response.data.results!, ...prev];
          return newHistory.slice(0, 100); // Keep last 100
        });
      }
      
      if (response.data.synthesized_answer) {
        setRagAnswer(response.data.synthesized_answer);
        setRagMetadata(response.data.rag_metadata);
      }
      // Initialize upvotes
      const initialUpvotes: Record<string, number> = {};
      response.data.results?.forEach((r) => {
        initialUpvotes[r.article.id] = Math.floor(Math.random() * 50) + 5;
      });
      setUpvotes(initialUpvotes);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setIsSearching(false);
    }
  }, [searchQuery]);

  // Quick search tags
  const quickTags = [
    { label: 'RBI Policy', query: 'RBI monetary policy interest rates' },
    { label: 'Tech Earnings', query: 'technology sector earnings results' },
    { label: 'Market Movers', query: 'stocks gaining losing market movers' },
    { label: 'IPO News', query: 'IPO listing upcoming issues' },
    { label: 'Global Markets', query: 'global markets US Fed inflation' },
    { label: 'Commodities', query: 'gold oil crude commodity prices' },
  ];

  // Refresh handler
  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await triggerRssFetch();
      // Wait a bit for RSS to be processed
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      if (searchQuery) {
        await handleSearch();
      } else if (activePage === 'home') {
        await loadFeed(activeTab);
      }
      
      setLastRefreshTime(new Date());
      localStorage.setItem(LAST_REFRESH_KEY, new Date().toISOString());
    } catch (error) {
      console.error('Refresh failed:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Toggle handlers
  const toggleBookmark = (id: string) => {
    setBookmarks((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleUpvote = (id: string) => {
    setUserUpvotes((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
        setUpvotes((u) => ({ ...u, [id]: (u[id] || 0) - 1 }));
      } else {
        next.add(id);
        setUpvotes((u) => ({ ...u, [id]: (u[id] || 0) + 1 }));
      }
      return next;
    });
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-zinc-100 flex">
      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 h-full bg-zinc-900/95 backdrop-blur-xl border-r border-zinc-800 z-40 transition-all duration-300 ${
          sidebarCollapsed ? 'w-16' : 'w-64'
        } ${!sidebarOpen ? '-translate-x-full' : ''} lg:translate-x-0`}
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-zinc-800">
          {!sidebarCollapsed && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
                <Activity size={18} className="text-white" />
              </div>
              <span className="font-bold text-lg bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                Tradl AI
              </span>
            </div>
          )}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors hidden lg:block"
          >
            {sidebarCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>

        {/* Health status */}
        <div className={`px-4 py-3 border-b border-zinc-800 ${sidebarCollapsed ? 'hidden' : ''}`}>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isHealthy === null ? 'bg-zinc-500' : isHealthy ? 'bg-emerald-500 live-dot' : 'bg-rose-500'}`} />
            <span className="text-xs text-zinc-400">
              {isHealthy === null ? 'Connecting...' : isHealthy ? `Online ${healthMessage}` : healthMessage}
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-2 space-y-1">
          {sidebarItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActivePage(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                activePage === item.id
                  ? 'bg-cyan-500/10 text-cyan-400'
                  : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
              }`}
            >
              <item.icon size={20} />
              {!sidebarCollapsed && <span className="font-medium">{item.label}</span>}
            </button>
          ))}
        </nav>

        {/* Narratives section */}
        {!sidebarCollapsed && narratives.length > 0 && (
          <div className="px-4 py-3 border-t border-zinc-800 mt-4">
            <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">
              Active Narratives
            </h4>
            <div className="space-y-2">
              {narratives.slice(0, 3).map((narrative) => (
                <button
                  key={narrative.id}
                  onClick={() => {
                    setSearchQuery(narrative.name);
                    handleSearch(narrative.name);
                  }}
                  className="w-full text-left p-2 rounded-lg hover:bg-zinc-800 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Target size={14} className="text-purple-400" />
                    <span className="text-sm text-zinc-300 truncate">{narrative.name}</span>
                  </div>
                  <div className="text-xs text-zinc-500 mt-0.5">
                    {narrative.article_count} articles • {narrative.sentiment}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* User section */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-zinc-800">
          {!sidebarCollapsed ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                  <User size={16} className="text-white" />
                </div>
                <div>
                  <p className="text-sm font-medium text-zinc-200">Trader</p>
                  <p className="text-xs text-zinc-500">Pro Plan</p>
                </div>
              </div>
              <button className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors">
                <Settings size={18} />
              </button>
            </div>
          ) : (
            <button className="w-full flex justify-center p-2 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors">
              <User size={20} />
            </button>
          )}
        </div>
      </aside>

      {/* Main content */}
      <main className={`flex-1 transition-all duration-300 ${sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64'}`}>
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-[#0a0a0a]/80 backdrop-blur-xl border-b border-zinc-800">
          <div className="flex items-center justify-between h-16 px-4 lg:px-6">
            {/* Mobile menu button */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden p-2 rounded-lg hover:bg-zinc-800 text-zinc-400"
            >
              <Menu size={20} />
            </button>

            {/* Search bar */}
            <div className="flex-1 max-w-2xl mx-4">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500" size={18} />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="Search news, stocks, or ask a question..."
                  className="w-full h-11 pl-11 pr-4 rounded-xl bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 transition-all"
                />
                {isSearching && (
                  <RefreshCw className="absolute right-4 top-1/2 -translate-y-1/2 text-cyan-400 animate-spin" size={18} />
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleRefresh}
                disabled={isRefreshing}
                className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-zinc-400 hover:text-white transition-colors disabled:opacity-50"
                title={lastRefreshTime ? `Last refresh: ${lastRefreshTime.toLocaleTimeString()}` : 'Refresh news'}
              >
                <RefreshCw size={18} className={isRefreshing ? 'animate-spin' : ''} />
              </button>
              <button
                onClick={() => setAutoRefreshEnabled(!autoRefreshEnabled)}
                className={`p-2.5 rounded-lg border transition-colors ${
                  autoRefreshEnabled
                    ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400'
                    : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700 text-zinc-400 hover:text-white'
                }`}
                title={autoRefreshEnabled ? 'Auto-refresh enabled' : 'Auto-refresh disabled'}
              >
                <Activity size={18} className={autoRefreshEnabled ? 'live-dot' : ''} />
              </button>
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`p-2.5 rounded-lg border transition-colors ${
                  showFilters 
                    ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400' 
                    : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700 text-zinc-400 hover:text-white'
                }`}
              >
                <Filter size={18} />
              </button>
              <button className="relative p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-zinc-400 hover:text-white transition-colors">
                <Bell size={18} />
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-rose-500 rounded-full text-[10px] font-bold flex items-center justify-center text-white">
                  {bookmarks.size}
                </span>
              </button>
            </div>
          </div>

          {/* Feed tabs - only show on home page */}
          {activePage === 'home' && (
            <div className="flex items-center gap-1 px-4 lg:px-6 pb-3 overflow-x-auto">
              {feedTabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`feed-tab flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                    activeTab === tab.id
                      ? 'active text-cyan-400 bg-cyan-500/10'
                      : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
                  }`}
                >
                  <tab.icon size={16} />
                  {tab.label}
                </button>
              ))}
            </div>
          )}
        </header>

        {/* Content */}
        <div className="p-4 lg:p-6">
          {/* Page-specific content */}
          {activePage === 'bookmarks' && (
            <div>
              <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <Bookmark size={24} className="text-cyan-400" />
                Bookmarked Articles
              </h2>
              {bookmarks.size === 0 ? (
                <div className="text-center py-20">
                  <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 flex items-center justify-center">
                    <Bookmark size={40} className="text-cyan-400" />
                  </div>
                  <h3 className="text-xl font-semibold text-zinc-100 mb-2">
                    No bookmarks yet
                  </h3>
                  <p className="text-zinc-400">
                    Bookmark articles to read them later
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {results.filter(r => bookmarks.has(r.article.id)).map((result) => (
                    <NewsCard
                      key={result.article.id}
                      article={result.article}
                      relevance={result.relevance_score}
                      onBookmark={() => toggleBookmark(result.article.id)}
                      isBookmarked={true}
                      onUpvote={() => toggleUpvote(result.article.id)}
                      upvotes={upvotes[result.article.id] || 0}
                      hasUpvoted={userUpvotes.has(result.article.id)}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {activePage === 'history' && (
            <div>
              <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <History size={24} className="text-cyan-400" />
                Recent Activity
              </h2>
              {searchHistory.length === 0 ? (
                <div className="text-center py-20">
                  <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 flex items-center justify-center">
                    <History size={40} className="text-cyan-400" />
                  </div>
                  <h3 className="text-xl font-semibold text-zinc-100 mb-2">
                    No history yet
                  </h3>
                  <p className="text-zinc-400">
                    Your search history will appear here
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {searchHistory.slice(0, 30).map((result, idx) => (
                    <NewsCard
                      key={`${result.article.id}-${idx}`}
                      article={result.article}
                      relevance={result.relevance_score}
                      onBookmark={() => toggleBookmark(result.article.id)}
                      isBookmarked={bookmarks.has(result.article.id)}
                      onUpvote={() => toggleUpvote(result.article.id)}
                      upvotes={upvotes[result.article.id] || 0}
                      hasUpvoted={userUpvotes.has(result.article.id)}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {activePage === 'explore' && (
            <div>
              <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <Globe size={24} className="text-cyan-400" />
                Explore Markets
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                {['Banking', 'IT', 'Pharma', 'Auto', 'Energy', 'FMCG', 'Metals', 'Real Estate'].map((sector) => (
                  <button
                    key={sector}
                    onClick={() => {
                      setSearchQuery(`${sector} sector news analysis`);
                      handleSearch(`${sector} sector news analysis`);
                    }}
                    className={`p-4 rounded-xl glass-card card-lift border ${getSectorClass(sector.toLowerCase())}`}
                  >
                    <div className="font-semibold text-sm">{sector}</div>
                    <div className="text-xs opacity-75 mt-1">Explore sector</div>
                  </button>
                ))}
              </div>
              {results.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {results.map((result) => (
                    <NewsCard
                      key={result.article.id}
                      article={result.article}
                      relevance={result.relevance_score}
                      onBookmark={() => toggleBookmark(result.article.id)}
                      isBookmarked={bookmarks.has(result.article.id)}
                      onUpvote={() => toggleUpvote(result.article.id)}
                      upvotes={upvotes[result.article.id] || 0}
                      hasUpvoted={userUpvotes.has(result.article.id)}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {activePage === 'alerts' && (
            <div>
              <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <Bell size={24} className="text-cyan-400" />
                Price Alerts & Notifications
              </h2>
              <div className="glass-card rounded-xl p-8 text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 flex items-center justify-center">
                  <Bell size={32} className="text-cyan-400" />
                </div>
                <h3 className="text-xl font-semibold text-zinc-100 mb-2">
                  Set up alerts
                </h3>
                <p className="text-zinc-400 mb-4">
                  Get notified about important market movements
                </p>
                <button className="px-6 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-600 text-white font-medium transition-colors">
                  Create Alert
                </button>
              </div>
            </div>
          )}

          {/* Home page content */}
          {activePage === 'home' && (
            <>
              {/* Quick tags */}
              <div className="flex flex-wrap gap-2 mb-6">
                {quickTags.map((tag) => (
                  <button
                    key={tag.label}
                    onClick={() => {
                      setSearchQuery(tag.query);
                      handleSearch(tag.query);
                    }}
                    className="px-3 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-sm text-zinc-400 hover:text-white hover:border-zinc-700 transition-colors"
                  >
                    {tag.label}
                  </button>
                ))}
              </div>

          {/* Heatmap section */}
          {activePage === 'home' && heatmapData.length > 0 && !ragAnswer && (
            <div className="mb-6">
              <h2 className="flex items-center gap-2 text-lg font-semibold mb-4">
                <PieChart size={20} className="text-cyan-400" />
                Market Attention Heatmap
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {heatmapData.map((data) => (
                  <HeatmapCard key={data.sector} data={data} />
                ))}
              </div>
            </div>
          )}

          {/* RAG Answer */}
          {activePage === 'home' && ragAnswer && <RAGAnswer answer={ragAnswer} metadata={ragMetadata} />}

          {/* Loading state */}
          {activePage === 'home' && isSearching && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          )}

          {/* Results */}
          {activePage === 'home' && !isSearching && results.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">
                  {results.length} Results
                </h2>
                <div className="flex items-center gap-2 text-sm text-zinc-400">
                  <Eye size={16} />
                  <span>Relevance sorted</span>
                  {lastRefreshTime && (
                    <>
                      <span>•</span>
                      <span>Updated {new Date().getTime() - lastRefreshTime.getTime() < 60000 ? 'just now' : `${Math.floor((new Date().getTime() - lastRefreshTime.getTime()) / 60000)}m ago`}</span>
                    </>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {results.map((result) => (
                  <NewsCard
                    key={result.article.id}
                    article={result.article}
                    relevance={result.relevance_score}
                    onBookmark={() => toggleBookmark(result.article.id)}
                    isBookmarked={bookmarks.has(result.article.id)}
                    onUpvote={() => toggleUpvote(result.article.id)}
                    upvotes={upvotes[result.article.id] || 0}
                    hasUpvoted={userUpvotes.has(result.article.id)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Empty state */}
          {activePage === 'home' && !isSearching && results.length === 0 && (
            <div className="text-center py-20">
              <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 flex items-center justify-center">
                <Newspaper size={40} className="text-cyan-400" />
              </div>
              <h3 className="text-xl font-semibold text-zinc-100 mb-2">
                Your personalized news feed
              </h3>
              <p className="text-zinc-400 max-w-md mx-auto mb-6">
                Search for market news, stock movements, or ask questions about recent financial events.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {quickTags.slice(0, 3).map((tag) => (
                  <button
                    key={tag.label}
                    onClick={() => {
                      setSearchQuery(tag.query);
                      handleSearch(tag.query);
                    }}
                    className="px-4 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-sm text-cyan-400 hover:bg-zinc-800 transition-colors"
                  >
                    Try "{tag.label}"
                  </button>
                ))}
              </div>
            </div>
          )}
            </>
          )}
        </div>
      </main>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}

export default App;
