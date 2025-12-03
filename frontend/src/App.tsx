import { useState, useEffect } from 'react';
import { Search, RefreshCw, TrendingUp, TrendingDown, AlertCircle, CheckCircle2, Clock, Building2, Activity, Newspaper, BarChart3, Zap, Sparkles, Bot } from 'lucide-react';
import { queryNews, fetchHealth, triggerRssFetch, QueryResponse, HealthStatus } from './api';

function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [fetchingRss, setFetchingRss] = useState(false);

  useEffect(() => {
    fetchHealth()
      .then((res) => setHealth(res.data))
      .catch(() => setHealth(null));
  }, []);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await queryNews(query);
      setResults(res.data);
    } catch (err) {
      console.error('Search failed', err);
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshRss = async () => {
    setFetchingRss(true);
    try {
      await triggerRssFetch();
    } catch (err) {
      console.error('RSS fetch failed', err);
    } finally {
      setTimeout(() => setFetchingRss(false), 2000);
    }
  };

  const sentimentColor = (label?: string) => {
    if (!label) return 'bg-gray-100 text-gray-600';
    if (label === 'positive') return 'bg-emerald-100 text-emerald-700';
    if (label === 'negative') return 'bg-rose-100 text-rose-700';
    return 'bg-amber-100 text-amber-700';
  };

  const sentimentIcon = (label?: string) => {
    if (label === 'positive') return <TrendingUp className="w-3 h-3" />;
    if (label === 'negative') return <TrendingDown className="w-3 h-3" />;
    return <Activity className="w-3 h-3" />;
  };

  const quickSearches = ['HDFC Bank', 'Reliance', 'RBI policy', 'Banking sector', 'IT sector', 'TCS', 'Infosys'];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Animated Header */}
      <header className="bg-gradient-to-r from-slate-900 via-blue-900 to-indigo-900 text-white shadow-xl">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="absolute inset-0 bg-cyan-500 blur-xl opacity-50 animate-pulse"></div>
                <div className="relative bg-gradient-to-br from-cyan-400 to-blue-500 p-2.5 rounded-xl">
                  <Activity className="w-8 h-8 text-white" />
                </div>
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent">
                  Tradl AI
                </h1>
                <p className="text-blue-300 text-sm">Financial News Intelligence Platform</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              {health ? (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/20 border border-emerald-500/30 rounded-full">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  <span className="text-emerald-300 text-sm font-medium">Live</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-rose-500/20 border border-rose-500/30 rounded-full">
                  <AlertCircle className="w-4 h-4 text-rose-400" />
                  <span className="text-rose-300 text-sm">Offline</span>
                </div>
              )}
              
              <button
                onClick={handleRefreshRss}
                disabled={fetchingRss}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 disabled:from-gray-500 disabled:to-gray-600 rounded-lg font-medium text-sm transition-all duration-200 shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40"
              >
                <RefreshCw className={`w-4 h-4 ${fetchingRss ? 'animate-spin' : ''}`} />
                {fetchingRss ? 'Fetching...' : 'Fetch Live News'}
              </button>
            </div>
          </div>

          {/* Search Bar */}
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/20 to-purple-500/20 rounded-2xl blur-xl"></div>
            <div className="relative bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-2">
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    placeholder="Search news... (e.g., 'HDFC Bank dividend', 'RBI repo rate', 'Banking sector')"
                    className="w-full pl-12 pr-4 py-4 bg-white/10 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/50 transition-all"
                  />
                </div>
                <button
                  onClick={handleSearch}
                  disabled={loading}
                  className="px-8 py-4 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:from-gray-500 disabled:to-gray-600 rounded-xl font-semibold transition-all duration-200 flex items-center gap-2 shadow-lg"
                >
                  {loading ? (
                    <RefreshCw className="w-5 h-5 animate-spin" />
                  ) : (
                    <>
                      <Zap className="w-5 h-5" />
                      Search
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Quick Search Tags */}
          <div className="flex flex-wrap gap-2 mt-4">
            {quickSearches.map((tag) => (
              <button
                key={tag}
                onClick={() => { setQuery(tag); }}
                className="px-3 py-1.5 bg-white/10 hover:bg-white/20 border border-white/10 hover:border-white/30 rounded-full text-sm text-blue-200 hover:text-white transition-all"
              >
                {tag}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Stats Bar */}
      {results && results.analysis && (
        <div className="bg-white/80 backdrop-blur-sm border-b shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-6 text-sm">
              <div className="flex items-center gap-2">
                <Newspaper className="w-4 h-4 text-blue-600" />
                <span className="text-gray-500">Results:</span>
                <span className="font-bold text-gray-900">{results.total_count}</span>
              </div>
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-indigo-600" />
                <span className="text-gray-500">Intent:</span>
                <span className="font-medium text-indigo-700 capitalize">{results.analysis.intent.replace('_', ' ')}</span>
              </div>
            </div>
            {results.analysis.entities_detected?.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">Entities:</span>
                {results.analysis.entities_detected.map((e, i) => (
                  <span key={i} className="px-2 py-1 bg-gradient-to-r from-purple-100 to-indigo-100 text-purple-700 text-xs rounded-full font-medium">
                    {e}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* RAG AI Answer Section */}
        {results?.synthesized_answer && (
          <div className="mb-8 bg-gradient-to-r from-indigo-50 via-purple-50 to-pink-50 rounded-2xl border border-indigo-200 shadow-lg overflow-hidden">
            <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-5 py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-1.5 bg-white/20 rounded-lg">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <h3 className="text-white font-semibold">AI-Powered Answer</h3>
              </div>
              {results.rag_metadata && (
                <div className="flex items-center gap-3 text-xs text-indigo-200">
                  <span className="flex items-center gap-1">
                    <Bot className="w-3.5 h-3.5" />
                    {results.rag_metadata.provider}/{results.rag_metadata.model}
                  </span>
                  <span className="px-2 py-0.5 bg-white/10 rounded-full">
                    {results.rag_metadata.llm_latency_ms?.toFixed(0)}ms
                  </span>
                  <span className="px-2 py-0.5 bg-white/10 rounded-full">
                    {results.rag_metadata.sources_used} sources
                  </span>
                </div>
              )}
            </div>
            <div className="p-5">
              <div className="prose prose-indigo prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
                {results.synthesized_answer}
              </div>
            </div>
          </div>
        )}

        {results ? (
          (results.results?.length ?? 0) > 0 ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {results.results!.map((r, idx) => (
                <article 
                  key={idx} 
                  className="group bg-white rounded-2xl shadow-sm hover:shadow-xl border border-gray-100 hover:border-blue-200 transition-all duration-300 overflow-hidden"
                >
                  <div className="p-5">
                    {/* Card Header */}
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-1 bg-gradient-to-r from-blue-100 to-indigo-100 text-blue-700 text-xs font-semibold rounded-lg uppercase tracking-wide">
                          {r.article.source}
                        </span>
                        <span className="text-xs text-gray-400 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {new Date(r.article.published_at).toLocaleDateString()}
                        </span>
                      </div>
                      {r.article.sentiment_label && (
                        <span className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${sentimentColor(r.article.sentiment_label)}`}>
                          {sentimentIcon(r.article.sentiment_label)}
                          {r.article.sentiment_label}
                        </span>
                      )}
                    </div>

                    {/* Title */}
                    <h4 className="font-semibold text-gray-900 leading-snug mb-2 group-hover:text-blue-700 transition-colors line-clamp-2">
                      {r.article.title}
                    </h4>

                    {/* Content */}
                    <p className="text-sm text-gray-500 line-clamp-3 mb-4">
                      {r.article.content}
                    </p>

                    {/* Entities */}
                    {r.article.entities && (
                      <div className="flex flex-wrap gap-1.5 mb-4">
                        {r.article.entities.companies?.slice(0, 3).map((c, i) => (
                          <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 bg-purple-50 text-purple-700 text-xs rounded-full">
                            <Building2 className="w-3 h-3" />
                            {c.value}
                          </span>
                        ))}
                        {r.article.entities.sectors?.slice(0, 2).map((s, i) => (
                          <span key={i} className="px-2 py-0.5 bg-indigo-50 text-indigo-700 text-xs rounded-full">
                            {s}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Stock Impacts */}
                    {r.article.stock_impacts && r.article.stock_impacts.length > 0 && (
                      <div className="pt-3 border-t border-gray-100">
                        <div className="text-xs text-gray-400 mb-2">Impacted Stocks</div>
                        <div className="flex flex-wrap gap-1.5">
                          {r.article.stock_impacts.slice(0, 4).map((impact, i) => (
                            <span key={i} className="inline-flex items-center gap-1 px-2 py-1 bg-gray-50 rounded text-xs">
                              <span className="font-mono font-bold text-gray-800">{impact.stock_symbol}</span>
                              <span className={`w-1.5 h-1.5 rounded-full ${impact.confidence > 0.7 ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Relevance Score */}
                    <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-100">
                      <div className="flex items-center gap-2">
                        <div className="w-20 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full transition-all"
                            style={{ width: `${r.relevance_score * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-xs text-gray-500 font-medium">{Math.round(r.relevance_score * 100)}%</span>
                      </div>
                      {r.article.url && (
                        <a
                          href={r.article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:text-blue-800 font-medium transition-colors"
                        >
                          Read more →
                        </a>
                      )}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="text-center py-20">
              <div className="relative inline-block mb-6">
                <div className="absolute inset-0 bg-blue-500/20 blur-2xl rounded-full"></div>
                <div className="relative bg-gradient-to-br from-blue-100 to-indigo-100 p-6 rounded-2xl">
                  <Search className="w-12 h-12 text-blue-500" />
                </div>
              </div>
              <h3 className="text-xl font-semibold text-gray-800 mb-2">No results found</h3>
              <p className="text-gray-500 max-w-md mx-auto">
                Try a different search term or refresh the page.
              </p>
            </div>
          )
        ) : (
          <div className="text-center py-20">
            <div className="relative inline-block mb-6">
              <div className="absolute inset-0 bg-blue-500/20 blur-2xl rounded-full"></div>
              <div className="relative bg-gradient-to-br from-blue-100 to-indigo-100 p-6 rounded-2xl">
                <Search className="w-12 h-12 text-blue-500" />
              </div>
            </div>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">Search Financial News</h3>
            <p className="text-gray-500 max-w-md mx-auto">
              Enter a company name, sector, or topic to discover AI-analyzed news with entity extraction and stock impact mapping.
            </p>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t bg-white/50 backdrop-blur-sm mt-auto">
        <div className="max-w-7xl mx-auto px-4 py-4 text-center text-sm text-gray-500">
          <p>Tradl AI — Powered by LangGraph, ChromaDB & LangSmith</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
