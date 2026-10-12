import urllib.request, json
import urllib.parse
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QTextEdit, QGroupBox, QScrollArea, QFrame, QFormLayout
)
from PySide6.QtCore import Qt, QThread, Signal

class YouTubeSearchWorker(QThread):
    finished_signal = Signal(list, list) # tags, trending titles
    
    def __init__(self, query: str):
        super().__init__()
        self.query = query
        
    def run(self):
        try:
            # Simple YouTube autosuggest for tags/keywords
            url = f"http://suggestqueries.google.com/complete/search?client=youtube&ds=yt&client=firefox&q={urllib.parse.quote(self.query)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req)
            data = json.loads(response.read().decode('utf-8'))
            tags = data[1] if len(data) > 1 else []
            
            # Since scraping Youtube without API is hard, we simulate the top trends by just getting related queries
            # For a real implementation, you'd integrate YouTube Data API v3
            
            # Using another generic search for more ideas
            url2 = f"http://suggestqueries.google.com/complete/search?client=chrome&q={urllib.parse.quote(self.query + ' youtube')}"
            req2 = urllib.request.Request(url2, headers={'User-Agent': 'Mozilla/5.0'})
            response2 = urllib.request.urlopen(req2)
            data2 = json.loads(response2.read().decode('utf-8'))
            related = data2[1] if len(data2) > 1 else []
            
            self.finished_signal.emit(tags, related)
        except Exception as e:
            print(f"Research error: {e}")
            self.finished_signal.emit([], [])


class ResearchView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        header = QLabel("Live YouTube SEO & Topic Research")
        header.setObjectName("header")
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(header)
        
        form_card = QGroupBox("Keyword Research")
        form_card.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; margin-top: 10px; }")
        form_layout = QFormLayout(form_card)
        
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Enter a seed niche or topic (e.g. AI News, Business Scams)")
        form_layout.addRow("Topic:", self.query_input)
        
        self.btn_search = QPushButton("Analyze YouTube Trends")
        self.btn_search.clicked.connect(self._on_search)
        form_layout.addRow("", self.btn_search)
        
        layout.addWidget(form_card)
        
        # Results area
        results_card = QGroupBox("SEO Insights & Suggestions")
        results_card.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; margin-top: 10px; }")
        results_layout = QVBoxLayout(results_card)
        
        self.tags_out = QTextEdit()
        self.tags_out.setReadOnly(True)
        self.tags_out.setPlaceholderText("Trending search tags will appear here...")
        results_layout.addWidget(QLabel("🔥 Top Trending Search Queries (Tags):"))
        results_layout.addWidget(self.tags_out)
        
        self.titles_out = QTextEdit()
        self.titles_out.setReadOnly(True)
        self.titles_out.setPlaceholderText("Related Google/YouTube intent matches will appear here...")
        results_layout.addWidget(QLabel("📈 Related Topic Intents:"))
        results_layout.addWidget(self.titles_out)
        
        layout.addWidget(results_card)
        layout.addStretch()

    def _on_search(self):
        query = self.query_input.text().strip()
        if not query:
            return
        
        self.btn_search.setText("Searching...")
        self.btn_search.setEnabled(False)
        self.tags_out.clear()
        self.titles_out.clear()
        
        self.worker = YouTubeSearchWorker(query)
        self.worker.finished_signal.connect(self._on_results)
        self.worker.start()
        
    def _on_results(self, tags, titles):
        self.btn_search.setText("Analyze YouTube Trends")
        self.btn_search.setEnabled(True)
        
        if not tags and not titles:
            self.tags_out.setText("No data found or network error.")
            return
            
        self.tags_out.setText("\n".join(f"• {t}" for t in tags))
        self.titles_out.setText("\n".join(f"• {t}" for t in titles))

