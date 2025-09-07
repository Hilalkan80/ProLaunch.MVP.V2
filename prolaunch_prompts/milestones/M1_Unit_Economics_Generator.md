# M1 — Unit Economics Generator Prompt
_Last updated: 2025-01-15_

## Purpose
Generate comprehensive unit economics analysis with COGS breakdown, margin calculations, profitability indicators, and actionable optimization strategies.

## Inputs (JSON)
```json{
"m0_data": {
"viability_score": 0,
"price_range": {"min": 0, "max": 0},
"competitors": [],
"product_idea": "..."
},
"product_specifications": {
"weight_kg": 0,
"dimensions_cm": {"length": 0, "width": 0, "height": 0},
"materials": [],
"packaging_type": "standard|custom|premium",
"fragility": "low|medium|high"
},
"cost_inputs": {
"product_cost": 0,
"shipping_unit_cost": 0,
"packaging_cost": 0,
"platform_fees_percent": 0,
"payment_processing_percent": 2.9,
"returns_rate_percent": 0,
"marketing_cac": 0
},
"pricing_strategy": {
"target_price": 0,
"competitor_average": 0,
"value_perception": "budget|standard|premium"
},
"volume_assumptions": {
"month_1": 0,
"month_3": 0,
"month_6": 0,
"month_12": 0
},
"evidence": [],
"max_words": 1000
}

## Required Calculations
```javascript// Core calculations - DO NOT modify formulas
const total_cogs = product_cost + shipping_unit_cost + packaging_cost + (target_price * platform_fees_percent/100);
const gross_profit = target_price - total_cogs;
const gross_margin = (gross_profit / target_price) * 100;
const contribution_margin = gross_profit - marketing_cac;
const true_margin = ((target_price - total_cogs - marketing_cac) / target_price) * 100;
const break_even_volume = fixed_costs / contribution_margin;
const payback_period = marketing_cac / gross_profit;

## Output Structure

```markdownUnit Economics Analysis🎯 Profitability DashboardMargin Health Score: [HEALTHY|WARNING|CRITICAL]
Gross Margin: {gross_margin}% [{indicator}]
True Margin: {true_margin}% (after CAC)
Contribution per Unit: ${contribution_margin}Visual Indicator
[CRITICAL]  [WARNING]  [HEALTHY]  [STRONG]
   <20%      20-30%     30-40%      >40%
            ▼ You are here💰 Cost Structure BreakdownPer-Unit Economics @ ${target_price}
ComponentCost% of PriceBenchmarkProduct Cost${product_cost}{pct}%Industry: {benchmark}%Shipping${shipping_unit_cost}{pct}%Industry: {benchmark}%Packaging${packaging_cost}{pct}%Industry: {benchmark}%Platform Fees${fees}{pct}%Standard: 15%Payment Processing${processing}2.9%Standard: 2.9%Total COGS${total_cogs}{pct}%Target: <60%Margin Cascade
Selling Price:        ${target_price}  (100%)
- COGS:              -${total_cogs}    ({pct}%)
= Gross Profit:       ${gross_profit}  ({gross_margin}%)
- Marketing CAC:     -${marketing_cac} ({pct}%)
= Contribution:       ${contribution}  ({true_margin}%)⚠️ Risk IndicatorsRed Flags {#if margin < 20}
🚨 CRITICAL: Unsustainable margins

Current gross margin below 20% threshold
No buffer for operational costs
Negative unit economics likely at scale
Yellow Flags {#if margin 20-30}
⚠️ WARNING: Tight margins

Limited room for error
Vulnerable to cost increases
Marketing spend must be highly efficient
Green Flags {#if margin > 30}
✅ HEALTHY: Sustainable margins

Room for promotional pricing
Buffer for market testing
Scalable unit economics
📊 Volume Sensitivity AnalysisBreak-Even Scenarios
Price PointUnits NeededTimelineFeasibility${target-10%}{units}{months} mo{assessment}${target}{units}{months} mo{assessment}${target+10%}{units}{months} mo{assessment}Profitability Trajectory
Month 1: {if profitable} ✅ Profitable | ❌ ${loss}
Month 3: {projection}
Month 6: {projection}
Month 12: {projection}🎯 Optimization OpportunitiesQuick Wins (Implement Now)

{Highest impact}: {Specific action} → Save ${amount}/unit
{Second impact}: {Specific action} → Save ${amount}/unit
{Third impact}: {Specific action} → Save ${amount}/unit
Strategic Improvements (3-6 months)

{Long-term optimization 1}
{Long-term optimization 2}
💡 Pricing Strategy RecommendationOptimal Price Points
Minimum Viable: ${min_viable} (20% margin)
Recommended: ${recommended} (35% margin)
Premium Position: ${premium} (45% margin)Compared to Competition
Your price (${target}): {position relative to competitors}
Market average: ${competitor_average}
Recommendation: {pricing action}✅ Action Items for M3 (Suppliers)
Based on these economics, when sourcing suppliers:

Target FOB price: ${max_product_cost} or less
Required MOQ: {based on break-even}
Shipping method: {recommendation based on margin}
📋 Next Steps Priority

{Most critical action based on margins}
{Second priority}
{Third priority}
Data Confidence
Evidence Quality: {✓✓✓ Strong | ✓✓ Moderate | ✓ Limited}
Assumptions Made: {list if any}

## Conditional Logic Rules
- IF gross_margin < 20 THEN status = "CRITICAL"
- IF gross_margin 20-30 THEN status = "WARNING"  
- IF gross_margin 30-40 THEN status = "HEALTHY"
- IF gross_margin > 40 THEN status = "STRONG"
- IF contribution_margin < 0 THEN show "NEGATIVE UNIT ECONOMICS" alert
- IF payback_period > 3 THEN flag CAC concern

## Evidence Requirements
- Cite [[ref_xxx]] for all benchmark comparisons
- Mark assumptions with asterisk (*)
- Include confidence indicators for projections