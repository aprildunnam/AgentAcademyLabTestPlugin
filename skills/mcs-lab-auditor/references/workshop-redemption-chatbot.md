# Workshop-code → test-account redemption (chatbot portal)

This document describes the Copilot Studio chatbot redemption flow used by the MCS Workshop Agent (`https://aka.ms/MCSWorkshopAgent/`).

## Inputs

- `config/workshop.yml.workshop_portal_url` — chatbot URL.
- The workshop code, prompted from the user via the chat (never logged or echoed back beyond the first 4 chars).

## Flow (Adaptive Cards 1→6)

### 1. Open chatbot page (Card 1)

```
_browser_navigate(url: <workshop_portal_url>)
_browser_wait_for(text: "Workshop Pass Code")
_browser_snapshot()
```

Find the card input labeled `Workshop Pass Code`, type the code, then click `Submit`.

### 2. Request account (Card 2)

Wait for card text `Agent Training Assistant`, then click quick reply `Get a User Account`.

```
_browser_wait_for(text: "Agent Training Assistant")
_browser_click(ref: <get-user-account-button-ref>)
```

### 3. Consent (Card 3)

Wait for the terms card (contains `I confirm`). Check `I confirm`, then click `Consent and create account`.

If the user selects `I don't consent`, abort with `reason: consent_declined`.

### 4. Complete profile form (Card 4)

Wait for `Training-user-account-request`.

Fill all required fields:
- Organization type
- Industry
- Company size
- Country/Region
- Job title

Then submit the card action that creates the account.

### 5. Scrape credentials (Card 5)

Wait for success card text that includes `Full name`, `Username`, and `Password`, then scrape values with `_browser_evaluate`.

If `Username` or `Password` is missing, abort with `reason: credentials_not_scraped`.

### 6. Ignore feedback card (Card 6)

If `Rate your answer` appears, do not block on it; credentials were already issued on Card 5.

## Continue with standard cache/sign-in flow

After scraping username/password, continue with `workshop-redemption.md` §5+ behavior:
- sign in to `https://login.microsoftonline.com/`
- capture `runtime/account/storage-state.json`
- DPAPI-encrypt `runtime/account/credential.enc`
- write `runtime/account/account.meta.json`
