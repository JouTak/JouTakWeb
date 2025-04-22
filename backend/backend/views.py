from http import HTTPStatus

from rest_framework.response import Response

__all__ = "health"


def health(request):
    if request.method != "GET":
        return Response(status=HTTPStatus.METHOD_NOT_ALLOWED)

    return Response("<p>Alive<p/>", status=HTTPStatus.OK)
