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
	if not settings.RECIPE_API_KEY:
		return JsonResponse(
			{'error': 'Recipe API is not configured. Set RECIPE_API_KEY.'},
			status=503,
		)

	query = {
		key: value
		for key, value in request.GET.items()
		if key.lower() != 'apikey'
	}
	query.setdefault('lang', 'en')
	query['apikey'] = settings.RECIPE_API_KEY
	provider_request = Request(
		f"https://recipeapi.io/api/v1/recipes?{urlencode(query)}",
		headers={'Accept': 'application/json'},
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
