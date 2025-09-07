# M4 — Financial Model Generator Prompt
_Last updated: 2025-01-15_

## Purpose
Generate comprehensive 36-month financial projections with P&L statements, cash flow analysis, scenario planning, and investment requirements.

## Inputs (JSON)
```json{
"business_context": {
"from_m0": {
"viability_score": 0,
"market_size": 0
},
"from_m1": {
"unit_economics": {
"selling_price": 0,
"cogs": 0,
"gross_margin": 0,
"contribution_margin": 0
}
},
"from_m2": {
"market_growth_rate": 0,
"addressable_market": 0
},
"from_m3": {
"supplier_costs": {
"unit_cost": 0,
"moq": 0,
"payment_terms": "..."
}
}
},
"assumptions": {
"revenue": {
"starting_units_month": 0,
"growth_rate_monthly": 0,
"seasonality_factors": {},
"price_increases": [],
"return_rate": 0
},
"costs": {
"fixed_costs_monthly": {
"rent": 0,
"salaries": 0,
"software": 0,
"insurance": 0,
"other": 0
},
"variable_cost_ratios": {
"shipping": 0,
"packaging": 0,
"platform_fees": 0,
"payment_processing": 0.029
},
"marketing": {
"cac": 0,
"monthly_budget": 0,
"growth_efficiency": 0
}
},
"working_capital": {
"inventory_days": 0,
"accounts_receivable_days": 0,
"accounts_payable_days": 0
},
"funding": {
"initial_investment": 0,
"debt_amount": 0,
"debt_interest_rate": 0
}
},
"scenarios": {
"conservative": {"growth_rate": 0.7, "cost_multiplier": 1.2},
"realistic": {"growth_rate": 1.0, "cost_multiplier": 1.0},
"optimistic": {"growth_rate": 1.5, "cost_multiplier": 0.9}
},
"evidence": [],
"max_words": 3000
}

## Output Structure

```markdown36-Month Financial Projections💼 Executive Financial SummaryInvestment Requirements
Initial Capital Needed: ${total_required}

Inventory: ${amount} ({pct}%)
Working Capital: ${amount} ({pct}%)
Operating Buffer: ${amount} ({pct}%)
Marketing Launch: ${amount} ({pct}%)
Key Financial Metrics
MetricYear 1Year 2Year 3Revenue${amount}${amount}${amount}Gross Profit${amount}${amount}${amount}Net Income${amount}${amount}${amount}ROI{pct}%{pct}%{pct}%Break-Even Analysis
Break-Even Point: Month {number} ({date})
Cash Flow Positive: Month {number} ({date})
Investment Payback: Month {number} ({date})📊 Profit & Loss ProjectionsYear 1 Monthly P&L
MonthRevenueCOGSGross ProfitOpExEBITDANet IncomeM1${rev}${cogs}${gp}${opex}${ebitda}${ni}M2${rev}${cogs}${gp}${opex}${ebitda}${ni}.....................M12${rev}${cogs}${gp}${opex}${ebitda}${ni}Total${rev}${cogs}${gp}${opex}${ebitda}${ni}Year 2 Quarterly P&L
QuarterRevenueGross ProfitNet IncomeMarginQ1${amount}${amount}${amount}{pct}%Q2${amount}${amount}${amount}{pct}%Q3${amount}${amount}${amount}{pct}%Q4${amount}${amount}${amount}{pct}%Total${amount}${amount}${amount}{pct}%Year 3 Annual Summary
Revenue: ${amount} ({growth}% YoY)
Gross Profit: ${amount} ({margin}%)
Operating Income: ${amount}
Net Income: ${amount} ({margin}%)💰 Cash Flow AnalysisMonthly Cash Flow (Year 1)
Starting Cash: ${amount}

Month 1:  [==========>                ] ${balance}
Month 2:  [=======>                   ] ${balance}  ⚠️ Lowest point
Month 3:  [=========>                 ] ${balance}
Month 4:  [===========>               ] ${balance}
Month 5:  [=============>             ] ${balance}
Month 6:  [===============>           ] ${balance}
Month 7:  [=================>         ] ${balance}
Month 8:  [===================>       ] ${balance}
Month 9:  [=====================>     ] ${balance}
Month 10: [======================>    ] ${balance}
Month 11: [========================>  ] ${balance}
Month 12: [==========================>] ${balance}Working Capital Requirements
ComponentAmountDaysNotesInventory${amount}{days}{MOQ impact}Accounts Receivable${amount}{days}{Platform terms}Accounts Payable(${amount}){days}{Supplier terms}Net Working Capital${amount}-{Interpretation}Cash Burn & Runway
Monthly Burn Rate: ${amount} (Months 1-6)
Current Runway: {months} months
To Cash Flow Positive: {months} months
Recommended Buffer: ${amount} (3 months opex)🎯 Scenario AnalysisThree Scenarios Comparison
MetricConservativeRealisticOptimisticAssumptionsGrowth Rate{rate}%/mo{rate}%/mo{rate}%/moUnit Sales Y1{units}{units}{units}CAC${amount}${amount}${amount}ResultsRevenue Y1${amount}${amount}${amount}Break-EvenMonth {n}Month {n}Month {n}Cash Required${amount}${amount}${amount}IRR{pct}%{pct}%{pct}%Sensitivity Analysis
What Moves the Needle Most:

Price ±10%: Impact ${amount} ({pct}% of profit)
Volume ±10%: Impact ${amount} ({pct}% of profit)
CAC ±10%: Impact ${amount} ({pct}% of profit)
COGS ±10%: Impact ${amount} ({pct}% of profit)
Risk Thresholds
🔴 Red Flags (Conservative):

Revenue below ${amount}/mo by Month 6
CAC above ${amount}
Gross margin below {pct}%
🟡 Warning Signs (Realistic):

Growth rate below {pct}%/mo
Inventory turnover below {x} times
Customer returns above {pct}%
🟢 Success Indicators (All scenarios):

Positive unit economics from Day 1 ✓
Gross margins above 40% ✓
Scalable growth model ✓
📈 Investment & ReturnsUse of Funds
Total Investment: ${amount}

Inventory (35%) ████████░░░░░░░░░░░░
Working Cap (25%) █████░░░░░░░░░░░░░░░
Marketing (20%) ████░░░░░░░░░░░░░░░░
Operations (15%) ███░░░░░░░░░░░░░░░░░
Reserve (5%) █░░░░░░░░░░░░░░░░░░░Return Projections
YearInvestmentRevenueNet IncomeROIIRR0(${amount})$0(${amount})-100%-1-${amount}${amount}{pct}%{pct}%2-${amount}${amount}{pct}%{pct}%3-${amount}${amount}{pct}%{pct}%Total(${inv})${rev}${ni}{pct}%{pct}%Exit Valuation (Year 3)
Revenue Multiple Method: ${amount} (2.5x revenue)
EBITDA Multiple Method: ${amount} (8x EBITDA)
DCF Valuation: ${amount} (10% discount rate)
Estimated Valuation Range: ${low}M - ${high}M🎬 Key Milestones & TriggersFinancial Milestones Timeline
MonthMilestoneMetricAction Required1LaunchFirst saleBegin tracking3Traction${revenue}/moOptimize CAC6Validation{units}/moScale inventory9Growth${revenue}/moAdd channel12Scale${revenue}/moHire support18Expansion${revenue}/moNew products24Maturity${revenue}/moConsider exitDecision Triggers
Scale Up When:

3 consecutive months of {pct}%+ growth
CAC payback < {months} months
Inventory turnover > {x} times/year
Pivot/Adjust When:

Burn rate exceeds ${amount}/mo
Growth rate below {pct}% for 2 months
Gross margins compress below {pct}%
📋 Action Items from Financial ModelImmediate Priorities

Secure ${amount} initial capital

Sources: {recommendations}
Timeline: Before {date}



Set up financial tracking

Tools: {recommendations}
KPIs to track: {list}



Negotiate payment terms

Target: Net 30-60 with suppliers
Impact: Reduces working capital by ${amount}


Financial Controls to Implement

 Weekly cash flow monitoring
 Monthly P&L review
 Inventory turnover tracking
 CAC/LTV monitoring
 Budget vs actual analysis
When to Raise Additional Capital
Triggers for Funding Round:

Proven product-market fit ({metric})
Need to accelerate growth
Pre-order larger inventory for economies of scale
Model Assumptions & Limitations
Key Assumptions:

Linear growth model (may vary in reality)
Stable CAC (typically increases with scale)
No major market disruptions
Consistent supplier pricing
Confidence Level: {High|Medium|Low}
Model Updated: {Date}
Next Review: {Date}

## Calculation Rules
- ALL formulas must use provided inputs
- Never invent numbers - mark as [ASSUMPTION] if missing
- Show formulas for key calculations in footnotes
- Round to nearest $100 for projections
- Include cell references for Excel export