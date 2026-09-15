import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def recipes(request):
	"""Proxy recipe searches through the provider without exposing the API key."""
	if not settings.RAPIDAPI_KEY or not settings.RAPIDAPI_HOST:
		return JsonResponse(
			{
				'error': 'RapidAPI is not configured.',
				'details': 'Set RAPIDAPI_KEY and RAPIDAPI_HOST in backend/.env.',
			},
			status=503,
		)

	query = {
		key: value
		for key, value in request.GET.items()
		if key.lower() not in {'apikey', 'x-rapidapi-key', 'x-rapidapi-host', 'limit', 'size'}
	}
	query.setdefault('lang', 'en')
	try:
		requested_limit = int(request.GET.get('limit', 15))
	except (TypeError, ValueError):
		requested_limit = 15
	query['size'] = str(max(1, min(requested_limit, 15)))
	rapidapi_host = settings.RAPIDAPI_HOST.removeprefix('https://').removeprefix('http://').rstrip('/')
	rapidapi_path = f"/{settings.RAPIDAPI_PATH.lstrip('/')}"
	provider_url = f"https://{rapidapi_host}{rapidapi_path}"
	provider_request = Request(
		f"{provider_url}?{urlencode(query)}",
		headers={
			'Accept': 'application/json',
			'X-RapidAPI-Key': settings.RAPIDAPI_KEY,
			'X-RapidAPI-Host': rapidapi_host,
		},
	)

	try:
		with urlopen(provider_request, timeout=10) as response:
			payload = json.load(response)
	except HTTPError as error:
		try:
			details = json.loads(error.read().decode('utf-8'))
		except (json.JSONDecodeError, UnicodeDecodeError):
			details = {'message': 'The recipe provider returned an error.'}
		return JsonResponse(
			{'error': 'Recipe provider request failed.', 'details': details},
			status=502,
		)
	except URLError:
		return JsonResponse(
			{'error': 'The recipe provider could not be reached.'},
			status=502,
		)

	return JsonResponse(payload, safe=not isinstance(payload, list))
