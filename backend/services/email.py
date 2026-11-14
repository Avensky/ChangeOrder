"""Send the GC's approval link by email, with the console link as the fallback.

Email is best effort. A provider outage must never block a change from being
reviewed or decided, so nothing here raises into a request: send() reports
whether the message was accepted and the caller prints the link either way.

No dependency is added. The provider is called over HTTPS with the standard
library, so this works before Bona picks the final service.
"""

import json
import urllib.error
import urllib.request

from core.config import email_settings

TIMEOUT_SECONDS = 10


def send(to: str, subject: str, body: str) -> bool:
    """Hand one message to the provider. True only if it accepted the message.

    Returns False, without raising, when email is not configured. That is the
    normal local state: the console link is then the only delivery.
    """
    settings = email_settings()
    if not settings["api_key"] or not to:
        return False

    request = urllib.request.Request(
        settings["api_url"],
        data=json.dumps(
            {
                "from": settings["sender"],
                "to": [to],
                "subject": subject,
                "text": body,
            }
        ).encode(),
        headers={
            "Authorization": f"Bearer {settings['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        # Report the failure without echoing the request, which carries the key.
        print(f"EMAIL FAILED: {type(error).__name__}. The console link still works.")
        return False


def money(cents: int | None, currency: str = "USD") -> str:
    """Format integer cents for a person to read. Never does math on floats."""
    if cents is None:
        return "not estimated yet"
    return f"{currency} {cents // 100:,}.{cents % 100:02d}"


def approval_request(change: dict, link: str) -> tuple[str, str]:
    """The templated email that carries the GC's review link."""
    subject = f"Approval needed: {change['code']} {change['title']}"
    body = f"""A change order needs your approval.

Change:   {change['code']} - {change['title']}
Project:  {change['project_id']}
Scope:    {change.get('approved_scope') or change['description']}
Cost:     {money(change.get('proposed_cost_cents'), change.get('currency', 'USD'))}
Timeline: {change.get('requested_timeline_days')} extra day(s)

Review and decide here:
{link}

Opening this link does not approve anything. Nothing is decided until you
press Approve or Decline on that page.
"""
    return subject, body


def fast_track_notice(change: dict) -> tuple[str, str]:
    """Heads-up that work was authorized before the cost is known.

    Deliberately carries no approval link. The spec binds a link to one
    proposal revision, and no revision exists yet; issuing one here would be
    superseded by the estimator's and leave two live tokens. The GC gets the
    real link once the cost is added. Wording is marked "to be agreed" in the
    spec, so treat this copy as a draft.
    """
    subject = f"Work started on urgent change {change['code']}"
    body = f"""An urgent change was authorized to start before it was priced.

Change:  {change['code']} - {change['title']}
Project: {change['project_id']}
Scope:   {change['description']}

The cost is not known yet. You will receive a separate email with a link to
approve or decline once the estimator has added it. No approval is being
requested now, and nothing has been approved on your behalf.
"""
    return subject, body
