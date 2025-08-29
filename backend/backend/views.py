from http import HTTPStatus
from ninja import Router
from django.http import HttpResponse

router = Router()


@router.get("/health", response={HTTPStatus.OK: str})
def health(request):
    return HttpResponse("<p>Alive</p>", status=HTTPStatus.OK)
