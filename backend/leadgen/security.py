"""Security headers for every response (the API serves JSON, so the CSP can be fully locked down)."""

API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
# Server-rendered review pages (outreach/review.py) use inline styles only.
PAGE_CSP = "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/admin') or request.path.startswith('/static'):
            return response
        html = 'text/html' in response.get('Content-Type', '')
        response.setdefault('Content-Security-Policy', PAGE_CSP if html else API_CSP)
        response.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=()')
        response.setdefault('Cross-Origin-Resource-Policy', 'same-site')
        response.setdefault('Cache-Control', 'no-store')
        return response
