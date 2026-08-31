import os
import re
import logging
import requests
import json
import dns.resolver
from email_validator import validate_email, EmailNotValidError
from django.db import IntegrityError
from urllib.parse import unquote, urljoin, urlparse
from .models import Lead

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}\b')

class EmailVerifier:
    """Handles email validation and verification"""

    INVALID_DOMAINS = {
        'noemail.com', 'noemail.local', 'example.com', 'example.org',
        'example.net', 'test.com', 'localhost', 'invalid'
    }
    INVALID_EMAIL_PATTERNS = [
        r'noreply', r'no-reply', r'do-not-reply', r'support@twitter',
        r'privacy@', r'abuse@', r'postmaster@'
    ]

    @staticmethod
    def normalize_email(email):
        if not email or not isinstance(email, str):
            return ""

        email = unquote(email.strip().strip('.,;:()[]{}<>"\''))
        if email.lower().startswith('mailto:'):
            email = email[7:]
        email = email.split('?')[0].split('#')[0].strip().lower()
        return email

    @staticmethod
    def is_valid_syntax(email):
        """Basic syntax validation"""
        email = EmailVerifier.normalize_email(email)
        if not email or email == "n/a" or '@' not in email:
            return False

        domain = email.split('@')[-1].lower()
        if domain in EmailVerifier.INVALID_DOMAINS:
            return False

        for pattern in EmailVerifier.INVALID_EMAIL_PATTERNS:
            if re.search(pattern, email, re.IGNORECASE):
                return False

        try:
            validate_email(email, check_deliverability=False)
            return True
        except EmailNotValidError:
            return False

    @staticmethod
    def verify_domain(email):
        """Check if domain has valid MX records"""
        try:
            email = EmailVerifier.normalize_email(email)
            domain = email.split('@')[1]
            resolver = dns.resolver.Resolver()
            resolver.timeout = 2
            resolver.lifetime = 4
            mx_records = resolver.resolve(domain, 'MX')
            return len(mx_records) > 0
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, Exception):
            return False

    @staticmethod
    def is_valid_email(email):
        """Complete email validation"""
        return EmailVerifier.is_valid_syntax(email) and EmailVerifier.verify_domain(email)


class DeliverabilityPolicyChecker:
    """Checks sender-side DNS/authentication signals that affect inbox placement."""

    COMMON_DKIM_SELECTORS = (
        "google", "selector1", "selector2", "default", "dkim", "mail",
        "k1", "s1", "s2", "20230601", "20210112", "20161025",
    )
    PERSONAL_MAILBOX_DOMAINS = {
        "gmail.com", "googlemail.com", "yahoo.com", "ymail.com",
        "outlook.com", "hotmail.com", "live.com", "icloud.com", "aol.com",
    }
    RISKY_PHRASES = (
        "free money", "guaranteed", "act now", "limited time", "winner",
        "risk free", "no obligation", "click here", "urgent", "cash bonus",
        "100% free", "buy now", "lowest price", "make money fast",
    )

    @staticmethod
    def _txt_records(name):
        resolver = dns.resolver.Resolver()
        resolver.timeout = 2
        resolver.lifetime = 4
        try:
            answers = resolver.resolve(name, "TXT")
            return [
                b"".join(answer.strings).decode("utf-8", errors="ignore")
                for answer in answers
            ]
        except Exception:
            return []

    @staticmethod
    def _mx_records(domain):
        resolver = dns.resolver.Resolver()
        resolver.timeout = 2
        resolver.lifetime = 4
        try:
            answers = resolver.resolve(domain, "MX")
            return [str(answer.exchange).rstrip(".") for answer in answers]
        except Exception:
            return []

    @staticmethod
    def _domain_from_email(email):
        normalized = EmailVerifier.normalize_email(email)
        if not EmailVerifier.is_valid_syntax(normalized):
            return "", normalized
        return normalized.split("@", 1)[1], normalized

    @staticmethod
    def _find_record(records, prefix):
        prefix = prefix.lower()
        return next((record for record in records if record.lower().startswith(prefix)), "")

    @classmethod
    def _check_dkim(cls, domain, selectors=None):
        selectors_to_check = list(dict.fromkeys(list(selectors or []) + list(cls.COMMON_DKIM_SELECTORS)))
        found = []
        checked = []

        for selector in selectors_to_check[:20]:
            selector = str(selector).strip()
            if not selector:
                continue
            lookup_name = f"{selector}._domainkey.{domain}"
            checked.append(selector)
            record = cls._find_record(cls._txt_records(lookup_name), "v=DKIM1")
            if record or any("p=" in txt.lower() for txt in cls._txt_records(lookup_name)):
                found.append(selector)

        return found, checked

    @classmethod
    def _content_checks(cls, subject="", body="", include_unsubscribe=None):
        text = f"{subject or ''} {body or ''}".lower()
        risky_hits = [phrase for phrase in cls.RISKY_PHRASES if phrase in text]
        has_unsubscribe = (
            include_unsubscribe
            if include_unsubscribe is not None
            else "unsubscribe" in text or "list-unsubscribe" in text
        )
        has_plain_body = len((body or "").strip()) >= 80

        return {
            "risky_phrases": risky_hits,
            "has_unsubscribe": bool(has_unsubscribe),
            "has_plain_body": has_plain_body,
        }

    @classmethod
    def check(cls, sender_email, subject="", body="", daily_volume=None,
              include_unsubscribe=None, dkim_selectors=None, smtp_host=None,
              smtp_tls=True):
        domain, normalized_email = cls._domain_from_email(sender_email)
        checks = []
        recommendations = []
        score = 100

        def add_check(key, label, passed, severity, detail, fix="", penalty=0):
            nonlocal score
            if not passed:
                score -= penalty
                if fix:
                    recommendations.append(fix)
            checks.append({
                "key": key,
                "label": label,
                "passed": bool(passed),
                "severity": severity,
                "detail": detail,
                "fix": fix,
            })

        if not domain:
            return {
                "sender_email": sender_email,
                "domain": "",
                "score": 0,
                "status": "invalid_sender",
                "inbox_prediction": "Cannot check delivery risk because the sender email is invalid.",
                "checks": [{
                    "key": "sender",
                    "label": "Sender address",
                    "passed": False,
                    "severity": "critical",
                    "detail": "Enter a real sender email address.",
                    "fix": "Use an authenticated business sender address.",
                }],
                "recommendations": ["Use a valid authenticated sender address."],
            }

        is_personal_domain = domain in cls.PERSONAL_MAILBOX_DOMAINS
        txt_records = cls._txt_records(domain)
        dmarc_records = cls._txt_records(f"_dmarc.{domain}")
        mx_records = cls._mx_records(domain)
        spf_record = cls._find_record(txt_records, "v=spf1")
        dmarc_record = cls._find_record(dmarc_records, "v=DMARC1")
        dkim_found, dkim_checked = cls._check_dkim(domain, dkim_selectors or [])
        content = cls._content_checks(subject, body, include_unsubscribe)
        try:
            normalized_volume = int(daily_volume or 0)
        except (TypeError, ValueError):
            normalized_volume = 0
        bulk_sender = normalized_volume >= 5000

        add_check(
            "mx",
            "Domain can receive mail",
            bool(mx_records),
            "critical",
            f"MX records found: {', '.join(mx_records[:3])}" if mx_records else "No MX records were found.",
            "Add valid MX records for the sending domain.",
            15,
        )
        add_check(
            "spf",
            "SPF record",
            bool(spf_record),
            "critical",
            f"Found SPF: {spf_record}" if spf_record else "No SPF TXT record was found at the root domain.",
            "Publish SPF for every service that sends mail for this domain.",
            25,
        )
        add_check(
            "dmarc",
            "DMARC record",
            bool(dmarc_record),
            "critical" if bulk_sender else "warning",
            f"Found DMARC: {dmarc_record}" if dmarc_record else "No DMARC TXT record was found.",
            "Publish a DMARC record at _dmarc with at least p=none while testing.",
            25 if bulk_sender else 18,
        )
        add_check(
            "dkim",
            "Probable DKIM record",
            bool(dkim_found) or is_personal_domain,
            "critical" if bulk_sender else "warning",
            f"DKIM selector(s) found: {', '.join(dkim_found)}" if dkim_found else (
                "Personal mailbox domain; DKIM is normally handled by the mailbox provider."
                if is_personal_domain else
                f"No DKIM record found using common selectors: {', '.join(dkim_checked[:8])}."
            ),
            "Enable DKIM signing in your mail provider and pass its selector in this checker.",
            20 if bulk_sender else 12,
        )
        add_check(
            "smtp_tls",
            "SMTP TLS",
            bool(smtp_tls),
            "warning",
            "TLS is enabled for the configured SMTP sender." if smtp_tls else "TLS is not enabled for SMTP.",
            "Enable TLS or SSL for SMTP sending.",
            10,
        )

        if smtp_host and "gmail" in smtp_host.lower() and not (
            domain in ("gmail.com", "googlemail.com") or "_spf.google.com" in spf_record
        ):
            add_check(
                "provider_alignment",
                "Gmail SPF alignment",
                False,
                "warning",
                "SMTP host is Gmail, but SPF does not include Google's SPF mechanism.",
                "Add include:_spf.google.com to the domain SPF record if Google sends for this domain.",
                12,
            )
        else:
            add_check(
                "provider_alignment",
                "Provider alignment",
                True,
                "info",
                "Sender domain and configured SMTP host do not show an obvious SPF mismatch.",
            )

        add_check(
            "mailbox_type",
            "Business sender domain",
            not is_personal_domain,
            "warning",
            "This is a custom/business domain." if not is_personal_domain else
            "This is a personal mailbox domain. Cold or bulk outreach from personal Gmail/Yahoo/Outlook accounts is more likely to be throttled or filtered.",
            "Use a warmed custom domain or a reputable email service provider for outreach.",
            12,
        )
        add_check(
            "unsubscribe",
            "Unsubscribe path",
            content["has_unsubscribe"] or not bulk_sender,
            "critical" if bulk_sender else "warning",
            "Unsubscribe language/header is present." if content["has_unsubscribe"] else
            "No unsubscribe signal was detected in the sample content.",
            "Add a visible unsubscribe link and List-Unsubscribe headers for campaigns.",
            12 if bulk_sender else 4,
        )
        add_check(
            "content_body",
            "Message body depth",
            content["has_plain_body"] or not body,
            "warning",
            "Body has enough plain text for a basic content review." if content["has_plain_body"] else
            "The sample body is very short; thin messages can look automated.",
            "Use a normal, personalized plain-text style body with real context.",
            5,
        )
        add_check(
            "risky_copy",
            "Spam-trigger phrasing",
            not content["risky_phrases"],
            "warning",
            f"Risky phrases found: {', '.join(content['risky_phrases'])}" if content["risky_phrases"] else
            "No obvious spam-trigger phrases found in the sample content.",
            "Remove hype, urgency, guarantees, and salesy claims from the first message.",
            min(18, len(content["risky_phrases"]) * 6),
        )

        score = max(0, min(100, score))
        if score >= 85:
            status = "inbox_ready"
            prediction = "Low policy risk. Inbox placement still depends on reputation, warm-up, complaints, and recipient engagement."
        elif score >= 65:
            status = "needs_work"
            prediction = "Medium spam-folder risk. Fix the failed policy checks before sending real campaigns."
        else:
            status = "high_spam_risk"
            prediction = "High spam-folder risk. Authentication or campaign policy signals are missing."

        return {
            "sender_email": normalized_email,
            "domain": domain,
            "score": score,
            "status": status,
            "inbox_prediction": prediction,
            "bulk_sender": bulk_sender,
            "authentication": {
                "spf": spf_record,
                "dmarc": dmarc_record,
                "dkim_selectors_found": dkim_found,
                "mx_records": mx_records,
            },
            "content": content,
            "checks": checks,
            "recommendations": list(dict.fromkeys(recommendations)),
        }


class LeadGenerator:
    """Handles lead generation from various sources"""

    CONTACT_LINK_HINTS = ('contact', 'about', 'team', 'staff', 'support')
    REQUEST_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    def __init__(self):
        self.serpapi_key = os.getenv('SERPAPI_KEY')
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.google_cx = os.getenv('GOOGLE_CX')
        self.apify_key = os.getenv('APIFY_API_KEY')
        self.gemini_key = os.getenv('GEMINI_API_KEY')

    def _extract_emails_from_text(self, text):
        """Return syntax-valid, deduplicated emails from text/html."""
        if not text:
            return []

        emails = []
        seen = set()
        for raw_email in EMAIL_REGEX.findall(text):
            email = EmailVerifier.normalize_email(raw_email)
            if email in seen or not EmailVerifier.is_valid_syntax(email):
                continue
            seen.add(email)
            emails.append(email)
        return emails

    def _first_active_email(self, emails):
        """Pick the first email with valid syntax and an active MX domain."""
        for email in emails:
            if EmailVerifier.is_valid_email(email):
                return EmailVerifier.normalize_email(email)
        return ""

    def _normalize_url(self, url):
        if not url:
            return ""

        url = str(url).strip()
        if not url:
            return ""
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        return url

    def _fetch_page(self, url):
        try:
            response = requests.get(
                url,
                headers=self.REQUEST_HEADERS,
                timeout=8,
                allow_redirects=True,
            )
            content_type = response.headers.get('content-type', '').lower()
            if response.status_code >= 400 or 'text/html' not in content_type:
                return ""
            return response.text[:300000]
        except requests.RequestException as e:
            logger.debug(f"Could not fetch {url}: {e}")
            return ""

    def _extract_active_email_from_website(self, website):
        """Crawl a business website and nearby contact pages for an active email."""
        start_url = self._normalize_url(website)
        if not start_url:
            return ""

        parsed_start = urlparse(start_url)
        if not parsed_start.netloc:
            return ""

        urls_to_check = [start_url]
        checked = set()

        while urls_to_check and len(checked) < 4:
            url = urls_to_check.pop(0)
            if url in checked:
                continue
            checked.add(url)

            html = self._fetch_page(url)
            active_email = self._first_active_email(self._extract_emails_from_text(html))
            if active_email:
                return active_email

            if len(checked) > 1:
                continue

            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    link_text = f"{href} {link.get_text(' ', strip=True)}".lower()
                    if not any(hint in link_text for hint in self.CONTACT_LINK_HINTS):
                        continue

                    next_url = urljoin(url, href)
                    parsed_next = urlparse(next_url)
                    if parsed_next.netloc and parsed_next.netloc != parsed_start.netloc:
                        continue
                    if next_url not in checked and next_url not in urls_to_check:
                        urls_to_check.append(next_url)
                    if len(urls_to_check) >= 3:
                        break
            except Exception as e:
                logger.debug(f"Could not parse links from {url}: {e}")

        return ""

    def search_google_maps(self, category, location):
        """Search Google Maps via SerpAPI and enrich websites with active emails."""
        if not self.serpapi_key:
            logger.warning("SERPAPI_KEY is not configured; Google Maps search skipped")
            return []

        try:
            import serpapi
            client = serpapi.Client(api_key=self.serpapi_key)
            params = {
                "engine": "google_maps",
                "q": f"{category} in {location}",
                "type": "search",
                "limit": 20
            }
            results = client.search(params)
            local_results = results.get("local_results", [])

            leads = []
            for res in local_results[:20]:
                website = res.get("website", "")
                phone = res.get("phone", "")
                if not website:
                    continue

                email = self._extract_active_email_from_website(website)
                if not email:
                    logger.debug(f"Skipping map result without active email: {res.get('title', website)}")
                    continue

                leads.append({
                    "email": email,
                    "phone": phone,
                    "source": "google-maps",
                    "category": category,
                    "location": res.get("address", location),
                    "link": website,
                    "problem_statement": f"Local business: {res.get('title', '')}. May need services."
                })
            return leads
        except Exception as e:
            logger.error(f"Google Maps search error: {e}")
            return []

    def search_google_custom_search(self, category, niche, location, platform=None):
        """Search Google Custom Search API"""
        if not self.google_api_key or not self.google_cx:
            return []

        query = f'{category} {niche or ""} {location or ""} "contact" (email OR phone) -agency -firm -software -consultancy -services'
        if platform:
            if platform.lower() in ('x', 'twitter'):
                query += ' site:twitter.com OR site:x.com'
            elif platform.lower() != 'google-maps':
                query += f' site:{platform}.com'

        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx": self.google_cx,
            "q": query,
            "num": 10
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            leads = []

            if "items" in data:
                for item in data["items"]:
                    snippet = item.get("snippet", "")
                    email = self._first_active_email(self._extract_emails_from_text(snippet))
                    if not email:
                        email = self._extract_active_email_from_website(item.get("link", ""))
                    if email:
                        leads.append({
                            "email": email,
                            "phone": "",
                            "source": "google-cse",
                            "category": category,
                            "location": location or "Unknown",
                            "link": item.get("link", ""),
                            "problem_statement": snippet
                        })
            return leads
        except Exception as e:
            logger.error(f"Google CSE error: {e}")
            return []

    def search_apify(self, category, location):
        """Search using Apify Google Places scraper with SerpAPI fallback.
        
        This is the PROFESSIONAL/ENTERPRISE data source.
        Only called when is_professional=True.
        Falls back to SerpAPI Google Maps if Apify fails or is unavailable.
        """
        if not self.apify_key or self.apify_key == "your_apify_api_key_here":
            logger.info("Apify API key not configured, falling back to SerpAPI Google Maps")
            return self.search_google_maps(category, location)

        try:
            from apify_client import ApifyClient
            client = ApifyClient(self.apify_key)
            run_input = {
                "searchStringsArray": [f"{category} in {location}"],
                "maxCrawledPlaces": 10,
            }

            logger.info(f"[Apify] Starting crawler for '{category}' in '{location}'")

            # Run the actor with a 3-minute timeout to avoid hanging
            run = client.actor("compass/crawler-google-places").call(
                run_input=run_input,
                timeout_secs=180,
            )

            run_status = run.get("status", "UNKNOWN")
            logger.info(f"[Apify] Run finished with status: {run_status}")

            if run_status not in ("SUCCEEDED", "RUNNING"):
                logger.warning(f"[Apify] Unexpected run status '{run_status}', falling back to SerpAPI")
                return self.search_google_maps(category, location)

            leads = []
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                logger.warning("[Apify] No dataset ID returned, falling back to SerpAPI")
                return self.search_google_maps(category, location)

            for item in client.dataset(dataset_id).iterate_items():
                email = item.get("email") or item.get("emails", [None])
                if isinstance(email, list):
                    email = email[0] if email else None

                phone = item.get("phone") or ""
                if isinstance(phone, list):
                    phone = phone[0] if phone else ""

                website = item.get("website") or item.get("url") or item.get("placeUrl", "")
                email = self._first_active_email([email]) if email else ""
                if not email:
                    email = self._extract_active_email_from_website(website)
                if not email:
                    logger.debug(f"[Apify] Skipping result without active email: {item.get('title', website)}")
                    continue

                leads.append({
                    "email": email,
                    "phone": phone,
                    "source": "apify-maps",
                    "category": category,
                    "location": item.get("address") or item.get("city") or location,
                    "link": website,
                    "problem_statement": f"Business: {item.get('title', 'Unknown')}. Rating: {item.get('totalScore', 'N/A')}."
                })

            logger.info(f"[Apify] Extracted {len(leads)} leads from dataset")
            if not leads:
                logger.info("[Apify] No leads found, falling back to SerpAPI")
                return self.search_google_maps(category, location)

            return leads

        except Exception as e:
            logger.warning(f"[Apify] Error: {e}. Falling back to SerpAPI Google Maps.")
            return self.search_google_maps(category, location)

    def filter_leads_with_ai(self, leads_batch, category, niche=None, target_location=None):
        """Use Gemini AI to filter leads"""
        if not self.gemini_key or not leads_batch:
            return leads_batch

        try:
            from google import genai
            client = genai.Client(api_key=self.gemini_key)

            content_to_analyze = "\n---\n".join([
                f"ID: {i} | Source: {l['source']} | Content: {l['problem_statement']}"
                for i, l in enumerate(leads_batch)
            ])

            location_info = f" in {target_location}" if target_location else ""
            niche_info = f" in {niche}" if niche else ""

            prompt = f"""
            You are an expert B2B Lead Generation AI.
            Analyze these extracted leads for the category: "{category}"{niche_info}{location_info}.
            
            Your job is to strictly filter out spam, low-quality data, and irrelevant businesses.
            Return ONLY the indices (numbers) of leads that appear to be HIGH-QUALITY, GENUINE potential CLIENTS who might need {category} services.
            
            CRITICAL EXCLUSION CRITERIA:
            - EXCLUDE any agencies, freelancers, or competitors offering the same or similar services.
            - EXCLUDE directory listings, review sites (like Yelp, YellowPages), or aggregator profiles.
            - EXCLUDE generic spam accounts, bots, or extremely low-information snippets.
            - EXCLUDE any lead that does not clearly belong to a real business or professional in need of the target service.

            Leads:
            {content_to_analyze}

            Return a valid JSON array of indices ONLY (e.g., [0, 2, 5]). Do not include markdown formatting or extra text.
            """

            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )

            raw_text = response.text.strip()
            if '```' in raw_text:
                raw_text = re.search(r'\[.*\]', raw_text, re.DOTALL).group()

            valid_indices = json.loads(raw_text)
            return [leads_batch[i] for i in valid_indices if i < len(leads_batch)]

        except Exception as e:
            logger.error(f"AI filtering error: {e}")
            return leads_batch

    def generate_leads(self, category, platforms, niche=None, target_location=None, is_professional=False):
        """Main lead generation method.
        
        API Priority:
        1. SerpAPI (Primary)
        2. Google CSE (Secondary)
        3. Apify (Third, only for maps if professional mode is enabled)
        4. Gemini AI (Fourth/Last, for lead validation)
        """
        leads_to_save = []

        logger.info(
            f"[LeadGen] Starting: category={category}, platforms={platforms}, "
            f"location={target_location}, professional={is_professional}"
        )

        # Iterate through requested platforms
        for platform in platforms:
            if platform in ('google-maps', 'apify', 'google-cse'):
                continue
                
            # 1) Primary Priority: SerpAPI
            logger.info(f"[LeadGen] Primary: SerpAPI for {platform}")
            results = self._search_platform(category, platform, niche, target_location)
            logger.info(f"[LeadGen] SerpAPI {platform} → {len(results)} leads")
            leads_to_save.extend(results)

            # 2) Secondary Priority: Google CSE
            logger.info(f"[LeadGen] Secondary: Google CSE for {platform}")
            cse_results = self.search_google_custom_search(category, niche, target_location, platform)
            logger.info(f"[LeadGen] Google CSE {platform} → {len(cse_results)} leads")
            leads_to_save.extend(cse_results)

        # Independent Google CSE if explicitly requested
        if 'google-cse' in platforms:
            logger.info(f"[LeadGen] Secondary: Independent Google CSE")
            results = self.search_google_custom_search(category, niche, target_location)
            logger.info(f"[LeadGen] google-cse → {len(results)} leads")
            leads_to_save.extend(results)

        # Google Maps with PRIORITY ROUTING
        if 'google-maps' in platforms and target_location:
            if is_professional:
                # 3) Third Priority: Apify (ONLY for maps AND if is_professional)
                logger.info("[LeadGen] Google Maps → APIFY (Third priority, Professional mode)")
                results = self.search_apify(category, target_location)
            else:
                # 1) Primary Priority fallback for Maps: SerpAPI
                logger.info("[LeadGen] Google Maps → SERPAPI (Primary priority, Standard mode)")
                results = self.search_google_maps(category, target_location)
            logger.info(f"[LeadGen] google-maps → {len(results)} leads")
            leads_to_save.extend(results)

        logger.info(f"[LeadGen] Total raw leads before dedup/save/AI: {len(leads_to_save)}")
        
        # 4) Last Priority: Gemini AI Validation
        if leads_to_save:
            logger.info("[LeadGen] Last: Running Gemini AI validation on leads...")
            leads_to_save = self.filter_leads_with_ai(leads_to_save, category, niche, target_location)
            logger.info(f"[LeadGen] Total leads after AI filter: {len(leads_to_save)}")

        return self._save_leads(leads_to_save, category)

    def _search_platform(self, category, platform, niche, location):
        """Platform-specific search using SerpAPI"""
        if not self.serpapi_key:
            return []

        try:
            import serpapi
            client = serpapi.Client(api_key=self.serpapi_key)
            leads = []

            if platform.lower() in ['reddit', 'x', 'twitter']:
                site_query = "site:twitter.com OR site:x.com" if platform.lower() in ['x', 'twitter'] else "site:reddit.com"
                query = f'({category} {niche or ""}) (email OR phone OR contact) {site_query}'
                params = {
                    "q": query,
                    "num": 50,
                    "tbs": "qdr:m"
                }
                results = client.search(params)
                
                for res in results.get("organic_results", []):
                    snippet = res.get("snippet", "")
                    content = (res.get("title", "") + " " + snippet).lower()
                    
                    email = self._first_active_email(self._extract_emails_from_text(content))
                    if not email:
                        email = self._extract_active_email_from_website(res.get("link", ""))
                    if not email:
                        continue
                    
                    leads.append({
                        "email": email,
                        "phone": "",
                        "source": platform,
                        "category": category,
                        "location": location or "Remote",
                        "link": res.get("link", ""),
                        "problem_statement": snippet[:200]
                    })
            
            else:
                # Generic Google search for other platforms
                negatives = "-agency -firm -software -solutions -consultancy -services"
                query = f'({category} {niche or ""}) (email OR phone) site:{platform}.com {negatives}'
                params = {
                    "q": query,
                    "num": 50,
                    "tbs": "qdr:m"
                }
                results = client.search(params)
                
                for res in results.get("organic_results", []):
                    snippet = res.get("snippet", "")
                    content = (res.get("title", "") + " " + snippet).lower()
                    
                    email = self._first_active_email(self._extract_emails_from_text(content))
                    if not email:
                        email = self._extract_active_email_from_website(res.get("link", ""))
                    if not email:
                        continue
                    
                    leads.append({
                        "email": email,
                        "phone": "",
                        "source": platform,
                        "category": category,
                        "location": location or "Remote",
                        "link": res.get("link", ""),
                        "problem_statement": snippet[:200]
                    })

            logger.info(f"Found {len(leads)} leads from {platform}")
            return leads
        except Exception as e:
            logger.error(f"Platform search error for {platform}: {e}")
            return []

    def _save_leads(self, leads, category):
        """Save only leads that have a real, deliverable email address."""
        saved_leads = []

        for lead in leads:
            email = EmailVerifier.normalize_email(lead.get('email', ''))
            if not EmailVerifier.is_valid_email(email):
                logger.debug(f"Skipping lead without active email: {lead}")
                continue

            if Lead.objects.filter(email=email).exists():
                logger.debug(f"Lead with email {email} already exists. Skipping.")
                continue

            try:
                lead_obj = Lead.objects.create(
                    email=email,
                    phone=lead.get('phone', ''),
                    source=lead['source'],
                    category=category,
                    service=category,
                    location=lead['location'],
                    link=lead['link'],
                    problem_statement=lead['problem_statement'],
                    is_verified=True,
                )
                saved_leads.append({
                    "id": lead_obj.id,
                    "email": lead_obj.email,
                    "phone": lead_obj.phone,
                    "source": lead_obj.source,
                    "category": lead_obj.category,
                    "service": lead_obj.service,
                    "location": lead_obj.location,
                    "link": lead_obj.link,
                    "problem_statement": lead_obj.problem_statement,
                    "is_verified": lead_obj.is_verified,
                })
            except IntegrityError:
                logger.warning(f"Duplicate lead detected during creation for {email}")
            except Exception as e:
                logger.error(f"Unexpected error saving lead {email}: {e}")

        return saved_leads
