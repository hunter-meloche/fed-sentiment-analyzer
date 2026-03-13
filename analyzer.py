from transformers import pipeline
import nltk
import ssl

# Bypass SSL verification for NLTK download if needed
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Download punkt tokenizer for sentence splitting
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)

class FOMCAnalyzer:
    def __init__(self, model_name="ProsusAI/finbert"):
        print(f"Loading robust financial NLP model {model_name}... This may take a moment.")
        # We use ProsusAI/finbert because it successfully classifies rate hikes as 'positive' (Hawkish)
        # and rate cuts/struggles as 'negative' (Dovish). And handles procedural text as 'neutral'.
        self.classifier = pipeline("text-classification", model=model_name)
        print("Model loaded successfully.")
        
    def map_label(self, label):
        """Helper to return human label and numeric score based on model label."""
        # Positive in FinBERT implies economic strength (Hawkish / Raising rates)
        # Negative implies economic weakness (Dovish / Cutting rates)
        if label == "negative":
            return "Dovish", -1.0
        elif label == "positive":
            return "Hawkish", 1.0
        else:
            return "Neutral", 0.0

    def analyze_text(self, text, source_url=None, source_date=None):
        """
        Analyzes a long FOMC text by splitting it into sentences.
        Returns aggregate scores and detailed sentence analysis.
        """
        # Split text into sentences since RoBERTa has a 512 token limit
        sentences = nltk.tokenize.sent_tokenize(text)
        
        import re
        
        # Filter out very short sentences
        sentences = [s for s in sentences if len(s.split()) > 5]
        
        # Filter out procedural statements (like voting lists) that confuse the zero-shot model
        filtered_sentences = []
        for s in sentences:
            # Clean up web scraping artifacts
            if s.startswith("Share "):
                s = s[6:]
                
            # Ignore voting sentences
            if re.search(r'Voting for the.*(?:monetary policy|action|directive)', s, re.IGNORECASE):
                continue
            # Ignore purely informational / structural sentences / procedural votes
            if re.search(r'In a related action', s, re.IGNORECASE):
                continue
            if re.search(r'annual organization meeting', s, re.IGNORECASE):
                continue
                
            filtered_sentences.append(s)
            
        sentences = filtered_sentences
        
        if not sentences:
            return {"error": "No valid sentences found to analyze."}
            
        try:
            # Text-classification pipeline usage
            results = self.classifier(sentences, batch_size=16)
        except Exception as e:
            return {"error": f"Classification failed: {e}"}
        
        total_score = 0
        sentiment_counts = {"Hawkish": 0, "Dovish": 0, "Neutral": 0}
        analyzed_sentences = []
        
        # Calculate scores based on probability weights
        for i, (sentence, result) in enumerate(zip(sentences, results)):
            # The text-classification pipeline returns dict like {'label': 'LABEL_0', 'score': 0.99}
            label_name, base_score = self.map_label(result['label'])
            confidence = result['score']
            
            # Weighted score: multiply the base score (-1, 0, or 1) by model's confidence
            weighted_score = base_score * confidence
            total_score += weighted_score
            
            sentiment_counts[label_name] += 1
            
            if label_name != "Neutral":
                analyzed_sentences.append({
                    "text": sentence,
                    "sentiment": label_name,
                    "confidence": confidence,
                    "score": weighted_score,
                    "url": source_url,
                    "date": source_date
                })
        
        # Normalize final score between -1.0 (Most Dovish) and 1.0 (Most Hawkish)
        num_sentences = len(sentences)
        average_score = total_score / num_sentences if num_sentences > 0 else 0
        
        # Sort analyzed sentences to put the strongest hawkish/dovish statements first
        analyzed_sentences.sort(key=lambda x: abs(x["score"]), reverse=True)
        
        # Top 5 most impactful sentences
        highlights = analyzed_sentences[:5]
        
        return {
            "aggregate_score": average_score, # Range: -1.0 to 1.0
            "sentiment_counts": sentiment_counts,
            "total_sentences_analyzed": num_sentences,
            "highlights": highlights
        }

if __name__ == "__main__":
    analyzer = FOMCAnalyzer()
    sample = "The Committee decided to raise the target range for the federal funds rate to 5-1/4 to 5-1/2 percent. In determining the extent of additional policy firming that may be appropriate, the Committee will take into account the cumulative tightening of monetary policy, the lags with which monetary policy affects economic activity and inflation, and economic and financial developments."
    res = analyzer.analyze_text(sample)
    print(res)
