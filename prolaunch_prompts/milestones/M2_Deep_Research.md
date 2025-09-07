# M2 — Deep Research Pack Generator Prompt
_Last updated: 2025-01-15_

## Purpose
Generate comprehensive market research report with competitive analysis, demand validation, trend analysis, and strategic positioning opportunities (10-15 minute generation).

## Inputs (JSON)
```json{
"research_context": {
"product": "...",
"category": "...",
"target_audience": "...",
"geography": "US",
"from_m0": {
"viability_score": 0,
"initial_competitors": [],
"price_range": {}
}
},
"research_stages": {
"market_sizing": {
"status": "complete",
"tam": 0,
"sam": 0,
"som": 0,
"growth_rate": 0,
"sources": []
},
"competitor_analysis": {
"status": "complete",
"direct_competitors": [],
"indirect_competitors": [],
"market_leaders": [],
"sources": []
},
"demand_signals": {
"status": "complete",
"search_volume": 0,
"trend_direction": "up|stable|down",
"seasonality": {},
"sources": []
},
"customer_insights": {
"status": "complete",
"pain_points": [],
"purchase_drivers": [],
"objections": [],
"sources": []
}
},
"evidence": [],
"processing_time": 0,
"max_words": 3500
}

## Output Structure

```markdownDeep Market Research Report📊 Executive SummaryMarket Opportunity Score: {0-100}
Market Size: ${TAM}B total addressable [[citations]]
Growth Rate: {rate}% YoY [[citations]]
Competition Level: {Low|Moderate|High|Saturated}
Demand Strength: {Weak|Moderate|Strong|Very Strong}
Entry Difficulty: {Easy|Moderate|Challenging|Very Hard}The Bottom Line
{One paragraph synthesis of go/no-go recommendation with key reasons}3 Key Insights

{Most important finding} [[citation]]
{Second finding} [[citation]]
{Third finding} [[citation]]
🌍 Market Landscape AnalysisMarket Sizing & Opportunity
TAM (Total Addressable Market): ${tam}B

{Explanation of what this includes} [[citation]]
SAM (Serviceable Addressable Market): ${sam}B

{Your realistic reach} [[citation]]
SOM (Serviceable Obtainable Market): ${som}M

{Year 1 capturable} [[citation]]
Growth Dynamics
2021: ${size} → 2023: ${size} → 2025E: ${size}
        {rate}%         {rate}%Growth Drivers:

{Driver 1} [[citation]]
{Driver 2} [[citation]]
{Driver 3} [[citation]]
Headwinds:

{Challenge 1} [[citation]]
{Challenge 2} [[citation]]
Market Maturity Assessment
IndicatorStatusWhat This MeansInnovation Rate{High/Med/Low}{Interpretation}Consolidation{Early/Mid/Late}{Interpretation}Price Pressure{High/Med/Low}{Interpretation}Regulation{Heavy/Moderate/Light}{Interpretation}🎯 Competitive Intelligence ReportCompetitive Landscape Map
High Price │ • [Premium Competitor]
          │ • [Premium Competitor 2]
          │
          │         YOUR POSITION ←
Mid Price │ • [Mid Competitor]  ★
          │ • [Mid Competitor 2]
          │
Low Price │ • [Budget Competitor]
          │ • [Budget Competitor 2]
          └─────────────────────────
            Low Quality    High QualityTop 10 Competitors Deep Dive1. {Competitor Name} - Market Leader
Share: ~{pct}% [[citation]]
Price Range: min−{min}-
min−{max}
Monthly Sales: {estimate} units [[citation]]
Key Strength: {What they do best}
Vulnerability: {Where they're weak}
Customer Sentiment: {rating}/5 ({review_count} reviews){Repeat for top 10 competitors}Competitive Advantages Matrix
FactorYouLeaderAverageOpportunityPrice{position}${x}${y}{strategy}Quality{position}{level}{level}{strategy}Speed{position}{days}{days}{strategy}Service{position}{level}{level}{strategy}Market Gaps & Opportunities

Underserved Segment: {Description} [[citation]]

Size: {number} potential customers
Need: {specific pain point}
Access: {how to reach}



Feature Gap: {Description} [[citation]]

Competitors missing: {feature}
Customer demand: {evidence}
Implementation difficulty: {assessment}



Price Point Gap: ${amount} [[citation]]

No strong player between x−{x}-
x−{y}

Customer willingness: {evidence}


📈 Demand Validation & TrendsSearch Demand Analysis
Primary Keyword: "{keyword}"

Monthly searches: {volume} [[citation]]
YoY growth: {rate}%
Competition: {High/Med/Low}
CPC: ${amount}
Related Searches Trending Up:

"{keyword}" (+{pct}% YoY) - {volume}/mo
"{keyword}" (+{pct}% YoY) - {volume}/mo
"{keyword}" (+{pct}% YoY) - {volume}/mo
Seasonal Patterns
Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec
 70  65  75  80  85  90  95 100  95 110 150 180
                                         ↑   ↑
                                   Key seasonsSocial Proof & Sentiment
Reddit Discussions: {count} threads/month [[citation]]

Sentiment: {Positive/Mixed/Negative}
Key complaints: {top issue}
Key praise: {top positive}
Social Media Signals:

Instagram: {hashtag count} posts [[citation]]
TikTok: {view count} views on #{hashtag}
Pinterest: {pin count} pins saved
Trend Lifecycle Position
Emerging → Growing → Maturing → Declining
           ★ You are here👥 Customer IntelligencePrimary Customer Profile
Demographics:

Age: {range}
Income: ${range}
Location: {primary regions}
Lifestyle: {description}
Psychographics:

Values: {top 3}
Pain points: {top 3}
Aspirations: {description}
Purchase Decision Factors

{Factor 1} - {pct}% importance [[citation]]
{Factor 2} - {pct}% importance [[citation]]
{Factor 3} - {pct}% importance [[citation]]
Customer Journey Insights
Awareness: How they discover products like yours

{Channel 1}: {pct}% [[citation]]
{Channel 2}: {pct}% [[citation]]
Consideration: What they compare

Average products compared: {number}
Decision timeline: {days}
Key comparison factors: {list}
Purchase: Transaction preferences

Preferred platform: {platform}
Payment method: {method}
Average order value: ${amount}
Voice of Customer Analysis
Top Praise Points: (from reviews)

"{Quote}" [[citation]]
"{Quote}" [[citation]]
Top Complaint Themes:

{Theme}: {frequency}% of negative reviews
{Theme}: {frequency}% of negative reviews
⚠️ Risk AssessmentMarket Risks
RiskProbabilityImpactMitigation{Risk 1}{H/M/L}{H/M/L}{Strategy}{Risk 2}{H/M/L}{H/M/L}{Strategy}{Risk 3}{H/M/L}{H/M/L}{Strategy}Regulatory Considerations

{Regulation 1}: {Impact on business} [[citation]]
{Regulation 2}: {Impact on business} [[citation]]
💡 Strategic RecommendationsPositioning Strategy
Recommended Position: {Description}

Different from competitors by: {differentiator}
Target micro-niche: {specific segment}
Key message: "{tagline}"
Go-to-Market Approach

Phase 1 (Months 1-3): {Strategy}
Phase 2 (Months 4-6): {Strategy}
Phase 3 (Months 7-12): {Strategy}
Success Factors
✅ Must Have: {Critical factor}
✅ Must Have: {Critical factor}
⚠️ Should Have: {Important factor}
💡 Nice to Have: {Bonus factor}📋 Next Steps for M3 (Suppliers)
Based on this research:

Focus on suppliers who can support: {requirement}
Ensure capability for: {specific need}
Price point must enable: ${target} retail
Research Quality Metrics
Sources Analyzed: {count}
Data Freshness: {pct}% from last 6 months
Confidence Level: {High|Medium|Low}
Key Assumptions: {List if any}

## Progressive Disclosure Rules
- Start with executive summary for quick readers
- Use collapsible sections in UI implementation
- Highlight actionable insights with emoji markers
- Include "What this means for you" explanations

## Citation Requirements
- Minimum 5 citations per major section
- Total citations should be 50-100
- Format: [[ref_xxx - YYYY-MM-DD]]
- Prioritize recent sources (< 6 months old)