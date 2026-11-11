---
name: meta-email-verification-troubleshoot
description: "Use when a Meta/Facebook confirmation, authorization, or 2FA code email isn't arriving in someone's inbox, to troubleshoot Gmail delivery systematically before assuming the account is broken."
---

# Troubleshooting a missing Meta/Facebook verification email

When someone reports that a Meta/Facebook confirmation, authorization, or two-factor code email never arrives (a common symptom when an ad account or Business Manager gets a security block, e.g. error codes like #3858385), don't just tell them to "check spam and wait." Walk through this checklist — most of the time the email did arrive, it's just not visible where they're looking.

## 1. Search by the exact sender and subject, not a vague keyword

Meta's authorization emails come from a specific address with a specific subject line:
- Sender: `notification@facebookmail.com`
- Subject (Spanish UI): "Confirma el correo electrónico para la autorización de Facebook"

A search for "facebook" in the inbox is not equivalent to searching for this sender — it misses emails that are archived, labeled, or otherwise routed out of the main view. In Gmail, use the exact search:

```
from:notification@facebookmail.com
```

This searches across all folders (inbox, spam, promotions, archived) at once, which a visual scroll through the inbox does not.

## 2. Check Gmail filters and blocked addresses

Go to Gmail → Settings (⚙️) → "Filters and Blocked Addresses" ("Filtros y direcciones bloqueadas"). Look for:
- Any filter that auto-deletes, auto-archives, or auto-marks-as-read mail from `facebookmail.com` — this is the most dangerous failure mode, because the email never lands anywhere visible, not even spam.
- Whether `facebookmail.com` or the sender address ended up on the blocked-addresses list, even by accident.

## 3. Confirm the exact email address on file

Have the person verify, inside their Meta/Facebook account settings, that the notification email on file is character-for-character correct (no stray space, extra dot, or typo). A mismatched address on file will make the email "never arrive" forever, no matter how many times it's resent — because it's not being sent to the mailbox they're checking.

## 4. Check that email notifications aren't disabled in Meta's own settings

Meta has a separate setting for whether it sends email notifications at all. If security/authorization notifications are toggled off, no amount of "resend code" will produce an email.

## 5. Check "All Mail," not just Inbox

A filter can archive a message (remove it from Inbox) without marking it spam or deleting it. In that case it won't appear in Inbox or Spam — only in "All Mail" ("Todos los correos"). Always check there before concluding the email never arrived.

## Personal Gmail vs. Google Workspace — scope the advice correctly

Meta's own troubleshooting article (as of Sept 2026) also lists domain-admin-level fixes: adding `facebookmail.com` as a safe sender at the mail server level, whitelisting Facebook's SPF IP ranges, and PowerShell transport rules for Microsoft Exchange/Outlook (bypassing Focused Inbox / Clutter). Before pointing someone at those steps, confirm whether the mailbox in question is:
- **A personal @gmail.com account** — none of the server-admin/Exchange steps apply; only steps 1–5 above are relevant, and the person is effectively their own "admin" (they can only use Gmail's own filter/block-list UI, not server-side allowlisting).
- **Google Workspace or Microsoft Exchange (a managed business domain)** — the IT admin can additionally add `facebookmail.com` as a safe sender, whitelist Meta's SPF IP ranges, and (for Exchange/Outlook specifically) create transport rules so mail bypasses Focused Inbox/Clutter and lands in the primary inbox.

Ask which kind of mailbox it is before recommending admin-level fixes — recommending Exchange PowerShell cmdlets to someone on a personal Gmail account is a dead end.

## Why this matters

In practice, the email has very often actually arrived — it's just been auto-filtered, archived, or sent to a slightly wrong address, and a generic "wait and check spam" answer misses all of these. Searching by the exact sender across all folders, and checking filters/blocked addresses, resolves the great majority of "the code never arrives" reports without needing to escalate to support at all.