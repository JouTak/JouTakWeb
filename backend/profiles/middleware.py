class HubPrivacyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(
            (
                "/api/profiles",
                "/api/communities",
                "/api/cities",
                "/api/moderation/cities",
                "/api/account/memberships",
                "/api/account/server-communities",
                "/api/groups",
                "/api/account/group",
                "/api/moderation/groups",
            )
        ):
            response["Cache-Control"] = "private, no-store"
            response["Vary"] = "Cookie, X-Session-Token, Origin"
        return response
