# M7 — Website Brief Generator Prompt
_Last updated: 2025-01-15_

## Purpose
Generate comprehensive website specifications including sitemap, wireframes, conversion optimization checklist, and platform-specific implementation guides.

## Inputs (JSON)
```json{
"website_context": {
"from_m5": {
"brand_guidelines": {
"voice": "...",
"personality": [],
"visual_direction": "..."
},
"key_messages": [],
"value_propositions": []
},
"from_m6": {
"conversion_goals": [],
"traffic_sources": [],
"customer_journey": {}
},
"product_catalog": {
"sku_count": 0,
"categories": [],
"variants": [],
"pricing_tiers": []
}
},
"website_requirements": {
"platform_preference": "shopify|wordpress|custom",
"budget_range": "...",
"timeline": "...",
"technical_level": "diy|developer|agency",
"features_needed": {
"ecommerce": true,
"subscription": false,
"multilingual": false,
"blog": true,
"customer_accounts": true,
"reviews": true,
"wishlist": false,
"live_chat": true
},
"integrations": [
"email_platform",
"analytics",
"shipping",
"payment_gateway"
]
},
"competitor_analysis": {
"competitor_sites": [],
"best_practices": [],
"avoid": []
},
"evidence": [],
"max_words": 2500
}

## Output Structure

```markdownWebsite Technical Brief & Implementation Guide🌐 Website Strategy OverviewSite Objectives (Prioritized)

Primary: {e.g., Convert visitors to first purchase}
Secondary: {e.g., Build email list}
Tertiary: {e.g., Establish authority}
Success Metrics
MetricCurrent3 Month Target6 Month TargetConversion RateN/A{pct}%{pct}%AOVN/A${amount}${amount}Bounce RateN/A<{pct}%<{pct}%Page LoadN/A<3s<2sPlatform Recommendation
Recommended: {Platform}

Why: {Specific reasons based on requirements}
Cost: ${setup} + ${monthly}/mo
Time to launch: {timeframe}
Alternative Options:

{Platform 2}: Better for {scenario}
{Platform 3}: Consider if {condition}
🗺️ Information ArchitectureSitemap Structure
Homepage
├── Shop
│   ├── All Products
│   ├── {Category 1}
│   │   ├── {Subcategory}
│   │   └── {Subcategory}
│   ├── {Category 2}
│   ├── New Arrivals
│   ├── Best Sellers
│   └── Sale
├── About
│   ├── Our Story
│   ├── Mission & Values
│   └── Sustainability
├── Resources
│   ├── Blog
│   ├── Size Guide
│   ├── Care Instructions
│   └── FAQs
├── Account
│   ├── Login/Register
│   ├── Orders
│   ├── Wishlist
│   └── Settings
└── Footer
    ├── Customer Service
    ├── Policies
    ├── Contact
    └── Social LinksPage Priority & Purpose
PagePriorityPrimary GoalSecondary GoalHomepageCriticalConvert/EngageBuild trustProduct PageCriticalConvertInformCategoryHighBrowseFilter/FindCartCriticalCheckoutUpsellAboutMediumTrustBrand storyBlogLowSEO/ValueEngagement📱 Wireframe SpecificationsHomepage Wireframe
┌─────────────────────────────────┐
│ Announcement Bar (Free Ship $X) │
├─────────────────────────────────┤
│ Logo    Nav Nav Nav    Cart     │
├─────────────────────────────────┤
│                                 │
│     Hero Image/Video            │
│     Headline (7 words max)     │
│     Subhead (15 words max)     │
│     [CTA Button] [Learn More]  │
│                                 │
├─────────────────────────────────┤
│ Value Props (3 columns)         │
│ ✓ Benefit  ✓ Benefit  ✓ Benefit│
├─────────────────────────────────┤
│ Featured Products (4-6)         │
│ [P][P][P][P]                   │
├─────────────────────────────────┤
│ Social Proof                    │
│ ⭐⭐⭐⭐⭐ "Review quote"        │
├─────────────────────────────────┤
│ Category Cards                  │
│ [Cat 1] [Cat 2] [Cat 3]        │
├─────────────────────────────────┤
│ Email Capture (10% off)         │
├─────────────────────────────────┤
│ Footer with links               │
└─────────────────────────────────┘Product Page Wireframe
┌─────────────────────────────────┐
│ Breadcrumbs > Category > Product│
├─────────────────────────────────┤
│          │  Product Name        │
│  Images  │  ⭐⭐⭐⭐⭐ (reviews)  │
│  Gallery │  Price               │
│          │  [Variant Selectors] │
│ [thumb]  │  [Add to Cart]       │
│ [thumb]  │  ✓ In Stock          │
│          │  Trust badges        │
├─────────────────────────────────┤
│ Tabs: Description | Specs | Ship│
├─────────────────────────────────┤
│ Customer Reviews                │
├─────────────────────────────────┤
│ Related Products                │
└─────────────────────────────────┘Mobile Responsiveness Notes

Hamburger menu for navigation
Single column layouts
Thumb-friendly buttons (min 44px)
Sticky add-to-cart on product pages
Optimized images for mobile
🎯 Conversion Optimization ChecklistAbove the Fold Must-Haves

 Clear value proposition (5 seconds to understand)
 Prominent CTA (contrasting color)
 Trust signals (badges, testimonials)
 Product/benefit visual
 Mobile-optimized layout
Product Page Optimization

 Multiple high-quality images
 Zoom functionality
 Size/variant selectors
 Urgency indicators (stock levels)
 Social proof near buy button
 Clear shipping info
 Easy returns policy link
 Cross-sell/upsell section
 Recently viewed products
Cart & Checkout

 Guest checkout option
 Progress indicator
 Security badges
 Multiple payment options
 Shipping calculator
 Promo code field
 Order summary visible
 Trust signals throughout
Trust Builders

 SSL certificate/HTTPS
 Professional design
 Contact information visible
 Return policy clear
 Customer reviews
 Media mentions/logos
 Guarantee badges
 Live chat option
🛠️ Platform-Specific Implementation{Shopify} Setup GuideTheme Selection
Recommended Theme: {Theme name}

Cost: ${amount}
Why: {Reasons specific to needs}
Alternative Free Theme: {Dawn/Craft}

Customization needed: {List}
Essential Apps (Month 1)
AppPurposeCostPriorityKlaviyoEmail marketingFree-$20CriticalJudge.meReviewsFree-$15CriticalSEO ManagerSEO optimization$20HighPrivyPopupsFree-$20MediumSetup Sequence

Week 1: Foundation

 Choose theme
 Set up payment processing
 Configure shipping zones
 Add legal pages



Week 2: Products

 Upload product catalog
 Write descriptions
 Set up collections
 Configure variants



Week 3: Optimization

 Install essential apps
 Set up email flows
 Add reviews system
 Test checkout flow



Week 4: Launch Prep

 SEO optimization
 Speed optimization
 Mobile testing
 Analytics setup


💻 Technical SpecificationsPerformance Requirements

Page load: <3 seconds
Mobile score: >90/100
Desktop score: >95/100
Core Web Vitals: Pass
SEO Foundation
URL Structure:

Products: /products/{product-name}
Categories: /collections/{category}
Blog: /blog/{post-title}
Meta Templates:
Title: {Product} | {Category} | {Brand}
Description: {Product description first 155 chars}Schema Markup Required:

Product schema
Review schema
Breadcrumb schema
Organization schema
Analytics Setup
Google Analytics 4:

Enhanced ecommerce
Conversion tracking
Audience building
Facebook Pixel Events:

PageView
ViewContent
AddToCart
InitiateCheckout
Purchase
Custom Events:

Email signup
Review submission
Wishlist add
📝 Content RequirementsPage-Specific Content NeedsHomepage

Hero headline (7 words)
Hero subheadline (15 words)
3 value propositions (10 words each)
Welcome paragraph (50 words)
CTA buttons text (2-4 words)
Product Pages (per product)

Product title
Short description (25 words)
Long description (150 words)
Features list (5-8 points)
Specifications
Care instructions
About Page

Brand story (300 words)
Mission statement (50 words)
Founder bio (150 words)
Values (3-5 with descriptions)
Photography Requirements
TypeQuantitySpecificationsProduct - Hero1 per SKU2000x2000px, white bgProduct - Lifestyle2-3 per productNatural settingProduct - Detail2-3 per productClose-ups, textureHomepage Hero3-51920x800pxCategory Headers1 per category1920x400pxAbout Page3-5Various, authentic🚀 Launch ChecklistPre-Launch Testing

 All links working
 Forms submitting correctly
 Payment processing test
 Mobile responsiveness check
 Cross-browser testing
 Speed optimization complete
 SEO basics configured
 Analytics tracking verified
 Legal pages complete
 SSL certificate active
Soft Launch (Friends & Family)

 10 test orders processed
 Feedback collected
 Bugs fixed
 Copy refined
Public Launch

 Announcement ready
 Email campaign scheduled
 Social posts prepared
 Support system ready
Development Handoff Package
Included Deliverables:

This technical brief
Wireframes (all pages)
Content spreadsheet
Asset library access
Brand guidelines
Third-party integrations list
Developer Requirements:

Platform expertise: {Shopify}
Timeline: {4-6 weeks}
Budget: ${amount}
Post-launch support: {terms}


## Platform Logic
- IF budget < $500 THEN recommend Shopify Basic
- IF products > 100 THEN consider Shopify Plus
- IF heavy customization THEN recommend WordPress/WooCommerce
- IF subscription model THEN specific platform features
- IF B2B THEN platform must support wholesale