# 🎬 Tradl AI Demo Script (7 Minutes)

## Setup Before Recording
```bash
# Terminal 1: Start Backend
cd "e:\lux pro\Tradl AI"
.\venv\Scripts\Activate.ps1
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start Frontend
cd frontend
npm run dev

# Browser: Open http://localhost:5173
```

---

## SCENE 1: Opening Hook (0:00-0:30)
**Screen**: Landing page with logo
**Script**:
> "Hi, I'm presenting Tradl AI - an intelligent financial news platform that transforms information overload into actionable insights using multi-agent AI. Let me show you how it works."

**Show**: Smooth scroll through homepage

---

## SCENE 2: The Problem (0:30-1:00)
**Screen**: Split screen - news websites vs. Tradl AI
**Script**:
> "Traders face a critical challenge - over 1000 articles daily from 50+ sources. Most are duplicates, lack context, and don't tell you which stocks are actually affected. Tradl AI solves this with 6 specialized AI agents working together."

**Visual Aid**: Show overwhelming news feeds on one side

---

## SCENE 3: Architecture (1:00-1:45)
**Screen**: Show `PROGRESS_REPORT.md` architecture section or draw.io diagram
**Script**:
> "Our system uses LangGraph to orchestrate 6 agents: 
> 1. Ingestion Agent fetches from RSS feeds
> 2. Dedup Agent eliminates 95% of duplicates using MinHash
> 3. NER Agent extracts companies, sectors, and regulators
> 4. Impact Agent maps news to stock tickers
> 5. Sentiment Agent uses FinBERT for financial sentiment
> 6. Storage Agent persists to ChromaDB vector database
>
> All of this happens in real-time, processing 100+ articles per minute."

**Transition**: Switch to live demo

---

## SCENE 4: Live Demo - Auto-Refresh (1:45-2:45)
**Action**: Click the refresh button
**Screen**: Show terminal logs + UI side-by-side

**Script**:
> "Watch this. I'll click refresh to fetch the latest financial news from Economic Times, MoneyControl, LiveMint, and NDTV Profit."

**Show in terminal**:
- RSS fetch starting
- "Running sentiment analysis on..." logs
- "Sentiment result: bullish (score: 0.923)"
- Articles appearing in UI

**Script (while loading)**:
> "In real-time, you can see each article being processed - deduplication, entity extraction, and sentiment analysis. Notice how FinBERT is scoring each article as bullish, bearish, or neutral."

**Highlight in UI**:
- Green badges (🟢 Bullish)
- Red badges (🔴 Bearish)
- Yellow badges (🟡 Neutral)
- Article count increasing

---

## SCENE 5: Intelligent Search (2:45-3:45)
**Action**: Type "HDFC Bank news" in search

**Script**:
> "Now let me show you the intelligent search. I'll search for HDFC Bank news."

**Show**:
- Search results appearing
- RAG synthesized answer at top
- Relevance scores (0.92, 0.87, 0.81)
- Entity highlights

**Script**:
> "Our RAG system doesn't just do keyword matching. It understands context. Notice the synthesized answer at the top - powered by Groq's Llama 3.1 model. It combines multiple sources into a coherent summary. You can also see relevance scores and why each article was matched."

**Click "Show Sources"**:
- Show source articles used for synthesis

**Try second query**: "RBI policy changes"
**Script**:
> "Let me try another query - RBI policy changes. Watch how it filters for regulator-specific news."

---

## SCENE 6: Sentiment Deep Dive (3:45-4:30)
**Action**: Click on a bullish article

**Script**:
> "Let me dive deeper into this bullish article about Reliance's quarterly earnings."

**Show**:
- Full article content
- Sentiment breakdown panel:
  - Bullish: 87%
  - Neutral: 10%
  - Bearish: 3%
- Stock impact list:
  - RELIANCE.NS (Confidence: 0.95)
  - NIFTY50 (Confidence: 0.72)
  - OIL (Confidence: 0.61)

**Script**:
> "FinBERT analyzes the financial tone with 85%+ accuracy. This article is 87% bullish. Below, you can see affected stocks with confidence scores. Reliance is directly mentioned, so confidence is 95%. Nifty 50 and Oil & Gas companies are indirectly affected."

---

## SCENE 7: Explore by Sector (4:30-5:00)
**Action**: Click "Explore" in sidebar

**Script**:
> "You can also explore by sector. Let's check what's happening in Banking."

**Click "Banking" button**:
- Feed updates with banking-only articles
- Show sector badge on each article

**Script**:
> "Now I'm seeing only Banking sector news - HDFC, ICICI, SBI, and RBI policy updates. Each article is tagged with relevant entities."

---

## SCENE 8: Feed Tabs & Bookmarks (5:00-5:45)
**Action**: Switch between feed tabs

**Script**:
> "Tradl AI has different feed views. For You gives personalized recommendations. Trending shows what's moving markets. Latest is real-time news. And you can filter by Bullish or Bearish sentiment."

**Click "Bullish" tab**:
- Show only green-badged articles

**Action**: Bookmark an article
**Script**:
> "I can bookmark important articles for later. Watch - I'll bookmark this TCS news."

**Click bookmark icon** → Article saved
**Navigate to "Bookmarks"** → Show saved article

**Script**:
> "All bookmarks are persisted locally, so they survive page refreshes."

---

## SCENE 9: Technical Highlights (5:45-6:30)
**Screen**: Show terminal logs + code snippets

**Script**:
> "Let's talk technical implementation. Under the hood, we're using:
> - **LangGraph** for multi-agent orchestration
> - **ChromaDB** for vector search with sentence-transformers embeddings
> - **FinBERT** for financial sentiment analysis
> - **Groq's Llama 3.1** for RAG synthesis
> - **FastAPI** backend with WebSocket support
> - **React + Tailwind** for the UI, inspired by daily.dev
>
> The entire system is type-safe with Pydantic models, includes Prometheus metrics, and has LangSmith tracing for observability."

**Show metrics**:
- Average query latency: 1.8s
- Dedup accuracy: 95%
- Articles processed today: 500+
- Auto-refresh interval: 5 minutes

---

## SCENE 10: What Makes It Different (6:30-7:00)
**Screen**: Feature comparison slide

**Script**:
> "What makes Tradl AI unique?
> 1. **Context-aware search** - Search for a company, get related sector news too
> 2. **Sentiment + Stock impact** in one view - No manual cross-referencing
> 3. **RAG synthesis** - Get the gist in seconds
> 4. **Real-time updates** - Always fresh data
> 5. **Beautiful UX** - Dark theme, smooth animations, intuitive navigation
>
> Most financial news platforms just aggregate links. We add intelligence."

---

## SCENE 11: Closing (7:00-7:30)
**Screen**: GitHub repo + Thank you slide

**Script**:
> "That's Tradl AI - transforming financial news into intelligent insights. The entire codebase is open source on GitHub. I've built this with LangGraph, ChromaDB, FinBERT, and modern web technologies. 
>
> Thank you for watching! Check out the GitHub repo for setup instructions and technical documentation."

**Show**:
- GitHub: `github.com/luxmikant/TraderLens-AI`
- Star the repo animation
- Fade to black

---

## 🎥 Recording Tips

### Camera & Audio
- Use 1920x1080 resolution
- Record at 30fps
- Clear audio (test microphone first)
- Speak at moderate pace (not too fast)

### Screen Layout
- **Option A**: Full screen browser (cleaner)
- **Option B**: Split screen (browser + terminal logs)
- Use browser zoom: 110% for better visibility

### Editing Checklist
- [ ] Remove long loading pauses (speed up 2x)
- [ ] Add captions for technical terms
- [ ] Smooth transitions between scenes
- [ ] Background music (low volume, non-distracting)
- [ ] Add "Skip to" timestamps in YouTube description
- [ ] Export at 1080p 60fps

### Common Mistakes to Avoid
- ❌ Don't show PostgreSQL errors (mention it's optional)
- ❌ Don't spend too long on any one feature
- ❌ Don't mumble or use filler words ("um", "uh")
- ❌ Don't show your face (unless confident on camera)

---

## 📊 Demo Queries to Prepare

### Good Demo Queries (Use These)
1. **"HDFC Bank news"** - Shows company + sector expansion
2. **"RBI policy changes"** - Shows regulator filtering
3. **"Reliance quarterly results"** - Shows high-confidence impact
4. **"Banking sector update"** - Shows sector-wide aggregation
5. **"Interest rate impact"** - Shows semantic theme matching

### Avoid These Queries
- Generic queries ("news", "update") - too broad
- Queries with no results - looks bad on demo
- Typos - make sure autocorrect is off

---

## ⏱️ Time Management

| Scene | Duration | Cumulative |
|-------|----------|------------|
| Opening | 0:30 | 0:30 |
| Problem | 0:30 | 1:00 |
| Architecture | 0:45 | 1:45 |
| Live Demo - Refresh | 1:00 | 2:45 |
| Intelligent Search | 1:00 | 3:45 |
| Sentiment Deep Dive | 0:45 | 4:30 |
| Explore by Sector | 0:30 | 5:00 |
| Feed Tabs | 0:45 | 5:45 |
| Technical Highlights | 0:45 | 6:30 |
| What Makes It Different | 0:30 | 7:00 |
| Closing | 0:30 | **7:30** |

**Buffer**: 2:30 minutes for unexpected delays

---

## 🚀 Pre-Recording Checklist

### Backend
- [ ] Backend running on port 8000
- [ ] FinBERT model loaded (check logs: "FinBERT model loaded successfully")
- [ ] ChromaDB has articles (run: `POST /ingest/rss` if empty)
- [ ] Groq API key is set (for RAG synthesis)
- [ ] LangSmith tracing enabled (optional, for observability)

### Frontend
- [ ] Frontend running on port 5173
- [ ] Browser cache cleared
- [ ] Bookmarks cleared (for fresh demo)
- [ ] Dark mode enabled
- [ ] Zoom level: 110% for better visibility
- [ ] Disable browser notifications

### Recording Software
- [ ] OBS Studio configured (1920x1080 @ 30fps)
- [ ] Microphone tested
- [ ] Screen area selected (full screen or window)
- [ ] Cursor highlighting enabled
- [ ] Noise suppression on

### Demo Data
- [ ] Fresh RSS articles ingested (<1 hour old)
- [ ] At least 20+ articles in feed
- [ ] Mix of bullish/bearish/neutral articles
- [ ] Multiple sectors represented

---

## 🎯 Success Criteria

Your demo video is successful if viewers can:
1. ✅ Understand the problem you're solving
2. ✅ See the system working in real-time
3. ✅ Appreciate the technical sophistication
4. ✅ Want to try it themselves

**Good luck with your demo!** 🚀
