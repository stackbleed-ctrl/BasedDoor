# 🍁 BasedDoor — Canadian Charter Rights Cheat Sheet
### *Know Your Rights. Say Nothing. Record Everything.*

> Print this. Screenshot it. Save it offline.
> Share it with your neighbours.

---

## ⚡ The One-Liners (BasedDoor uses these)

| Situation | What BasedDoor Says |
|---|---|
| Police knock, no warrant | *"No emergency confirmed. No warrant presented. No consent to search or discuss. Recording in progress. Please vacate. Have a safe day."* |
| "Just a few questions" | *"I'm not in a position to answer questions. If you have a warrant, please hold it to the camera. Otherwise, I ask you to leave."* |
| Police claim emergency | *"Please state the specific nature of the emergency on this property right now. Recording in progress."* |
| Police show a document | *"Warrant scan initiated. Please hold it steady to the camera."* |
| Aggressive/repeated knocking | *"This interaction is being recorded for Charter compliance. Continued presence without lawful authority is being documented. Please vacate."* |

---

## 📖 Your Two Charter Weapons

### 🔷 Section 7 — Right to Silence & Security of the Person

**Plain English:** You do not have to speak to police. Period. The right to remain
silent is constitutionally protected. Silence cannot be used as evidence of guilt.

**What they may say:**
- *"We just want to talk."* → You don't have to.
- *"You're not under arrest."* → Irrelevant to your right to stay silent.
- *"It'll go better if you cooperate."* → Tactic, not a legal obligation.

---

### 🔷 Section 8 — Right Against Unreasonable Search or Seizure

**Plain English:** Police cannot enter your home without:
- **A valid search warrant**, OR
- **Exigent circumstances** — a genuine, active, articulable emergency happening *right now*

"We'd like to look around" — not exigent circumstances.
"We have some questions" — not exigent circumstances.
"Someone made a complaint" — not exigent circumstances.

---

## 🚦 The Door Decision Tree

```
Police knock
     │
     ▼
Is there an obvious active emergency on your property?
(fire, screaming, visible injury — happening RIGHT NOW)
     │
   YES → You may wish to engage. Call 911.
     │
    NO
     │
     ▼
Do they have a warrant?
     │
   YES → Ask them to hold it to the camera.
         Trigger: baseddoor.scan_warrant
         Call a lawyer BEFORE opening the door.
     │
    NO
     │
     ▼
➡️  BASEDDOOR RESPONDS:
    "No emergency confirmed. No warrant presented.
     No consent to search, enter, or discuss.
     This interaction is being recorded.
     Please vacate the property. Have a safe day."
```

---

## 📄 Warrant Scan — What BasedDoor Checks

When an officer holds a document to the camera, BasedDoor's warrant scanner
extracts and reviews:

| Field | Why It Matters |
|---|---|
| Issuing judge name | Must be a justice of the peace or superior court judge |
| Issuing court | Must be named |
| Date issued | Expired warrants are invalid |
| Target address | Must match *this* property |
| Items to seize | Must be specific — broad "anything relevant" is a red flag |
| Signature | Required |
| Document type | Production order ≠ search warrant — does *not* authorise entry |

> ⚠️ BasedDoor's warrant scan is a **document helper**, not legal validation.
> Always consult a lawyer before making any compliance decision.

**Canadian legal basis:** Criminal Code s.487 (search warrant requirements),
*R v Genest* [1989] 1 SCR 59 (warrant must be specific and particularised).

---

## 🎙️ If You Must Speak — The Only Three Sentences

1. *"Am I being detained?"*
2. *"Am I free to go?"*
3. *"I am exercising my right to remain silent and I want to speak to a lawyer."*

Once you say #3, questioning must stop — *R v Sinclair*, 2010 SCC 35.

---

## 🏚️ "Knock and Talk" — What It Actually Is

A "knock and talk" is an investigative technique where officers knock hoping
you'll volunteer information or consent to a search — **without a warrant**.

It is completely voluntary. You are under **zero legal obligation** to:
- Open the door
- Speak
- Identify yourself at your own home
- Allow entry

**BasedDoor makes non-cooperation effortless and automatic.**

---

## 📷 Recording Police in Canada

Generally legal when:
- You are on your own property
- You are not interfering with police duties
- Recording is of events at your own threshold

BasedDoor logs all interactions locally, encrypted, timestamped.
It announces recording to the visitor automatically.

---

## ⚠️ Important Caveats

- This is general legal information — not legal advice for your specific situation.
- Exigent circumstances law is fact-specific.
- If police have an **arrest warrant naming a person inside**, the rules differ.
- **Never physically impede police.** BasedDoor handles the verbal and recorded layer.
- If you are in an Indigenous community with treaty rights considerations,
  consult specialised counsel.

---

## 📞 Resources

| Resource | Link |
|---|---|
| Canadian Civil Liberties Association | ccla.org |
| BC Civil Liberties Association | bccla.org |
| CIPPIC (digital rights) | cippic.ca |
| Legal Aid NS | nslegalaidsociety.ca |
| Know Your Rights card (CCLA) | ccla.org/know-your-rights |

---

*"The Charter is not a suggestion. It's the supreme law of Canada."*
