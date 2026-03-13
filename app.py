from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import asyncio
import os

from scraper import get_latest_fomc_text, get_recent_fomc_texts
from analyzer import FOMCAnalyzer

app = FastAPI(title="FedSentiment API")

# Initialize the analyzer model
try:
    analyzer = FOMCAnalyzer()
except Exception as e:
    print(f"Failed to load analyzer model on startup: {e}")
    analyzer = None

class AnalysisResult(BaseModel):
    status: str
    urls: list[str] | None = None
    aggregate_score: float | None = None
    sentiment_counts: dict | None = None
    total_sentences_analyzed: int | None = None
    highlights: list | None = None
    error: str | None = None

# Create static directory if it doesn't exist
os.makedirs("static", exist_ok=True)

@app.get("/api/analyze", response_model=AnalysisResult)
async def analyze_latest_meeting(limit: int = 5):
    try:
        # Step 1: Scrape the latest texts
        # The user has opted to allow unlimited documents, knowing it will take a while
        texts_and_urls = get_recent_fomc_texts(limit=limit)
        
        # Step 2: Analyze the text
        if analyzer is None:
            raise HTTPException(status_code=500, detail="Analyzer model failed to load.")
            
        analyses = []
        for text, url in texts_and_urls:
            # Extract date from URL (e.g., .../monetary20230726a.htm -> 2023-07-26)
            date_str = "Unknown Date"
            import re
            match = re.search(r'monetary(\d{4})(\d{2})(\d{2})', url)
            if match:
                date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                
            # Run synchronous analysis in a threadpool so it doesn't block the event loop
            analysis = await asyncio.to_thread(analyzer.analyze_text, text, url, date_str)
            if "error" not in analysis:
                analysis["url"] = url
                analyses.append(analysis)
                
        if not analyses:
            return AnalysisResult(status="error", error="Failed to analyze any statements.")
            
        total_weighted_score = 0
        total_weight = 0
        combined_sentiment_counts = {"Hawkish": 0, "Dovish": 0, "Neutral": 0}
        total_sentences = 0
        all_highlights = []
        
        for i, analysis in enumerate(analyses):
            base_weight = 5 - i # 5 for the most recent, 1 for the 5th most recent
            
            # Combine counts
            for k, v in analysis["sentiment_counts"].items():
                combined_sentiment_counts[k] += v
            total_sentences += analysis["total_sentences_analyzed"]
            all_highlights.extend(analysis["highlights"])
            
            # "If an entry has no hawkish or dovish sentiment, it should have no weight."
            doc_counts = analysis["sentiment_counts"]
            has_sentiment = doc_counts.get("Hawkish", 0) > 0 or doc_counts.get("Dovish", 0) > 0
            
            if has_sentiment:
                total_weighted_score += analysis["aggregate_score"] * base_weight
                total_weight += base_weight
                
        if total_weight > 0:
            final_score = total_weighted_score / total_weight
        else:
            final_score = 0.0
            
        all_highlights.sort(key=lambda x: abs(x["score"]), reverse=True)
        
        # Blend Hawkish and Dovish highlights
        hawkish_highlights = [h for h in all_highlights if h["sentiment"] == "Hawkish"]
        dovish_highlights = [h for h in all_highlights if h["sentiment"] == "Dovish"]
        
        # Get up to 3 of each to ensure a blend
        top_highlights = hawkish_highlights[:3] + dovish_highlights[:3]
        # Re-sort the combined list by absolute score intensity
        top_highlights.sort(key=lambda x: abs(x["score"]), reverse=True)
            
        return AnalysisResult(
            status="success",
            urls=[a["url"] for a in analyses] if analyses else None,
            aggregate_score=final_score,
            sentiment_counts=combined_sentiment_counts,
            total_sentences_analyzed=total_sentences,
            highlights=top_highlights
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return AnalysisResult(status="error", error=str(e))

# Mount the static directory to serve index.html
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
