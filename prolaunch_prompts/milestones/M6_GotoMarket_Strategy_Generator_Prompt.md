# M6 — Go-to-Market Strategy Generator Prompt
_Last updated: 2025-01-15_

## Purpose
Generate comprehensive GTM strategy with channel recommendations, content calendar, campaign plans, budget allocation, and performance projections.

## Inputs (JSON)
```json{
"gtm_context": {
"from_m1": {
"unit_economics": {
"cac_target": 0,
"ltv": 0,
"margin": 0
}
},
"from_m2": {
"market_insights": {
"customer_channels": [],
"competitor_channels": [],
"market_trends": []
}
},
"from_m4": {
"marketing_budget": {
"month_1": 0,
"month_3": 0,
"month_6": 0
}
},
"from_m5": {
"brand_positioning": "...",
"target_personas": [],
"key_messages": []
}
},
"gtm_parameters": {
"timeline": {
"launch_date": "YYYY-MM-DD",
"prep_weeks": 0
},
"budget": {
"total": 0,
"monthly": 0,
"test_budget": 0
},
"goals": {
"month_1_revenue": 0,
"month_3_revenue": 0,
"month_6_revenue": 0
},
"constraints": {
"team_size": 0,
"experience_level": "beginner|intermediate|advanced",
"time_availability": "part-time|full-time"
}
},
"channel_research": {
"channel_performance": [
{
"channel": "...",
"avg_cac": 0,
"typical_conv_rate": 0,
"time_to_results": 0,
"complexity": "low|medium|high",
"fit_score": 0
}
]
},
"evidence": [],
"max_words": 3000
}

## Output Structure

```markdownGo-to-Market Strategy & Launch Plan🚀 GTM Strategy OverviewLaunch Approach
Strategy Type: {Soft Launch|Big Bang|Rolling|Stealth}
Primary Channel: {Channel} (${budget}, {pct}% of spend)
Secondary Channels: {List}
Timeline: {X} weeks to launch, {Y} weeks to scaleRevenue Projections by Channel
ChannelMonth 1Month 3Month 6CACROAS{Channel 1}${rev}${rev}${rev}${cac}{x}:1{Channel 2}${rev}${rev}${rev}${cac}{x}:1{Channel 3}${rev}${rev}${rev}${cac}{x}:1Total${rev}${rev}${rev}${avg}{x}:1Success Metrics
Primary KPI: {metric} - Target: {value}
Secondary KPIs:

{KPI 2}: Target {value}
{KPI 3}: Target {value}
{KPI 4}: Target {value}
📊 Channel Strategy MatrixChannel Prioritization
High Impact │ 🎯 {Channel}     ⭐ {Channel}
           │    (Quick Win)     (Scale Here)
           │
           │ 
Medium     │ 📌 {Channel}     🔄 {Channel}
           │    (Test)         (Optimize)
           │
           │
Low Impact │ ❌ {Channel}     ⏸️ {Channel}
           │    (Skip)         (Later)
           └────────────────────────────────
             Low Effort    High EffortRecommended Channel Mix🥇 Primary: {Channel Name} (40% of budget)
Why This Channel:

Best fit for {persona} because {reason}
Expected CAC: ${amount} (vs target ${target})
Time to results: {timeframe}
Implementation Plan:
Week 1-2: {Setup tasks}
Week 3-4: {Testing tasks}
Week 5+: {Scaling tasks}Budget Allocation:

Setup/Tools: ${amount}
Ad Spend: ${amount}/month
Content Creation: ${amount}
Success Metrics:

Target: {conversions} sales/month by Month 3
Leading indicator: {metric}
Optimization trigger: {condition}
🥈 Secondary: {Channel 2} (30% of budget)
{Condensed version of above}🥉 Support: {Channel 3} (20% of budget)
{Condensed version of above}🧪 Test: {Channel 4} (10% of budget)
{Brief test parameters}📅 30-Day Content CalendarWeek 1: Pre-Launch Preparation
DayChannelContent TypeTopic/HookStatusMonAllBrand Story"Why we started..."[ ] CreateTueIGProduct RevealBehind the scenes[ ] CreateWedEmailList Building"Get early access"[ ] CreateThuBlogSEO Post{Target keyword}[ ] CreateFriSocialEngagementPoll/Question[ ] CreateWeek 2: Soft Launch
{Similar daily breakdown}Week 3: Launch Week
{Similar daily breakdown with increased intensity}Week 4: Momentum Building
{Similar daily breakdown}Content TemplatesSocial Post Formula
Hook: {Attention grabber}
Story: {Relatable scenario}
Value: {What they learn/get}
CTA: {Specific action}Example:
"{Hook that stops scroll}{Story in 2-3 lines}Here's what we learned: {Value point}{CTA with urgency/incentive}"Email Templates
Subject Lines That Work:

"{Curiosity gap}" - {expected open rate}%
"{Benefit statement}" - {expected open rate}%
"{Urgency/FOMO}" - {expected open rate}%
💰 Budget Allocation StrategyMonth 1 Budget: ${total}
Paid Ads (40%) ████████░░░░░░░░ ${amount}
Content (25%) █████░░░░░░░░░░░ ${amount}
Influencer (20%) ████░░░░░░░░░░ ${amount}
Tools (10%) ██░░░░░░░░░░░░░░ ${amount}
Reserve (5%) █░░░░░░░░░░░░░░░ ${amount}Channel-Specific Budgets
ChannelTest BudgetScale BudgetNotesFacebook Ads${amount}${amount}/mo{Guidelines}Google Ads${amount}${amount}/mo{Guidelines}Influencer${amount}${amount}/mo{Guidelines}Content${amount}${amount}/mo{Guidelines}Testing Framework
Minimum Viable Test:

Budget: ${amount} per channel
Duration: {days} days
Success Criteria: CAC < ${amount}
Kill Criteria:

CAC > ${amount} after {days} days
Conversion rate < {pct}%
Quality score < {threshold}
📱 Campaign BlueprintsCampaign 1: Launch Campaign
Name: "{Campaign Name}"
Objective: Awareness → Conversion
Duration: {timeframe}
Budget: ${amount}Creative Brief:

Hero Image: {Description}
Headlines: {3 options}
Body Copy: {Key points}
CTA: "{Button text}"
Targeting:

Demographics: {Specifications}
Interests: {List}
Behaviors: {List}
Exclusions: {List}
Landing Page Requirements:

Above fold: {Elements}
Social proof: {Types}
Conversion elements: {List}
Campaign 2: Retargeting Campaign
{Similar structure}Campaign 3: Influencer Seeding
Tier Structure:

Nano (1K-10K): {number} creators, ${budget}
Micro (10K-100K): {number} creators, ${budget}
Macro (100K+): {number} creators, ${budget}
Outreach Template:
{Ready-to-use influencer pitch}🎯 Launch Sequence TimelineT-4 Weeks: Foundation

 Set up analytics (GA4, Pixel, etc.)
 Create landing pages
 Set up email automation
 Produce initial content batch
 Configure shopping/payment
T-2 Weeks: Preparation

 Launch "coming soon" campaign
 Begin influencer outreach
 Schedule social content
 Set up customer service
 Test all systems
Launch Week: Execution

 Day 1: Soft launch to email list
 Day 2: Social announcement
 Day 3: Influencer posts go live
 Day 4: Paid ads activate
 Day 5: PR/Media push
 Day 6-7: Momentum campaigns
Post-Launch: Optimization

 Week 2: Analyze initial data
 Week 3: Optimize based on performance
 Week 4: Scale winning channels
 Month 2: Add new channels
📈 Performance TrackingDashboard Metrics
Daily Tracking:

Revenue: Target ${amount}/day by Day 30
Traffic: Target {number} visitors/day
Conversion Rate: Target {pct}%
CAC: Must stay below ${amount}
Weekly Reviews:

Channel performance comparison
Content engagement rates
Email list growth
Customer feedback themes
A/B Testing Calendar
WeekTestHypothesisSuccess Metric1Headlines{Hypothesis}CTR > {pct}%2Images{Hypothesis}Conv > {pct}%3Pricing{Hypothesis}AOV > ${amount}4Audiences{Hypothesis}CAC < ${amount}🎬 Quick Start ActionsDo This TODAY:

Create Facebook Business Manager

Link: business.facebook.com
Time: 15 minutes



Set Up Google Analytics

Link: analytics.google.com
Time: 30 minutes



Install Tracking Pixels

Facebook Pixel
Google Tag Manager
Time: 45 minutes


This Week:

Create first 10 pieces of content
Set up email capture landing page
Schedule initial social posts
Begin influencer outreach
Before Launch:

 30 pieces of content created
 5 email sequences written
 10 ad variations ready
 3 influencers confirmed
 All tracking verified
Risk Mitigation
If CAC exceeds target:
→ Pivot to {alternative channel}If launch traffic disappoints:
→ Activate {backup promotion}If inventory runs out:
→ Implement {waitlist strategy}

## Channel Selection Logic
- IF budget < $1000 THEN prioritize organic/influencer
- IF experience = "beginner" THEN start with 1-2 channels max
- IF timeline < 30 days THEN focus on paid ads
- IF product visual THEN prioritize Instagram/TikTok
- IF B2B elements THEN include LinkedIn