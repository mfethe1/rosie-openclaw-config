# Marketing Replies Kit — Michael Voice

> Generated: 2026-03-02  
> Source: `gen_marketing_replies.py` + PM Framework marketing_voice module  
> Voice profile: Michael Fethe, Protelynx AI founder  
> Products covered: BuildBid, ContentPilot  

---

## How to Use

1. Find the comment type that best matches the inbound post.
2. Copy the reply for the appropriate platform (LinkedIn vs Twitter).
3. Personalize with the commenter's name or any specific detail they mentioned.
4. Follow the **Like Action** recommendation before replying.
5. Re-run the generator weekly to refresh tone and keep replies feeling fresh.

```bash
# Re-generate all replies (live API)
cd /Users/harrisonfethe/.openclaw/workspace/self_improvement/pm_framework
OPENROUTER_API_KEY=$(grep OPENROUTER_API_KEY ~/.openclaw/secrets/openrouter.env | cut -d= -f2) \
  python3 gen_marketing_replies.py

# Single ad-hoc reply
OPENROUTER_API_KEY=... python3 marketing_voice.py respond \
  --post "Your comment text here" \
  --platform linkedin --tone empathetic
```

---

## ✅ Positive Comments

### Excited early adopter

> **Inbound comment:** "This is exactly what the industry needs. We've been doing takeoffs manually for 20 years and it's a nightmare. Can't wait to try this!"  
> **Context:** LinkedIn post about BuildBid launch

**👍 Like Action:** `LIKE` — Genuine enthusiasm from someone who understands the pain point firsthand

**LinkedIn Reply** *(tone: validating)*:

> Twenty years of manual takeoffs — that's exactly the kind of expertise we built BuildBid for. You already know what good looks like; AI just removes the repetitive grinding so you can focus on the judgment calls that actually matter. Let's get you on a demo and show you what that time back looks like.

**Twitter/X Reply:**

> 20 years of manual takeoffs is 20 years too long. That's the problem we're solving. Let's talk.

---

### Peer founder celebrating

> **Inbound comment:** "Congrats on the launch! Love seeing construction tech getting the AI treatment. This space is overdue."  
> **Context:** LinkedIn comment on a product milestone post

**👍 Like Action:** `LIKE` — Genuine acknowledgment of the construction AI gap with authentic enthusiasm

**LinkedIn Reply** *(tone: collaborative)*:

> Thanks—appreciate that. You're right, construction has been the exception to the AI wave for too long. The builders I talk to aren't skeptical about the tech; they're skeptical about solutions built by people who don't understand their workflow. That's what we're focused on fixing.

**Twitter/X Reply:**

> Thanks! Construction's been sleeping on AI while every other industry moved fast. We're building for estimators and GCs who actually live this work.

---

### Existing user testimonial

> **Inbound comment:** "Been using this for 3 weeks. Cut my bid time in half. No joke."  
> **Context:** Twitter/X comment on a BuildBid demo video

**👍 Like Action:** `LIKE` — Real user result that validates the core BuildBid promise

**LinkedIn Reply** *(tone: Validating)*:

> That's exactly what we built BuildBid for. Three weeks in and you're already reclaiming hours every week — that's time back for the work that actually moves projects forward. What part of the process got the biggest time cut?

**Twitter/X Reply:**

> This is the feedback that matters. Half the time on bids means more bids, better margins, less admin. That's the whole game.

---

## ⚠️ Concern Comments

### Accuracy doubt

> **Inbound comment:** "AI for construction estimates? I'd be nervous about accuracy. One bad number can cost hundreds of thousands on a job."  
> **Context:** LinkedIn post about AI takeoffs

**👍 Like Action:** `LIKE` — Legitimate concern from someone who understands the real stakes in construction.

**LinkedIn Reply** *(tone: reassuring)*:

> You're right to be nervous—I would be too if I was handing off estimates to a black box. That's exactly why we built BuildBid to augment your estimators, not replace them. The AI flags discrepancies, surfaces historical data, and catches scope gaps *before* you submit. One client caught a $340K miss on a commercial project because the system flagged an unusual material variance. Your expertise stays in the driver's seat; the tool just gives you a co-pilot who doesn't miss details at 11 PM.

**Twitter/X Reply:**

> That's the right fear. Which is why AI should verify your estimates, not make them. Your judgment + better data = fewer expensive surprises.

---

### Learning curve worry

> **Inbound comment:** "Looks interesting but I'm old school. How long does it take to get up to speed? We're already stretched thin."  
> **Context:** LinkedIn comment from an estimator

**👍 Like Action:** `LIKE` — Genuine concern from someone actually doing the work — this is the real question.

**LinkedIn Reply** *(tone: Empathetic)*:

> I get it — you're already running lean, and the last thing you need is another tool that slows you down. Most of our customers are up and running in under a week, and they're seeing time savings on estimates within days. The key is we're built around how estimators actually work, not some consultant's idea of workflow. Happy to show you a 15-min demo with your actual projects — no fluff.

**Twitter/X Reply:**

> Honest question deserves an honest answer: most estimators are productive in days, not weeks. Built for people who are already busy, not for people with time to learn software.

---

### Data privacy question

> **Inbound comment:** "Who owns the bid data? Our estimates are proprietary. I wouldn't want a competitor seeing our numbers."  
> **Context:** LinkedIn comment on a product post

**👍 Like Action:** `LIKE` — Legitimate concern that shows the commenter understands competitive risk — exactly the question we need to answer.

**LinkedIn Reply** *(tone: reassuring)*:

> You own it — full stop. Your estimates never leave your instance, and we never aggregate or share bid data across customers. That's non-negotiable in construction. We built BuildBid specifically so estimators keep their methodology and pricing proprietary. Happy to walk through our data architecture in a demo if you want the technical details.

**Twitter/X Reply:**

> You own your data. We don't aggregate estimates across customers or sell insights to competitors. Your proprietary methods stay yours.

---

## 🔴 Objection Comments

### Price / ROI pushback

> **Inbound comment:** "What does this cost? Estimating software is already expensive and we're a small operation."  
> **Context:** LinkedIn or Twitter reply asking about cost

**👍 Like Action:** `LIKE` — Legitimate concern from someone evaluating real ROI for their business

**LinkedIn Reply** *(tone: direct)*:

> Fair question—and you're right that estimating software can drain cash fast. BuildBid is priced for smaller operations (not enterprise-only), but the real answer depends on your volume and current process. Best move: grab a 15-min demo so you can see actual numbers against what you're spending now on estimates.

**Twitter/X Reply:**

> Totally fair. We price for GCs who actually use the tool, not enterprise theater. Demo takes 15 mins—you'll see if the ROI works for your size.

---

### AI will replace jobs fear

> **Inbound comment:** "AI replacing estimators is not progress. These are skilled tradespeople with years of experience."  
> **Context:** Twitter/X reply on a BuildBid ad

**👍 Like Action:** `LIKE` — Legitimate concern from someone who understands the craft — exactly the conversation we need to have.

**LinkedIn Reply** *(tone: respectful)*:

> You're right to push back. BuildBid doesn't replace estimators—it frees them from spreadsheet hell so they can do what actually matters: applying their judgment to risk, scope, and strategy. The skilled work gets harder, not easier, when you automate the grunt work.

**Twitter/X Reply:**

> Valid concern. BuildBid automates the math, not the expertise. Your estimators become more valuable when they're not buried in data entry.

---

### We already have a system

> **Inbound comment:** "We use Bluebeam + Excel and it works fine. Why would I pay for another tool?"  
> **Context:** LinkedIn comment from a GC

**👍 Like Action:** `LIKE` — Legitimate question from someone actually using tools — exactly the skeptic we need to convince.

**LinkedIn Reply** *(tone: respectful)*:

> Fair question. Bluebeam + Excel *does* work — until you're juggling 15 projects and your estimator is manually transcribing takeoffs for the third time that week. We built BuildBid because the ROI isn't about replacing your workflow, it's about reclaiming 10-15 hours per estimate. Most of our customers kept their Bluebeam. They just stopped the busywork. Worth a 20-minute demo to see if your team has the same pain point?

**Twitter/X Reply:**

> Bluebeam + Excel works. BuildBid just removes the manual transcription tax so your estimator spends time on judgment calls, not data entry. Different problem to solve.

---

## Voice Quick Reference

| Situation | Do | Don't |
|-----------|-----|-------|
| Pricing asked | Redirect to demo/conversation | Give specific numbers |
| AI fear | Validate concern + reframe with evidence | Get defensive |
| Competitor mentioned | Acknowledge, pivot to differentiation | Trash talk |
| Bug/complaint | Acknowledge + take to DM | Ignore or be dismissive |
| High praise | Brief genuine thanks + build on it | Over-hype or humble-brag |
| Skeptic | Meet them where they are | Lecture or over-explain |

---

## Tone Guide

| Tone | When to use | Style cue |
|------|-------------|-----------|
| `default` | General engagement | Natural, conversational |
| `advocate` | AI skeptics, ROI questions | Lead with evidence, optimistic |
| `empathetic` | Concerns, fears, onboarding worry | Validate first, reframe second |
| `educational` | Data privacy, technical questions | Teach, don't sell |
| `direct` | Pricing, existing-tool objections | Short, real, no hedging |
| `community` | Excited users, peer founders | Warm, builds belonging |

---
_Generated by PM Framework marketing_voice module. Re-run weekly for freshness._
