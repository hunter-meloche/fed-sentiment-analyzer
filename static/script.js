document.addEventListener('DOMContentLoaded', () => {
    const analyzeBtn = document.getElementById('analyze-btn');
    const btnText = analyzeBtn.querySelector('.btn-text');
    const loader = analyzeBtn.querySelector('.loader');
    
    const resultsPanel = document.getElementById('results-panel');
    const errorPanel = document.getElementById('error-panel');
    const errorMessage = document.getElementById('error-message');
    
    // Elements to update
    const needle = document.getElementById('needle');
    const scoreDisplay = document.getElementById('score-display');
    const sentimentCategory = document.getElementById('sentiment-category');
    
    const totalSentences = document.getElementById('total-sentences');
    const dovishCount = document.getElementById('dovish-count');
    const neutralCount = document.getElementById('neutral-count');
    const hawkishCount = document.getElementById('hawkish-count');
    
    const highlightsList = document.getElementById('highlights-list');
    const urlDropdown = document.getElementById('url-dropdown');
    const viewSourceBtn = document.getElementById('view-source-btn');
    const docLimitInput = document.getElementById('doc-limit');
    const sourceLinkContainer = document.querySelector('.source-link');

    analyzeBtn.addEventListener('click', async () => {
        // UI Loading State
        analyzeBtn.disabled = true;
        btnText.classList.add('hidden');
        loader.classList.remove('hidden');
        resultsPanel.classList.add('hidden');
        errorPanel.classList.add('hidden');

        try {
            const limit = Math.max(1, parseInt(docLimitInput.value) || 5);
            const response = await fetch(`/api/analyze?limit=${limit}`);
            const data = await response.json();

            if (data.status === 'success') {
                updateUI(data);
                resultsPanel.classList.remove('hidden');
            } else {
                showError(data.error || 'Unknown error occurred during analysis.');
            }
        } catch (error) {
            showError('Failed to connect to the server. Is it running?');
        } finally {
            // Restore UI State
            analyzeBtn.disabled = false;
            btnText.classList.remove('hidden');
            loader.classList.add('hidden');
            
            // Allow re-triggering animation by removing focus
            analyzeBtn.blur();
        }
    });

    function updateUI(data) {
        // Update Dial
        // Map score (-1.0 to 1.0) to rotation angle (-90deg to 90deg)
        // Adjust formula for SVG transform logic where 0 is left (-90 visually) and 180 is right (90 visually)
        // We start with the polygon pointing UP at 0, rotate -90 points it LEFT.
        // Wait, standard rotation: 0 = UP. -90 = LEFT (Dovish). 90 = RIGHT (Hawkish).
        // Let's constrain score between -1 and 1
        const clampedScore = Math.max(-1, Math.min(1, data.aggregate_score));
        
        // -1 score -> -90 deg rotation. 1 score -> +90 deg rotation.
        // The SVG group has default rotation: transform="rotate(-90 100 100)"
        // If we set to (clampedScore * 90), it will point correctly.
        const rotationAngle = clampedScore * 90;
        
        // Update needle rotation with slight delay for dramatic effect
        setTimeout(() => {
            needle.setAttribute('transform', `rotate(${rotationAngle} 100 100)`);
        }, 300);

        // Update Score Text
        scoreDisplay.textContent = data.aggregate_score.toFixed(3);
        
        // Determine Category and Color
        let category = 'Neutral';
        let colorClass = 'neutral';
        
        if (data.aggregate_score <= -0.15) {
            category = 'Dovish';
            colorClass = 'dovish';
            scoreDisplay.style.color = 'var(--dovish)';
            sentimentCategory.style.color = 'var(--dovish)';
        } else if (data.aggregate_score >= 0.15) {
            category = 'Hawkish';
            colorClass = 'hawkish';
            scoreDisplay.style.color = 'var(--hawkish)';
            sentimentCategory.style.color = 'var(--hawkish)';
        } else {
            scoreDisplay.style.color = 'var(--text-main)';
            sentimentCategory.style.color = 'var(--neutral)';
        }
        
        sentimentCategory.textContent = category;

        // Update Stats
        totalSentences.textContent = data.total_sentences_analyzed;
        dovishCount.textContent = data.sentiment_counts.Dovish;
        neutralCount.textContent = data.sentiment_counts.Neutral;
        hawkishCount.textContent = data.sentiment_counts.Hawkish;

        // Update Highlights
        highlightsList.innerHTML = '';
        if (data.highlights && data.highlights.length > 0) {
            data.highlights.forEach(h => {
                const li = document.createElement('li');
                const pClass = h.sentiment.toLowerCase();
                li.className = `highlight-item ${pClass}`;
                
                const confidencePercent = (h.confidence * 100).toFixed(1);
                
                li.innerHTML = `
                    <p>"${h.text}"</p>
                    <div class="highlight-meta ${pClass}">
                        <div class="meta-left">
                            <span class="sentiment-badge">${h.sentiment}</span>
                            <span class="confidence">Confidence: ${confidencePercent}%</span>
                        </div>
                        <div class="meta-right">
                            <a href="${h.url}" target="_blank" class="source-link-small">${h.date}</a>
                        </div>
                    </div>
                `;
                highlightsList.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.className = 'highlight-item';
            li.innerHTML = '<p>No significantly hawkish or dovish statements detected.</p>';
            highlightsList.appendChild(li);
        }

        // Update Links Dropdown
        urlDropdown.innerHTML = '';
        if (data.urls && data.urls.length > 0) {
            data.urls.forEach((url, index) => {
                const option = document.createElement('option');
                option.value = url;
                
                // Extract part of URL to make it readable (e.g., monetaryYYYYMMDD)
                const parts = url.split('/');
                const filename = parts[parts.length - 1].replace('.htm', '');
                option.textContent = `Statement ${index + 1} (${filename})`;
                
                urlDropdown.appendChild(option);
            });
            sourceLinkContainer.style.display = 'block';
        } else {
            sourceLinkContainer.style.display = 'none';
        }
    }

    viewSourceBtn.addEventListener('click', () => {
        const selectedUrl = urlDropdown.value;
        if (selectedUrl) {
            window.open(selectedUrl, '_blank');
        }
    });

    function showError(msg) {
        errorMessage.textContent = msg;
        errorPanel.classList.remove('hidden');
    }
});
