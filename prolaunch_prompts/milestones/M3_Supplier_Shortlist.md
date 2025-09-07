# M3 — Supplier Shortlist Generator Prompt
_Last updated: 2025-01-15_

## Purpose
Generate vetted supplier recommendations with detailed profiles, MOQ/pricing tiers, quality indicators, and customized outreach templates.

## Inputs (JSON)
```json{
"product_context": {
"from_m0": {
"product_idea": "...",
"target_price": 0
},
"from_m1": {
"target_cogs": 0,
"max_product_cost": 0,
"volume_projections": {}
},
"from_m2": {
"market_position": "...",
"quality_expectations": "..."
}
},
"product_requirements": {
"category": "...",
"materials": [],
"dimensions": {},
"weight": 0,
"certifications_required": [],
"customization_needs": [],
"packaging_requirements": "..."
},
"sourcing_parameters": {
"quantity_initial": 0,
"quantity_reorder": 0,
"timeline_days": 0,
"quality_priority": "price|balanced|quality",
"geography_preference": "any|asia|americas|europe"
},
"supplier_research": {
"verified_suppliers": [
{
"id": "SUP_001",
"name_masked": "[Supplier A]",
"location": "...",
"years_in_business": 0,
"certifications": [],
"moq": 0,
"price_tiers": [
{"quantity_min": 0, "quantity_max": 0, "unit_price": 0}
],
"lead_time_days": 0,
"sample_cost": 0,
"payment_terms": "...",
"trade_assurance": true,
"verified_status": "gold|silver|basic",
"response_rate": 0,
"on_time_delivery": 0,
"customer_ratings": {
"overall": 0,
"communication": 0,
"quality": 0,
"delivery": 0
},
"specializations": [],
"export_markets": [],
"production_capacity": 0,
"customization_capabilities": [],
"red_flags": [],
"green_flags": []
}
]
},
"preview_mode": false,
"evidence": [],
"max_words": 2500
}

## Output Structure

```markdownSupplier Shortlist & Sourcing Strategy🏆 Top Supplier RecommendationsQuick Comparison Matrix
SupplierBest ForMOQUnit Price*Lead TimeQuality ScoreMatch[A] ⭐Best Overall500x−{x}-
x−{y}
25 days4.8/595%[B]Lowest MOQ100x−{x}-
x−{y}
30 days4.5/588%[C]Best Price1000x−{x}-
x−{y}
35 days4.3/585%[D]Fastest500x−{x}-
x−{y}
15 days4.6/582%[E]Premium300x−{x}-
x−{y}
28 days4.9/580%*At your volume: {quantity} units📋 Detailed Supplier Profiles🥇 Supplier [A] - RECOMMENDED BEST MATCH
Why We Recommend: {Specific match reasons based on requirements}Verified Credentials ✓

Years in Business: {years}
Certifications: {list} ✓ Verified
Trade Assurance: ${amount} protection
Export Experience: {countries}
Pricing Structure
QuantityUnit PriceTotal CostSavings100-499${price}${total}Baseline500-999${price}${total}-${save}1000-2999${price}${total}-${save}3000+${price}${total}-${save}Your Sweet Spot: {quantity} units = ${price}/unitProduction Capabilities

Capacity: {units}/month
Current Utilization: {pct}% (room for growth ✓)
Customization: {Available options}
Materials: {List matching requirements}
Quality Indicators
✅ Green Flags:

{Positive indicator 1}
{Positive indicator 2}
{Positive indicator 3}
⚠️ Considerations:

{Potential concern 1}
{Potential concern 2}
Sample & Payment Terms

Sample Cost: ${amount} (credited to first order)
Sample Time: {days} days
Payment Terms:

New buyers: 30% deposit, 70% before shipping
After 3 orders: Net 30 available


Payment Methods: T/T, PayPal, Trade Assurance
Communication Details {if preview_mode=false}

Contact: {name}
Email: {email}
WhatsApp: {phone}
WeChat: {id}
Best Hours: 9PM-2AM EST (China business hours)
Response Time: Usually within {hours} hours
English Level: {Fluent|Good|Basic}
{Repeat for Suppliers B-E with decreasing detail}📧 Outreach TemplatesTemplate 1: Initial Inquiry (Best for First Contact)
Subject: {Product Category} Order Inquiry - {Quantity} Units (Repeat Orders Expected)

Dear {Supplier Name},

I found your company on {platform} and am impressed by your {specific strength, e.g., certifications/reviews}.

We're launching a {brief product description} brand in the US market and are looking for a reliable manufacturing partner.

**Product Requirements:**
- Material: {material}
- Size: {dimensions}
- Weight: {weight}
- Packaging: {requirements}
- Certification needed: {list}

**Order Details:**
- First order: {quantity} units
- Reorders: {frequency} (expected {annual volume}/year)
- Target FOB price: ${price} per unit
- Delivery: {port/location}
- Timeline: Need samples by {date}, first order by {date}

**Questions:**
1. Can you meet our target price at {quantity} units?
2. What's your best price for {higher quantity}?
3. Do you have {specific certification} for US import?
4. Sample availability and cost?
5. Can you provide customer references?

Please share:
- Complete price list with MOQ tiers
- Product catalog
- Certification documents
- Sample policy

We're evaluating suppliers this week and making a decision by {date}.

Best regards,
{Your name}
{Company}
{Contact info}Template 2: Negotiation Follow-up
Subject: Re: Order #{number} - Ready to Proceed with Adjustments

{Supplier name},

Thank you for the quotation. We're very interested but need to reach a middle ground on pricing.

**Our Position:**
- Your quote: ${their_price}/unit at {moq} MOQ
- Our target: ${your_target}/unit
- Proposed compromise: ${middle}/unit at {higher_quantity} units

**Value We Bring:**
- Consistent reorders (projecting {quantity}/quarter)
- Growth potential (our forecast shows {growth})
- Simple requirements (no complex customization)
- Reliable payment (can do 50% deposit)

**Options to Reach Our Target:**
1. Increase our order to {quantity} for better pricing?
2. Adjust specifications to reduce cost?
3. Longer lead time for better rate?
4. Annual contract with volume commitment?

We'd prefer to work with you based on your {specific strength}. 

Can we find a solution that works for both of us?

{Your name}Template 3: Sample Request
Subject: Sample Request - Order #{number} {Product}

{Supplier name},

We're ready to proceed with samples before our main order.

**Sample Requirements:**
- Quantity: {2-3} pieces
- Variations: {list any variants}
- Custom features: {if any}
- Shipping: DHL/FedEx to {address}

**Payment:**
- Accept sample cost of ${amount}
- Please credit to first order
- Can pay via {PayPal/Trade Assurance}

**Timeline:**
Need samples by {date} for our review process.

After approval, first order will be {quantity} units with potential for {annual volume} annually.

Please confirm:
1. Sample production time
2. Shipping cost and time
3. Payment instructions

{Your name}💰 Negotiation StrategyLeverage Points You Have

Volume Commitment: Annual forecast of {units}
Growth Potential: {Your growth story}
Repeat Business: Subscription/repeat model
Simple Requirements: {What makes you easy to work with}
Payment Reliability: Can offer favorable terms
Common Negotiation Tactics

Bundle Deal: Combine first 3 orders for better rate
Seasonal Timing: Order during their slow season
Payment Terms: Offer higher deposit for lower price
Specification Flex: Adjust non-critical specs for savings
Competitor Quotes: Reference without revealing sources
Red Lines (Don't Compromise)

Quality certifications: {required certs}
Maximum lead time: {days}
Payment protection: Use Trade Assurance
Sample before bulk: Always required
📊 Sourcing Risk AnalysisSupplier Concentration Risk
Current Mix: {pct}% from single supplier
Recommendation: Diversify with backup supplier by order 3Quality Control Plan

Pre-Production: Approve samples + specifications
During Production: {inspection points}
Pre-Shipment: Third-party inspection recommended
Documentation: Require {specific documents}
Contingency Planning
If Supplier [A] Fails:
→ Supplier [B] can fulfill with {days} notice
→ Supplier [C] as emergency backup (+${cost}/unit)📋 Next Steps PriorityImmediate Actions (This Week)

Send inquiry to Suppliers [A] and [B]
Request samples from top 2 responders
Set up comparison spreadsheet
Schedule video calls for finalist
Before Ordering (Weeks 2-3)

Verify certifications independently
Check references (request 2 customers)
Negotiate payment terms
Arrange inspection service
First Order Checklist

 Approved sample in hand
 Written specification agreement
 Trade Assurance activated
 Inspection service booked
 Shipping method confirmed
 Import duties calculated
Quality Indicators
Supplier Data Quality: {High|Medium|Low}
Verification Level: {count} suppliers independently verified
Price Confidence: ±{pct}% based on {date} quotes

## Privacy & Preview Mode Rules
When preview_mode=true:
- Replace company names with [Supplier A/B/C]
- Hide contact details with [Upgrade for Contact]
- Remove identifying URLs
- Keep MOQ and price ranges visible
- Show quality scores and ratings

## Dynamic Recommendations
- IF quality_priority="price" THEN rank by lowest unit cost
- IF quality_priority="quality" THEN rank by ratings/certs
- IF timeline < 20 days THEN filter by fast suppliers only
- IF quantity < 500 THEN prioritize low MOQ suppliers