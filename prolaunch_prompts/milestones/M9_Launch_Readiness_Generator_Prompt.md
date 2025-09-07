# M9 — Launch Readiness Generator Prompt
_Last updated: 2025-01-15_

## Purpose
Generate comprehensive launch readiness checklist aggregating all milestone data, identifying critical path items, and providing go/no-go assessment.

## Inputs (JSON)
```json
{
  "milestone_completion": {
    "m0": {"status": "complete", "score": 0, "data": {}},
    "m1": {"status": "complete", "margin": 0, "data": {}},
    "m2": {"status": "complete", "confidence": 0, "data": {}},
    "m3": {"status": "complete", "suppliers": 0, "data": {}},
    "m4": {"status": "complete", "runway": 0, "data": {}},
    "m5": {"status": "complete", "brand_ready": true, "data": {}},
    "m6": {"status": "complete", "campaigns": 0, "data": {}},
    "m7": {"status": "complete", "website_ready": true, "data": {}},
    "m8": {"status": "complete", "compliant": true, "data": {}}
  },
  "launch_parameters": {
    "target_date": "YYYY-MM-DD",
    "soft_launch": true,
    "inventory_status": {
      "on_hand": 0,
      "on_order": 0,
      "lead_time": 0
    },
    "team_readiness": {
      "founder": "ready|partial|not_ready",
      "support": "ready|partial|not_ready",
      "fulfillment": "ready|partial|not_ready"
    },
    "systems_status": {
      "website": "ready|testing|building",
      "payment": "ready|testing|setup",
      "shipping": "ready|testing|setup",
      "customer_service": "ready|testing|setup"
    }
  },
  "risk_factors": {
    "identified_risks": [],
    "mitigation_plans": [],
    "contingencies": []
  },
  "evidence": [],
  "max_words": 2000
}
Output Structure
markdown# 🚀 Launch Readiness Assessment

## Overall Readiness Score: {0-100}%

### Visual Status
Product     ████████████████████ 100% ✅
Operations  ████████████░░░░░░░░  65% ⚠️
Marketing   ████████████████░░░░  85% ✅
Legal       ████████████████████ 100% ✅
Financial   ████████████████░░░░  80% ✅
Tech        ███████████░░░░░░░░░  55% 🔧
OVERALL     ████████████████░░░░  81%
Status: READY WITH CONDITIONS

## 🎯 Launch Go/No-Go Decision

### Launch Recommendation: {GO with Conditions | NO-GO | FULL GO}

**Bottom Line:** {One paragraph assessment of readiness}

### Critical Success Factors
✅ **Ready:** {What's fully prepared}
⚠️ **Needs Attention:** {What needs work but isn't blocking}
🚨 **Blocking Issues:** {What must be fixed before launch}

---

## ✅ 50-Point Launch Checklist

### Product & Inventory (10 points)
- [x] Product finalized and tested - M0: Viability {score}
- [x] Unit economics validated - M1: {margin}% margin
- [x] Supplier confirmed - M3: {supplier count} verified
- [x] Initial inventory received/ordered - {status}
- [x] Quality control process defined
- [x] Packaging finalized
- [x] Product photography complete - M7 ready
- [ ] Backup supplier identified
- [x] Return/defect process defined
- [ ] Safety certifications obtained

**Score: 8/10** {emoji}

### Marketing & Brand (10 points)
- [x] Brand positioning defined - M5 complete
- [x] Website live and tested - M7: {status}
- [x] Social media profiles created
- [x] Email list started - {count} subscribers
- [ ] Launch campaign created - M6: {campaign count}
- [x] Content calendar planned - 30 days ready
- [ ] PR/influencer outreach done
- [x] Customer service scripts ready
- [ ] Reviews system activated
- [ ] Referral program setup

**Score: 7/10** {emoji}

### Operations & Fulfillment (10 points)
- [x] Payment processing active
- [ ] Shipping rates configured
- [x] Fulfillment process tested
- [ ] Inventory management system
- [x] Order notification system
- [ ] Customer service hours set
- [x] Return policy published
- [ ] FAQ section complete
- [ ] Order tracking enabled
- [ ] Packaging supplies stocked

**Score: 6/10** {emoji}

### Financial & Legal (10 points)
- [x] Business entity formed - M8
- [x] EIN obtained
- [x] Business bank account
- [x] Sales tax registration
- [ ] Business insurance active
- [x] Terms of service published
- [x] Privacy policy published
- [x] Financial tracking system
- [ ] Break-even timeline clear - M4: Month {n}
- [x] Operating capital secured - ${amount}

**Score: 8/10** {emoji}

### Technology & Analytics (10 points)
- [ ] Website speed optimized (<3s)
- [x] Mobile responsive verified
- [ ] SSL certificate active
- [x] Analytics installed (GA4)
- [x] Pixel tracking active
- [ ] Email automation setup
- [ ] Backup systems in place
- [x] Security measures implemented
- [ ] 404/error pages configured
- [ ] XML sitemap submitted

**Score: 6/10** {emoji}

### **Total Checklist Score: 35/50 (70%)**

---

## 🔴 Critical Path Items

### Must Fix Before Launch (Red Flags)
1. **{Critical Issue 1}**
   - Impact: {Description}
   - Solution: {Specific steps}
   - Time needed: {hours/days}
   - Owner: {who}

2. **{Critical Issue 2}**
   - Impact: {Description}
   - Solution: {Specific steps}
   - Time needed: {hours/days}
   - Owner: {who}

### Should Fix Soon (Yellow Flags)
1. **{Important Issue 1}**
   - Impact: {Description}
   - Can launch without but: {consequence}
   - Fix by: {date}

2. **{Important Issue 2}**
   - Impact: {Description}
   - Can launch without but: {consequence}
   - Fix by: {date}

---

## 📅 Launch Timeline & Sequence

### T-Minus Launch Schedule
**Target Launch: {Date}** ({days} days away)

#### Week of {Date} (T-14 days)
- [ ] Mon: Final inventory check
- [ ] Tue: Complete website testing
- [ ] Wed: Launch email sequence setup
- [ ] Thu: Team briefing/training
- [ ] Fri: Social content scheduled

#### Week of {Date} (T-7 days)
- [ ] Mon: Soft launch to friends/family
- [ ] Tue: Gather feedback, fix issues
- [ ] Wed: Influencer packages sent
- [ ] Thu: PR outreach completed
- [ ] Fri: Final system checks

#### Launch Week
- [ ] Day -2: Final preparations
- [ ] Day -1: Team ready positions
- [ ] Day 0: Launch! 🚀
- [ ] Day +1: Monitor and respond
- [ ] Day +2: First optimization

---

## 💰 Financial Launch Readiness

### Capital Position
**Available Capital:** ${amount}
**Required for Launch:** ${amount}
**Buffer Available:** ${amount} ({months} months runway)

### Day 1 Projections
- Expected Orders: {range}
- Revenue Range: ${min} - ${max}
- Inventory Coverage: {days}

### Week 1 Targets
- Orders: {target}
- Revenue: ${target}
- CAC Target: ${amount}
- Key Metric: {metric}

---

## 📊 Success Metrics & Monitoring

### Launch Day KPIs
| Metric | Target | Alert If | Dashboard Link |
|--------|--------|----------|----------------|
| Traffic | {number} | <{number} | [Analytics] |
| Conversion | {pct}% | <{pct}% | [Analytics] |
| CAC | ${amount} | >${amount} | [Ads] |
| Orders | {number} | <{number} | [Shop] |

### Week 1 Goals
- Revenue: ${amount}
- Email signups: {number}
- Social followers: +{number}
- Reviews: {number}

### Month 1 Milestones
- Break-even day: Day {n}
- Reorder point: Day {n}
- Scaling decision: Day {n}

---

## 🎬 Launch Day Playbook

### Pre-Launch (Night Before)
- [ ] 10:00 PM: Final inventory count
- [ ] 10:30 PM: Test order placed and confirmed
- [ ] 11:00 PM: Team communication check
- [ ] 11:30 PM: Social posts scheduled
- [ ] 12:00 AM: Get rest!

### Launch Morning
- [ ] 8:00 AM: Systems check
- [ ] 8:30 AM: Team standup
- [ ] 9:00 AM: Send launch email
- [ ] 9:15 AM: Social media posts live
- [ ] 9:30 AM: Monitor incoming traffic
- [ ] 10:00 AM: First order celebration! 🎉

### Launch Day Monitoring
- Every 30 min: Check vital signs
- Every hour: Team check-in
- Every 2 hours: Social engagement
- End of day: Full debrief

---

## 🛡️ Contingency Plans

### If Things Go Wrong

**Website Crashes:**
→ Immediate: {backup plan}
→ Communication: {message template}
→ Recovery: {steps}

**No Sales:**
→ Hour 4: {action}
→ Hour 8: {action}
→ Day 2: {action}

**Too Many Sales:**
→ Inventory: {allocation strategy}
→ Communication: {waitlist strategy}
→ Fulfillment: {priority system}

**Negative Feedback:**
→ Response: {template}
→ Resolution: {process}
→ Learning: {improvement system}

---

## 📋 Final Pre-Launch Checklist

### 48 Hours Before
- [ ] All systems tested
- [ ] Inventory confirmed
- [ ] Team briefed
- [ ] Content ready
- [ ] Backup plans documented

### 24 Hours Before
- [ ] Final website review
- [ ] Payment test
- [ ] Email scheduled
- [ ] Social scheduled
- [ ] Rest planned

### Launch Morning
- [ ] Coffee ready ☕
- [ ] Team assembled
- [ ] Monitoring active
- [ ] Celebration planned
- [ ] Deep breath taken

## 🎯 Launch Readiness Declaration

Based on the assessment above:

**I, [Founder Name], confirm that:**
- [ ] I understand the risks identified
- [ ] I accept the current readiness level
- [ ] I commit to addressing critical items
- [ ] I'm prepared for launch day
- [ ] I'm excited to begin this journey!

**Launch Decision:** [GO | NO-GO | DELAY TO: {date}]

**Signed:** _________________________ Date: _____________

---

## 🎉 Congratulations!
You've completed all 9 ProLaunch milestones. Whether you launch today or after addressing the remaining items, you're more prepared than 90% of first-time founders.

**Remember:**
- Perfect is the enemy of done
- You can iterate after launch
- Customer feedback is gold
- Every expert was once a beginner

**You've got this! 🚀**
Readiness Calculation Logic
javascript// Overall readiness score calculation
const weights = {
  product: 0.25,
  marketing: 0.20,
  operations: 0.20,
  financial: 0.20,
  tech: 0.15
};

const calculate_readiness = (scores) => {
  const weighted_score = Object.keys(scores).reduce((total, category) => {
    return total + (scores[category] * weights[category]);
  }, 0);
  
  if (weighted_score >= 90) return "FULL GO";
  if (weighted_score >= 70) return "GO WITH CONDITIONS";
  return "NO-GO";
};
Auto-population Rules

Pull viability score from M0
Pull margin data from M1
Pull supplier count from M3
Pull break-even from M4
Pull campaign count from M6
Aggregate all red flags across milestones
Calculate days until target launch