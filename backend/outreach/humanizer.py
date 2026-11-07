"""Automated humanizer check for outreach drafts.

Encodes the rules of the humanizer skill (based on Wikipedia's "Signs of AI
writing") plus a few cold-email spam signals. Findings are either:

- "block": a strong tell. With OUTREACH_HUMANIZER_STRICT on, the draft cannot
  be approved until it is rewritten.
- "warn": a weak tell. Shown for review, never blocks on its own.
"""
import re

URL_RE = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)


def _rx(*phrases):
    return re.compile(r'\b(?:' + '|'.join(phrases) + r')', re.IGNORECASE)


# (level, rule name, compiled pattern, advice)
RULES = [
    ('block', 'dash', re.compile(r'[—–]|\s--\s'),
     "Uses a dash (—, – or --). Use a comma, full stop or colon instead."),
    ('block', 'not-x-but-y',
     re.compile(r"\bnot (?:just|only|merely)\b[^.?!]{1,80}\bbut\b|\bit'?s not\b[^.?!]{1,60}[,;] it'?s\b"
                r"|\bisn'?t just\b", re.IGNORECASE),
     "Uses a \"not X but Y\" contrast. Say the point directly."),
    ('block', 'staged-opener',
     _rx(r"let'?s dive", r"let'?s explore", r"let'?s break (?:this|it) down", r"here'?s what you need to know",
         r"here'?s the thing", r"the thing is", r"let'?s be honest", r"real talk", r"without further ado",
         r"quick note", r"honestly\?"),
     "Announces the point instead of making it. Start with the point."),
    ('block', 'chatbot-residue',
     _rx(r"i hope this (?:email|message|note) finds you", r"i hope this helps", r"great question",
         r"certainly!", r"of course!", r"i'?d be (?:happy|delighted|thrilled) to", r"feel free to reach out",
         r"don'?t hesitate to (?:reach out|contact)", r"i trust this (?:email|message)",
         r"i wanted to reach out", r"i am reaching out", r"i'?m reaching out"),
     "Stock chatbot/template phrase. Cut it or say it plainly."),
    ('block', 'deep-saying',
     _rx(r"at its core", r"the real question is", r"what really matters", r"the heart of the matter",
         r"the deeper issue", r"in today'?s (?:digital|fast[- ]paced|competitive)"),
     "Dresses an ordinary point as a deep truth. State the specific claim."),
    ('block', 'arguing-with-no-one',
     _rx(r"to be clear", r"don'?t get me wrong", r"i'?m not saying", r"this is not to say"),
     "Answers an objection nobody raised. Remove it."),
    ('block', 'fake-urgency',
     _rx(r"act now", r"limited time", r"last chance", r"urgent", r"don'?t miss out", r"100% free",
         r"guaranteed", r"risk[- ]free", r"click here", r"once in a lifetime", r"special offer",
         r"\d+% (?:off|discount)"),
     "Spam-style urgency or offer wording. Gmail and readers treat this as spam."),
    ('block', 'emoji', re.compile('[\U0001F300-\U0001FAFF☀-➿⭐✅]'),
     "Contains an emoji. Keep first emails plain."),
    ('block', 'shouting', re.compile(r'!{2,}|\b[A-Z]{5,}\b'),
     "Uses ALL CAPS or repeated exclamation marks."),
    ('warn', 'ai-vocabulary',
     _rx(r"additionally", r"align(?:s|ed)? with", r"bolster(?:ed|s)?", r"crucial", r"deep dive", r"delve",
         r"enhanc(?:e|es|ed|ing)", r"foster(?:ing|s)?", r"garner", r"interplay", r"intricac(?:y|ies)",
         r"intricate", r"landscape", r"meticulous(?:ly)?", r"pivotal", r"robust", r"showcas(?:e|es|ing)",
         r"tapestry", r"testament", r"underscor(?:e|es|ing)", r"vibrant", r"seamless(?:ly)?", r"elevate",
         r"leverage", r"unlock", r"empower", r"game[- ]changer", r"cutting[- ]edge", r"synerg(?:y|ies)",
         r"streamline", r"transformative", r"holistic"),
     "Word that AI text overuses. Prefer a plainer word."),
    ('warn', 'sales-language',
     _rx(r"boasts?", r"nestled", r"in the heart of", r"renowned", r"breathtaking", r"stunning",
         r"diverse array", r"world[- ]class", r"state[- ]of[- ]the[- ]art", r"commitment to excellence",
         r"take (?:your|it) to the next level", r"stands? out from the crowd"),
     "Reads like an advert. Say what the thing is."),
    ('warn', 'inflated-significance',
     _rx(r"plays? a (?:key|vital|crucial|pivotal) role", r"pivotal moment", r"lasting legacy",
         r"setting the stage", r"evolving landscape", r"the future looks bright", r"exciting times"),
     "Inflates an ordinary detail. Keep the fact, drop the significance."),
    ('warn', 'avoiding-is', _rx(r"serves as", r"stands as", r"functions as"),
     "Use \"is\" or \"has\" instead."),
    ('warn', 'curly-quotes', re.compile('[“”‘’]'),
     "Curly quotes. Use straight quotes."),
]


def check(subject, body):
    """Return a list of findings: {'level', 'rule', 'message', 'example'}."""
    text = URL_RE.sub(' ', f"{subject or ''}\n{body or ''}")
    findings = []
    for level, rule, pattern, advice in RULES:
        match = pattern.search(text)
        if match:
            findings.append({
                'level': level,
                'rule': rule,
                'message': f'{advice} (found: "{match.group(0).strip()}")',
                'example': match.group(0).strip(),
            })
    if text.count('!') > 1 and not any(f['rule'] == 'shouting' for f in findings):
        findings.append({'level': 'warn', 'rule': 'exclamations', 'example': '!',
                         'message': "More than one exclamation mark. One-to-one business emails rarely need any."})
    return findings


def blocking(findings):
    return [f['message'] for f in findings if f['level'] == 'block']


def warnings(findings):
    return [f['message'] for f in findings if f['level'] == 'warn']
