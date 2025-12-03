"""
Real-time WebSocket Alerts for Breaking News

Features:
1. WebSocket server for push notifications
2. Alert priority levels (critical, high, normal)
3. Per-user subscription filters
4. Breaking news detection
5. Alert history and acknowledgment
"""
import asyncio
import logging
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from weakref import WeakSet

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class AlertPriority(str, Enum):
    """Alert priority levels"""
    CRITICAL = "critical"  # Breaking: Major corporate actions, market halts
    HIGH = "high"          # Important: Earnings, regulatory actions
    NORMAL = "normal"      # Standard: General news updates
    LOW = "low"            # FYI: Minor updates


class AlertType(str, Enum):
    """Types of alerts"""
    BREAKING_NEWS = "breaking_news"
    EARNINGS = "earnings"
    REGULATORY = "regulatory"
    PRICE_MOVEMENT = "price_movement"
    SENTIMENT_SHIFT = "sentiment_shift"
    NEW_CLUSTER = "new_cluster"


@dataclass
class NewsAlert:
    """Alert object for WebSocket notifications"""
    alert_id: str
    alert_type: AlertType
    priority: AlertPriority
    title: str
    summary: str
    symbols: List[str]
    sectors: List[str]
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    price_prediction: Optional[Dict] = None
    source: Optional[str] = None
    url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "priority": self.priority.value,
            "title": self.title,
            "summary": self.summary,
            "symbols": self.symbols,
            "sectors": self.sectors,
            "sentiment": self.sentiment,
            "sentiment_score": self.sentiment_score,
            "price_prediction": self.price_prediction,
            "source": self.source,
            "url": self.url,
            "created_at": self.created_at.isoformat()
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class AlertSubscription:
    """User subscription preferences"""
    websocket: WebSocket
    user_id: str
    symbols: Set[str] = field(default_factory=set)      # Empty = all symbols
    sectors: Set[str] = field(default_factory=set)      # Empty = all sectors
    min_priority: AlertPriority = AlertPriority.NORMAL
    alert_types: Set[AlertType] = field(default_factory=set)  # Empty = all types
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def matches_alert(self, alert: NewsAlert) -> bool:
        """Check if this subscription should receive the alert"""
        # Priority filter
        priority_order = [AlertPriority.LOW, AlertPriority.NORMAL, AlertPriority.HIGH, AlertPriority.CRITICAL]
        if priority_order.index(alert.priority) < priority_order.index(self.min_priority):
            return False
        
        # Alert type filter
        if self.alert_types and alert.alert_type not in self.alert_types:
            return False
        
        # Symbol filter (empty = all)
        if self.symbols:
            if not any(s in self.symbols for s in alert.symbols):
                return False
        
        # Sector filter (empty = all)
        if self.sectors:
            if not any(s in self.sectors for s in alert.sectors):
                return False
        
        return True


class AlertManager:
    """
    Manages WebSocket connections and alert distribution.
    
    Usage:
        manager = AlertManager()
        
        # In FastAPI endpoint
        @app.websocket("/ws/alerts")
        async def websocket_endpoint(websocket: WebSocket):
            await manager.connect(websocket, user_id="user123")
            try:
                while True:
                    data = await websocket.receive_text()
                    # Handle subscription updates
            except WebSocketDisconnect:
                manager.disconnect(websocket)
        
        # To send alerts
        await manager.broadcast_alert(alert)
    """
    
    def __init__(self):
        self.subscriptions: Dict[str, AlertSubscription] = {}  # user_id -> subscription
        self.websocket_to_user: Dict[WebSocket, str] = {}
        self.alert_history: List[NewsAlert] = []
        self.max_history = 1000
        self._lock = asyncio.Lock()
        
        logger.info("AlertManager initialized")
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        symbols: Optional[Set[str]] = None,
        sectors: Optional[Set[str]] = None,
        min_priority: AlertPriority = AlertPriority.NORMAL
    ):
        """Accept a new WebSocket connection and create subscription"""
        await websocket.accept()
        
        subscription = AlertSubscription(
            websocket=websocket,
            user_id=user_id,
            symbols=symbols if symbols is not None else set(),
            sectors=sectors if sectors is not None else set(),
            min_priority=min_priority
        )
        
        async with self._lock:
            self.subscriptions[user_id] = subscription
            self.websocket_to_user[websocket] = user_id
        
        logger.info(f"WebSocket connected: {user_id}")
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "message": "Connected to Tradl AI alerts"
        })
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        user_id = self.websocket_to_user.pop(websocket, None)
        if user_id:
            self.subscriptions.pop(user_id, None)
            logger.info(f"WebSocket disconnected: {user_id}")
    
    async def update_subscription(
        self,
        user_id: str,
        symbols: Optional[Set[str]] = None,
        sectors: Optional[Set[str]] = None,
        min_priority: Optional[AlertPriority] = None,
        alert_types: Optional[Set[AlertType]] = None
    ):
        """Update subscription preferences"""
        async with self._lock:
            if user_id in self.subscriptions:
                sub = self.subscriptions[user_id]
                if symbols is not None:
                    sub.symbols = symbols
                if sectors is not None:
                    sub.sectors = sectors
                if min_priority is not None:
                    sub.min_priority = min_priority
                if alert_types is not None:
                    sub.alert_types = alert_types
                
                logger.info(f"Updated subscription for {user_id}")
    
    async def broadcast_alert(self, alert: NewsAlert):
        """Send alert to all matching subscriptions"""
        async with self._lock:
            # Store in history
            self.alert_history.append(alert)
            if len(self.alert_history) > self.max_history:
                self.alert_history = self.alert_history[-self.max_history:]
        
        # Find matching subscriptions and send
        tasks = []
        disconnected = []
        
        for user_id, subscription in self.subscriptions.items():
            if subscription.matches_alert(alert):
                try:
                    task = subscription.websocket.send_json({
                        "type": "alert",
                        "data": alert.to_dict()
                    })
                    tasks.append(task)
                except Exception as e:
                    logger.error(f"Error sending to {user_id}: {e}")
                    disconnected.append(subscription.websocket)
        
        # Execute all sends concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Clean up disconnected
        for ws in disconnected:
            self.disconnect(ws)
        
        logger.info(f"Alert broadcast: {alert.title} to {len(tasks)} subscribers")
    
    async def send_to_user(self, user_id: str, alert: NewsAlert):
        """Send alert to specific user"""
        subscription = self.subscriptions.get(user_id)
        if subscription:
            try:
                await subscription.websocket.send_json({
                    "type": "alert",
                    "data": alert.to_dict()
                })
            except Exception as e:
                logger.error(f"Error sending to {user_id}: {e}")
                self.disconnect(subscription.websocket)
    
    def get_recent_alerts(
        self,
        limit: int = 50,
        symbols: Optional[List[str]] = None,
        priority: Optional[AlertPriority] = None
    ) -> List[Dict]:
        """Get recent alerts for REST API"""
        alerts = self.alert_history[-limit:]
        
        if symbols:
            symbols_set = set(s.upper() for s in symbols)
            alerts = [a for a in alerts if any(s.upper() in symbols_set for s in a.symbols)]
        
        if priority:
            priority_order = [AlertPriority.LOW, AlertPriority.NORMAL, AlertPriority.HIGH, AlertPriority.CRITICAL]
            min_idx = priority_order.index(priority)
            alerts = [a for a in alerts if priority_order.index(a.priority) >= min_idx]
        
        return [a.to_dict() for a in reversed(alerts)]
    
    @property
    def active_connections(self) -> int:
        """Number of active WebSocket connections"""
        return len(self.subscriptions)


class BreakingNewsDetector:
    """
    Detects breaking news that should trigger alerts.
    
    Criteria for breaking news:
    1. Keywords indicating urgency
    2. High sentiment magnitude
    3. Major companies/regulators mentioned
    4. Unusual time (off-market hours)
    """
    
    BREAKING_KEYWORDS = [
        "breaking", "urgent", "flash", "just in", "exclusive",
        "halted", "suspended", "banned", "crash", "surge",
        "record high", "record low", "all-time", "plunge",
        "acquisition", "merger", "takeover", "buyback",
        "fraud", "scam", "arrest", "resign", "fire"
    ]
    
    MAJOR_ENTITIES = {
        "companies": ["RELIANCE", "TCS", "HDFC", "ICICI", "INFOSYS", "SBI", "BHARTI"],
        "regulators": ["RBI", "SEBI", "IRDAI", "PFRDA", "MINISTRY OF FINANCE"],
        "indices": ["NIFTY", "SENSEX", "BANKNIFTY"]
    }
    
    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
        self._alert_counter = 0
    
    def _generate_alert_id(self) -> str:
        """Generate unique alert ID"""
        self._alert_counter += 1
        return f"ALT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._alert_counter:04d}"
    
    def detect_priority(
        self,
        title: str,
        content: str,
        sentiment_score: float,
        entities: Dict
    ) -> AlertPriority:
        """Determine alert priority based on content analysis"""
        text = f"{title} {content}".lower()
        
        # Check for breaking keywords
        breaking_count = sum(1 for kw in self.BREAKING_KEYWORDS if kw in text)
        
        # Check for major entities
        major_entity = False
        for entity_type, entities_list in self.MAJOR_ENTITIES.items():
            if any(e.upper() in text.upper() for e in entities_list):
                major_entity = True
                break
        
        # High sentiment magnitude
        high_sentiment = abs(sentiment_score) > 0.8
        
        # Determine priority
        if breaking_count >= 2 or (major_entity and high_sentiment):
            return AlertPriority.CRITICAL
        elif breaking_count >= 1 or major_entity or high_sentiment:
            return AlertPriority.HIGH
        elif abs(sentiment_score) > 0.5:
            return AlertPriority.NORMAL
        else:
            return AlertPriority.LOW
    
    def detect_alert_type(self, title: str, content: str) -> AlertType:
        """Detect the type of alert based on content"""
        text = f"{title} {content}".lower()
        
        if any(kw in text for kw in ["quarterly", "results", "profit", "revenue", "earnings", "eps"]):
            return AlertType.EARNINGS
        elif any(kw in text for kw in ["rbi", "sebi", "regulatory", "compliance", "penalty"]):
            return AlertType.REGULATORY
        elif any(kw in text for kw in ["surge", "plunge", "rally", "crash", "hit", "low", "high"]):
            return AlertType.PRICE_MOVEMENT
        elif any(kw in text for kw in ["breaking", "flash", "exclusive", "just in"]):
            return AlertType.BREAKING_NEWS
        else:
            return AlertType.NEW_CLUSTER
    
    async def process_article(
        self,
        title: str,
        content: str,
        symbols: List[str],
        sectors: List[str],
        sentiment_label: Optional[str] = None,
        sentiment_score: Optional[float] = None,
        price_prediction: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        url: Optional[str] = None
    ) -> Optional[NewsAlert]:
        """
        Process an article and create alert if warranted.
        
        Returns the alert if one was created, None otherwise.
        """
        # Determine priority
        priority = self.detect_priority(
            title, content,
            sentiment_score or 0.0,
            {"symbols": symbols, "sectors": sectors}
        )
        
        # Only alert for normal priority or higher
        if priority == AlertPriority.LOW:
            return None
        
        # Detect alert type
        alert_type = self.detect_alert_type(title, content)
        
        # Create summary
        summary = content[:200] + "..." if len(content) > 200 else content
        
        # Create alert
        alert = NewsAlert(
            alert_id=self._generate_alert_id(),
            alert_type=alert_type,
            priority=priority,
            title=title,
            summary=summary,
            symbols=symbols,
            sectors=sectors,
            sentiment=sentiment_label,
            sentiment_score=sentiment_score,
            price_prediction=price_prediction,
            source=source,
            url=url
        )
        
        # Broadcast
        await self.alert_manager.broadcast_alert(alert)
        
        return alert


# Singleton instances
_alert_manager: Optional[AlertManager] = None
_breaking_detector: Optional[BreakingNewsDetector] = None


def get_alert_manager() -> AlertManager:
    """Get or create the alert manager"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def get_breaking_detector() -> BreakingNewsDetector:
    """Get or create the breaking news detector"""
    global _breaking_detector
    if _breaking_detector is None:
        _breaking_detector = BreakingNewsDetector(get_alert_manager())
    return _breaking_detector
