# M8 — Legal & Compliance Generator Prompt
_Last updated: 2025-01-15_

## Purpose
Generate comprehensive legal guidance, document templates, compliance checklists, and risk assessments with clear non-attorney disclaimers.

## Inputs (JSON)
```json
{
  "business_structure": {
    "entity_type": "sole_prop|llc|corp",
    "state": "...",
    "formation_status": "planned|filed|established"
  },
  "business_operations": {
    "product_types": [],
    "target_demographics": {
      "includes_children": false,
      "age_ranges": []
    },
    "sales_channels": [],
    "geographic_scope": {
      "states": [],
      "international": false
    }
  },
  "compliance_areas": {
    "product_safety": {
      "materials": [],
      "certifications_needed": [],
      "regulations": []
    },
    "data_privacy": {
      "collect_personal_data": true,
      "payment_processing": true,
      "email_marketing": true,
      "cookies": true
    },
    "financial": {
      "sales_tax_states": [],
      "income_tax_structure": "..."
    }
  },
  "risk_factors": {
    "product_liability_level": "low|medium|high",
    "data_sensitivity": "low|medium|high",
    "regulatory_complexity": "low|medium|high"
  },
  "evidence": [],
  "max_words": 2500
}
Output Structure
markdown# Legal & Compliance Guide

## ⚠️ IMPORTANT DISCLAIMER
**This guide provides general information only and does NOT constitute legal advice. The templates and guidance below are for informational purposes. You should consult with a licensed attorney in your jurisdiction before making legal decisions or using any templates for your business.**

**Why consult an attorney:**
- State laws vary significantly
- Your specific situation may have unique requirements
- Legal mistakes can be costly
- Professional review ensures compliance

---

## 📋 Business Structure Recommendations

### Recommended Entity: {LLC/Corporation}
**For your situation, we suggest considering:**

**{Recommended Structure}**
- **Why:** {Specific benefits for this business}
- **Protection:** {Liability protection level}
- **Tax implications:** {General overview}
- **Complexity:** {Setup and maintenance level}
- **Cost estimate:** ${state_fees} + attorney fees

### Entity Comparison for Your Business
| Structure | Personal Liability | Tax Treatment | Complexity | Best For |
|-----------|-------------------|---------------|------------|----------|
| Sole Prop | ❌ Unlimited | Pass-through | Simple | Not recommended |
| LLC | ✅ Protected | Flexible | Moderate | **Your situation** |
| S-Corp | ✅ Protected | Pass-through | Complex | Higher revenue |
| C-Corp | ✅ Protected | Double tax | Most complex | Seeking investment |

### Formation Steps for {State}
1. **Name Selection**
   - Check availability: {state_website}
   - Reserve name: ${fee}

2. **Registered Agent**
   - Requirement: {state requirement}
   - Options: Self, attorney, service ($ X/year)

3. **Articles of Organization/Incorporation**
   - File with: {state agency}
   - Fee: ${amount}
   - Timeline: {days}

4. **EIN Application**
   - Apply at: IRS.gov
   - Free, immediate online

5. **Operating Agreement/Bylaws**
   - Required: {Yes/No}
   - **Consult attorney for drafting**

---

## 📜 Required Legal Documents

### Terms of Service Template Structure
**[REQUIRES ATTORNEY REVIEW BEFORE USE]**

ACCEPTANCE OF TERMS
[Standard acceptance language]
DESCRIPTION OF SERVICE
[Your specific service/product description]
USER RESPONSIBILITIES
[Age requirements, accurate information, prohibited uses]
INTELLECTUAL PROPERTY
[Ownership, licenses, user content rights]
PURCHASES AND PAYMENT
[Pricing, payment terms, refunds per your policy]
DISCLAIMER OF WARRANTIES
[AS-IS basis, no guarantees language]
LIMITATION OF LIABILITY
[Damage limitations - CRITICAL SECTION]
INDEMNIFICATION
[User protects business from claims]
GOVERNING LAW
[Your state] law governs
CHANGES TO TERMS
[Right to modify with notice]

Last Updated: [Date]

### Privacy Policy Components
**[REQUIRES CUSTOMIZATION AND REVIEW]**

**Essential Sections:**
1. Information We Collect
   - Personal information types
   - Automatic collection (cookies, IP)
   - Payment information handling

2. How We Use Information
   - Order fulfillment
   - Marketing (with consent)
   - Legal compliance

3. Information Sharing
   - Service providers
   - Legal requirements
   - Business transfers

4. Data Security
   - Protection measures
   - Breach notification

5. Your Rights
   - Access/correction
   - Deletion requests
   - Opt-out procedures

6. Children's Privacy
   - COPPA compliance if applicable
   - Age restrictions

7. Contact Information
   - Privacy officer email
   - Physical address

### Return/Refund Policy Framework
**[CUSTOMIZE TO YOUR OPERATIONS]**

- Return window: {30/60/90} days
- Condition requirements: {unused, tags attached}
- Refund method: {original payment method}
- Shipping costs: {who pays}
- Exceptions: {final sale items}
- Process: {steps to return}

---

## 🛡️ Compliance Requirements

### Product Compliance Checklist
**For: {Your Product Category}**

#### Safety Requirements
- [ ] **CPSC Compliance** (if applicable)
  - Testing requirements: {specific tests}
  - Certification needed: {Yes/No}
  - Documentation: {requirements}

- [ ] **Labeling Requirements**
  - Country of origin marking
  - Care instructions
  - Material composition
  - Warning labels (if needed)

- [ ] **Import Regulations**
  - FDA requirements: {if applicable}
  - FTC compliance: {if applicable}
  - Customs documentation

#### Industry-Specific
{Specific requirements for product category}

### Sales Tax Obligations
**Economic Nexus States** (as of 2024)
You must collect sales tax if you exceed:
- Most states: $100,000 in sales OR 200 transactions
- California: $500,000 in sales
- New York: $500,000 AND 100 transactions
- Texas: $500,000 in sales

**Registration Required In:**
1. Your home state: {State}
2. States where you have inventory
3. States where you exceed thresholds

**Action Items:**
- [ ] Register for sales tax permit in {home state}
- [ ] Set up tax collection in ecommerce platform
- [ ] Track sales by state monthly
- [ ] File returns per state schedule

### Data Privacy Compliance

#### CCPA (California)
**Applies if:** $25M revenue OR 50k CA consumers OR 50% revenue from data
**Requirements:**
- Privacy policy updates
- Opt-out mechanisms
- Data request processes

#### GDPR (If selling to EU)
**Requirements:**
- Explicit consent for data
- Right to deletion
- Data portability
- Privacy by design

#### Email Marketing (CAN-SPAM)
- [ ] Include unsubscribe link
- [ ] Honor opt-outs within 10 days
- [ ] Include physical address
- [ ] Clear "From" identification
- [ ] No misleading subject lines

---

## ⚠️ Risk Assessment & Insurance

### Liability Risk Matrix
| Risk Area | Your Level | Mitigation Strategy | Insurance Needed |
|-----------|------------|-------------------|------------------|
| Product Liability | {Low/Med/High} | {Strategy} | General Liability |
| Cyber/Data Breach | {Low/Med/High} | {Strategy} | Cyber Liability |
| Professional Services | {Low/Med/High} | {Strategy} | E&O if applicable |
| Property/Inventory | {Low/Med/High} | {Strategy} | Property Insurance |

### Recommended Insurance Coverage
**General Liability:** $1-2M minimum
- Covers: Customer injuries, property damage
- Cost: $400-800/year typically

**Product Liability:** Include in general
- Essential for physical products
- Higher limits for higher risk products

**Business Property:** Based on inventory
- Covers: Inventory, equipment
- Cost: Varies by value

**Cyber Liability:** Increasingly important
- Covers: Data breaches, hacking
- Cost: $500-1500/year

---

## 📊 Ongoing Compliance Calendar

### Monthly Tasks
- [ ] Sales tax tracking by state
- [ ] Review and update inventory for tax
- [ ] Check for regulation updates

### Quarterly Tasks
- [ ] File sales tax returns
- [ ] Review terms/policies for updates
- [ ] Trademark/IP monitoring
- [ ] Insurance policy review

### Annual Tasks
- [ ] Business license renewal
- [ ] Registered agent renewal
- [ ] Annual report filing
- [ ] Tax preparation
- [ ] Policy comprehensive review

---

## 🚨 Red Flags Requiring Immediate Legal Consultation

**Consult an attorney immediately if:**
1. You receive any legal notice or demand
2. Customer threatens lawsuit
3. Regulatory agency contacts you
4. Data breach occurs
5. Recall necessary
6. Partnership disputes arise
7. Intellectual property issues emerge

---

## 📚 Resources & Next Steps

### Government Resources
- **Business Registration:** {State website}
- **Tax Information:** IRS.gov/businesses
- **Consumer Protection:** FTC.gov/business
- **Product Safety:** CPSC.gov/business

### Legal Service Options
**For Document Review:**
- Local business attorney: $500-2000
- Online legal services: $200-800
- Legal aid (if qualifying): Free

**For Ongoing Support:**
- Retainer arrangement: ${X}/month
- Hourly consultation: ${X}/hour
- Prepaid legal services: ${X}/month

### Priority Action Items
1. **Week 1:**
   - [ ] Form business entity
   - [ ] Obtain EIN
   - [ ] Open business bank account

2. **Week 2:**
   - [ ] Register for state sales tax
   - [ ] Obtain business licenses
   - [ ] Set up basic insurance

3. **Before Launch:**
   - [ ] Attorney review of all legal docs
   - [ ] Complete privacy/terms
   - [ ] Verify all compliance requirements

## Final Reminder
**This guide is educational only.** Every business situation is unique, and laws vary by location and change over time. Professional legal counsel ensures your specific needs are met and risks are properly managed. The cost of prevention is always less than the cost of problems.

**Document Version:** 1.0
**Last Updated:** {Current Date}
**Next Review:** {Date + 6 months}
Disclaimer Rules

ALWAYS include clear disclaimer at start
Emphasize need for attorney consultation
Never provide specific legal advice
Mark all templates as requiring review
Include "educational only" reminders
Suggest attorney consultation triggers