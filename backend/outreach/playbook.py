"""The cold email playbook, as code.

Distilled from the Cold Email Hall of Fame (coldemails.world): the emails that got
answers from busy founders were short (about five sentences), sounded like one person
writing to another, opened with the reader instead of the sender, made one easy ask,
had a short curious subject line, and were followed up politely more than once.

The rest of outreach uses this module to:
- score() a draft from 0 to 100 and say what to fix (writer retries, review email, auto-send gate)
- priority() who gets emailed first when the queue is longer than today's limit
- daily_limit() warm a new mailbox up slowly instead of sending the full quota on day one
- followup_text() write the polite follow-ups that keep a thread alive
"""
import random
import re
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

URL_RE = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)
SENTENCE_RE = re.compile(r'[^.?!\n]+[.?!]+')
GREETING_RE = re.compile(r'^\s*(hi|hello|hey|dear|good (morning|afternoon))\b[^\n]*\n', re.IGNORECASE)
SIGN_OFF_RE = re.compile(r'\n\s*(regards|best|thanks|thank you|cheers|all the best|kind regards|warmly)\b.*$',
                         re.IGNORECASE | re.DOTALL)
SELF_OPENER_RE = re.compile(r"^\s*(my name is|i am|i'm|i )", re.IGNORECASE)
YOU_RE = re.compile(r"\b(you|your|you're|yours)\b", re.IGNORECASE)
ME_RE = re.compile(r"\b(i|me|my|i'm|i've|i'd|mine)\b", re.IGNORECASE)


def core_text(body):
    """The body without greeting, sign-off and links: the part the reader actually weighs."""
    text = GREETING_RE.sub('', (body or '').strip() + '\n', count=1)
    text = SIGN_OFF_RE.sub('', text)
    return URL_RE.sub(' ', text).strip()


def personal_hooks(facts):
    """Words that show an email was written for this business: its name, trade, or town."""
    hooks = []
    name = str(facts.get('name') or '').strip().lower()
    if len(name) > 2:
        hooks.append(name)
    category = str(facts.get('category') or '').strip().lower()
    if len(category) > 2:
        hooks.append(category[:-1] if category.endswith('s') else category)
    for part in str(facts.get('location') or '').lower().split(','):
        part = part.strip()
        if len(part) > 2 and not any(ch.isdigit() for ch in part):
            hooks.append(part)  # towns and areas, not street numbers or postcodes
    return hooks


def score(subject, body, facts=None):
    """Grade a draft against the playbook. Returns {'score': 0-100, 'notes': [what to fix]}."""
    facts = facts or {}
    notes, points = [], 100
    core = core_text(body)
    words = len((body or '').split())
    sentences = SENTENCE_RE.findall(core)

    if words > 120:
        points -= 20
        notes.append(f"{words} words. The emails that got answers were about five sentences; cut to under 110.")
    elif words < 30:
        points -= 15
        notes.append("Too thin to earn a reply. Say who you are and why them in a sentence each.")
    if len(sentences) > 8:
        points -= 20
        notes.append(f"{len(sentences)} sentences. Keep it to about five.")
    elif len(sentences) > 6:
        points -= 10
        notes.append(f"{len(sentences)} sentences. Five reads faster.")

    questions = core.count('?')
    if questions == 0:
        points -= 15
        notes.append("No clear ask. End with one easy question they can answer in a line.")
    elif questions > 2:
        points -= 10
        notes.append("Several questions. Keep one ask.")

    if sentences and SELF_OPENER_RE.match(sentences[0]):
        points -= 10
        notes.append("Opens with you. Open with them: their business, their customers, something you noticed.")
    you, me = len(YOU_RE.findall(core)), len(ME_RE.findall(core))
    if me > you * 1.5 + 1:
        points -= 10
        notes.append(f"Talks about you ({me}) more than them ({you}). Turn a few 'I' sentences around.")

    subject_words = (subject or '').split()
    if len(subject_words) > 8:
        points -= 10
        notes.append("Subject is long. Two to six words that make them curious.")
    if len(subject_words) >= 3 and all(w[:1].isupper() for w in subject_words if w[:1].isalpha()):
        points -= 5
        notes.append("Subject Is In Title Case, which reads like marketing. Write it like a person would.")

    hooks = personal_hooks(facts)
    if hooks and not any(h in f"{subject}\n{body}".lower() for h in hooks):
        points -= 15
        notes.append("Nothing in it is about this business. Mention their name, trade or town once.")

    if len(URL_RE.findall(body or '')) > 1:
        points -= 5
        notes.append("More than one link. One link on a first email looks less like a campaign.")

    return {'score': max(0, points), 'notes': notes}


def lead_facts(lead):
    """Name/trade/town for scoring, preferring fresh Google Maps facts."""
    if lead is None:
        return {}
    facts = {'category': lead.category, 'location': lead.location}
    research = found_research(lead)
    if research is not None:
        facts['name'] = research.data.get('name')
    return facts


def found_research(lead):
    """The lead's confirmed Google Maps match, or None."""
    from .models import LeadResearch

    if lead is None:
        return None
    return LeadResearch.objects.filter(lead=lead, status=LeadResearch.Status.OK).first()


def score_message(message):
    return score(message.subject, message.body, lead_facts(message.lead))


def priority(message):
    """Who goes first when there is more in the queue than today's limit allows.

    Follow-ups keep their place so a conversation's timing holds. After that, the best
    prospects for a web designer: businesses with no website, then well reviewed ones
    (they have customers and something to lose), then the best written emails.
    """
    points = 0
    if message.sequence_step:
        points += 100
    research = found_research(message.lead)
    if research is not None:
        data = research.data
        if not data.get('has_website'):
            points += 30
        rating, reviews = data.get('rating') or 0, data.get('reviews') or 0
        if rating >= 4:
            points += 10
        if reviews >= 20:
            points += 5
    domain = (message.to_email or '').rsplit('@', 1)[-1].lower()
    if domain in settings.OUTREACH_FREEMAIL_DOMAINS:
        points -= 10
    if not message.sequence_step:
        points += score_message(message)['score'] // 10
    return points


def daily_target(day):
    """A random but repeatable number of emails for this date, between OUTREACH_DAILY_MIN and OUTREACH_DAILY_LIMIT."""
    high = settings.OUTREACH_DAILY_LIMIT
    low = min(settings.OUTREACH_DAILY_MIN, high)
    return random.Random(f'{settings.SECRET_KEY}:{day.isoformat()}').randint(low, high)


def daily_limit(now=None):
    """Today's send cap: the day's random 10-20 target, lowered while a new mailbox is warming up."""
    today = timezone.localtime(now or timezone.now()).date()
    cap = daily_target(today)
    if not settings.OUTREACH_WARMUP_ENABLED:
        return cap
    from .models import OutreachMessage

    first = (OutreachMessage.objects.filter(status=OutreachMessage.Status.SENT, dry_run=False)
             .order_by('sent_at').values_list('sent_at', flat=True).first())
    if first is None:
        return min(cap, settings.OUTREACH_WARMUP_START)
    days = (today - timezone.localtime(first).date()).days
    return min(cap, settings.OUTREACH_WARMUP_START + settings.OUTREACH_WARMUP_STEP * max(days, 0))


# --- follow-ups ---------------------------------------------------------------------

def followup_days():
    """Days to wait after the previous email before each follow-up, e.g. [3, 4, 7]."""
    days = []
    for part in str(settings.OUTREACH_FOLLOWUP_DAYS).split(','):
        part = part.strip()
        if part.isdigit() and int(part) > 0:
            days.append(int(part))
    return days


def followup_due(previous, step, now=None):
    days = followup_days()
    if step > len(days) or previous.sent_at is None:
        return False
    return (now or timezone.now()) >= previous.sent_at + timedelta(days=days[step - 1])


BUMP = ("{greeting}\n\n"
        "Bumping this up in case it got buried. If you'd like, I can send over a quick website idea "
        "for {business}. It only takes a couple of minutes to read.\n\n"
        "Is that worth a look?\n\n"
        "Regards,\n{first}")
VALUE = ("{greeting}\n\n"
         "One more thought since my last note. Most customers check a business on their phone before they call "
         "or visit, so a quick, clear page does a lot of quiet work. I'd be glad to sketch what that could look "
         "like for {business}, no strings attached.\n\n"
         "Would that help?\n\n"
         "Regards,\n{first}")
BREAKUP = ("{greeting}\n\n"
           "I'll leave it here so I don't fill up your inbox. If a new website ever comes up for {business}, "
           "{portfolio_line}just reply to this email any time.\n\n"
           "All the best,\n{first}")


def followup_text(root, step):
    """Subject and body for follow-up number `step` (1-based) in root's thread."""
    total = len(followup_days())
    template = BREAKUP if step >= total else (BUMP if step % 2 else VALUE)
    first_line = (root.body or '').strip().splitlines()[0] if (root.body or '').strip() else ''
    greeting = first_line if GREETING_RE.match(first_line + '\n') else 'Hi,'
    business = 'your business'
    facts = lead_facts(root.lead)
    if facts.get('name'):
        business = facts['name']
    portfolio = settings.OUTREACH_PORTFOLIO_URL
    body = template.format(
        greeting=greeting, business=business,
        first=(settings.OUTREACH_FROM_NAME or 'Zubair').split()[0],
        portfolio_line=f"you can see my work at {portfolio} and " if portfolio else '',
    )
    subject = root.subject if root.subject.lower().startswith('re:') else f"Re: {root.subject}"
    return subject[:200], body
