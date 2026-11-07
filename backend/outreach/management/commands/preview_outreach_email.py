from pathlib import Path

from django.core.management.base import BaseCommand

from outreach import branding, playbook

SAMPLE_SUBJECT = "bright smile dental online"
SAMPLE_BODY = """Hi Bright Smile Dental team,

Your 4.8 stars from 120 reviews in Leeds say patients love you, but Google shows no website for the clinic yet.

I'm Zubair, a developer who builds fast, simple sites for local practices. A one page site with your hours, reviews and a booking button would let new patients find you before they call.

Would you like me to send over a quick mock up?

Regards,
Zubair"""


SIGNATURE_PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>ZH. email signature</title></head>
<body style="margin:0;padding:32px 18px;background:#ffffff;font-family:Helvetica,Arial,sans-serif;color:#555;">
<p style="font-size:13px;margin:0 0 6px;">Hostinger webmail signature: select everything inside the dashed box
(click just before the card and drag past it, or click inside and press Ctrl+A), copy, then paste into
Settings &rarr; Identities / Signatures and save.</p>
<p style="font-size:13px;margin:0 0 18px;">Regards,<br>Zubair</p>
<div style="border:1px dashed #ccc;padding:14px;display:inline-block;">
{card}
</div>
</body></html>
"""


class Command(BaseCommand):
    help = "Write the branded outreach email (sample or your own text) to an HTML file you can open in a browser."

    def add_arguments(self, parser):
        parser.add_argument('--out', default='outreach_email_preview.html')
        parser.add_argument('--subject', default=SAMPLE_SUBJECT)
        parser.add_argument('--body-file', default='', help="Plain-text file with the body to preview")
        parser.add_argument('--signature-only', action='store_true',
                            help="Write only the ZH. signature card, for Hostinger webmail")

    def handle(self, *args, **options):
        if options['signature_only']:
            out = Path(options['out'])
            out.write_text(SIGNATURE_PAGE.format(card=branding.signature_html()), encoding='utf-8')
            self.stdout.write(f"Wrote {out.resolve()}")
            return
        body = Path(options['body_file']).read_text(encoding='utf-8') if options['body_file'] else SAMPLE_BODY
        subject = options['subject']
        out = Path(options['out'])
        out.write_text(branding.html_version(subject, body), encoding='utf-8')
        graded = playbook.score(subject, body, {'name': 'Bright Smile Dental', 'location': 'Leeds'})
        self.stdout.write(f"Wrote {out.resolve()}")
        self.stdout.write(f"Playbook score: {graded['score']}/100")
        for note in graded['notes']:
            self.stdout.write(f"  - {note}")
