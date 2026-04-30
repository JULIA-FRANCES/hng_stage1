import csv
import requests
from datetime import datetime, timezone

from django.http import HttpResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .models import Profile
from authentication.backends import JWTAuthentication


def error_response(message, http_status):
    return Response(
        {"status": "error", "message": message},
        status=http_status,
    )


def check_api_version(request):
    version = request.headers.get('X-API-Version')
    if not version:
        return False
    return True


def is_authenticated(request):
    return request.user and hasattr(request.user, 'id') and request.user.is_active


def get_age_group(age):
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    else:
        return "senior"


def format_profile(profile):
    return {
        "id": str(profile.id),
        "name": profile.name,
        "gender": profile.gender,
        "gender_probability": profile.gender_probability,
        "age": profile.age,
        "age_group": profile.age_group,
        "country_id": profile.country_id,
        "country_name": profile.country_name,
        "country_probability": profile.country_probability,
        "created_at": profile.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def format_profile_list(profile):
    return {
        "id": str(profile.id),
        "name": profile.name,
        "gender": profile.gender,
        "gender_probability": profile.gender_probability,
        "age": profile.age,
        "age_group": profile.age_group,
        "country_id": profile.country_id,
        "country_name": profile.country_name,
        "country_probability": profile.country_probability,
        "created_at": profile.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def build_pagination_links(request, page, limit, total):
    base_url = request.path
    params = request.GET.copy()

    params['page'] = page
    params['limit'] = limit
    self_link = f"{base_url}?{params.urlencode()}"

    total_pages = (total + limit - 1) // limit
    if page < total_pages:
        params['page'] = page + 1
        next_link = f"{base_url}?{params.urlencode()}"
    else:
        next_link = None

    if page > 1:
        params['page'] = page - 1
        prev_link = f"{base_url}?{params.urlencode()}"
    else:
        prev_link = None

    return self_link, next_link, prev_link, total_pages


def apply_filters(queryset, request):
    gender = request.query_params.get("gender")
    country_id = request.query_params.get("country_id")
    age_group = request.query_params.get("age_group")
    min_age = request.query_params.get("min_age")
    max_age = request.query_params.get("max_age")
    min_gender_probability = request.query_params.get("min_gender_probability")
    min_country_probability = request.query_params.get("min_country_probability")

    if gender:
        queryset = queryset.filter(gender__iexact=gender)
    if country_id:
        queryset = queryset.filter(country_id__iexact=country_id)
    if age_group:
        queryset = queryset.filter(age_group__iexact=age_group)
    if min_age:
        try:
            queryset = queryset.filter(age__gte=int(min_age))
        except ValueError:
            return None, "Invalid query parameters"
    if max_age:
        try:
            queryset = queryset.filter(age__lte=int(max_age))
        except ValueError:
            return None, "Invalid query parameters"
    if min_gender_probability:
        try:
            queryset = queryset.filter(gender_probability__gte=float(min_gender_probability))
        except ValueError:
            return None, "Invalid query parameters"
    if min_country_probability:
        try:
            queryset = queryset.filter(country_probability__gte=float(min_country_probability))
        except ValueError:
            return None, "Invalid query parameters"

    return queryset, None


def apply_sorting(queryset, request):
    sort_by = request.query_params.get("sort_by")
    order = request.query_params.get("order", "asc")
    valid_sort_fields = ["age", "created_at", "gender_probability"]

    if sort_by:
        if sort_by not in valid_sort_fields:
            return None, "Invalid query parameters"
        if order == "desc":
            queryset = queryset.order_by(f"-{sort_by}")
        else:
            queryset = queryset.order_by(sort_by)

    return queryset, None


def parse_natural_language(query):
    query = query.lower().strip()
    filters = {}

    if "female" in query or "females" in query:
        filters["gender"] = "female"
    elif "male" in query or "males" in query:
        filters["gender"] = "male"

    if "young" in query:
        filters["min_age"] = 16
        filters["max_age"] = 24
    elif "teenager" in query or "teenagers" in query:
        filters["age_group"] = "teenager"
    elif "child" in query or "children" in query:
        filters["age_group"] = "child"
    elif "senior" in query or "seniors" in query:
        filters["age_group"] = "senior"
    elif "adult" in query or "adults" in query:
        filters["age_group"] = "adult"

    import re
    above_match = re.search(r'above\s+(\d+)', query)
    below_match = re.search(r'below\s+(\d+)', query)
    older_match = re.search(r'older than\s+(\d+)', query)
    younger_match = re.search(r'younger than\s+(\d+)', query)
    over_match = re.search(r'over\s+(\d+)', query)
    under_match = re.search(r'under\s+(\d+)', query)

    if above_match:
        filters["min_age"] = int(above_match.group(1))
    if below_match:
        filters["max_age"] = int(below_match.group(1))
    if older_match:
        filters["min_age"] = int(older_match.group(1))
    if younger_match:
        filters["max_age"] = int(younger_match.group(1))
    if over_match:
        filters["min_age"] = int(over_match.group(1))
    if under_match:
        filters["max_age"] = int(under_match.group(1))

    country_map = {
        "nigeria": "NG", "ghana": "GH", "kenya": "KE",
        "tanzania": "TZ", "uganda": "UG", "ethiopia": "ET",
        "south africa": "ZA", "egypt": "EG", "angola": "AO",
        "cameroon": "CM", "senegal": "SN", "mali": "ML",
        "sudan": "SD", "madagascar": "MG", "ivory coast": "CI",
        "mozambique": "MZ", "zambia": "ZM", "zimbabwe": "ZW",
        "united states": "US", "usa": "US", "uk": "GB",
        "united kingdom": "GB", "india": "IN", "france": "FR",
        "germany": "DE", "brazil": "BR", "canada": "CA",
        "benin": "BJ", "togo": "TG", "niger": "NE",
        "chad": "TD", "rwanda": "RW", "burundi": "BI",
        "somalia": "SO", "algeria": "DZ", "morocco": "MA",
        "tunisia": "TN", "libya": "LY", "congo": "CG",
    }

    for country_name, code in country_map.items():
        if f"from {country_name}" in query or f"in {country_name}" in query:
            filters["country_id"] = code
            break

    return filters


@api_view(["GET", "DELETE"])
def profile_detail(request, pk):
    if not check_api_version(request):
        return error_response("API version header required", status.HTTP_400_BAD_REQUEST)

    if not is_authenticated(request):
        return error_response("Authentication required", status.HTTP_401_UNAUTHORIZED)

    import uuid
    try:
        uuid.UUID(str(pk))
    except ValueError:
        return error_response("Profile not found.", status.HTTP_404_NOT_FOUND)

    try:
        profile = Profile.objects.get(pk=pk)
    except Profile.DoesNotExist:
        return error_response("Profile not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(
            {"status": "success", "data": format_profile(profile)},
            status=status.HTTP_200_OK,
        )

    if request.method == "DELETE":
        if request.user.role != 'admin':
            return error_response("Admin access required", status.HTTP_403_FORBIDDEN)
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def profile_search(request):
    if not check_api_version(request):
        return error_response("API version header required", status.HTTP_400_BAD_REQUEST)

    if not is_authenticated(request):
        return error_response("Authentication required", status.HTTP_401_UNAUTHORIZED)

    query = request.query_params.get("q", "").strip()

    if not query:
        return error_response("q parameter is required.", status.HTTP_400_BAD_REQUEST)

    filters = parse_natural_language(query)

    if not filters:
        return Response(
            {"status": "error", "message": "Unable to interpret query"},
            status=status.HTTP_200_OK,
        )

    queryset = Profile.objects.all()

    if "gender" in filters:
        queryset = queryset.filter(gender=filters["gender"])
    if "age_group" in filters:
        queryset = queryset.filter(age_group=filters["age_group"])
    if "country_id" in filters:
        queryset = queryset.filter(country_id=filters["country_id"])
    if "min_age" in filters:
        queryset = queryset.filter(age__gte=filters["min_age"])
    if "max_age" in filters:
        queryset = queryset.filter(age__lte=filters["max_age"])

    try:
        page = max(1, int(request.query_params.get("page", 1)))
        limit = min(50, max(1, int(request.query_params.get("limit", 10))))
    except ValueError:
        return error_response("Invalid query parameters", status.HTTP_400_BAD_REQUEST)

    total = queryset.count()
    self_link, next_link, prev_link, total_pages = build_pagination_links(request, page, limit, total)
    start = (page - 1) * limit
    end = start + limit
    queryset = queryset[start:end]

    return Response(
        {
            "status": "success",
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "links": {
                "self": self_link,
                "next": next_link,
                "prev": prev_link,
            },
            "data": [format_profile_list(p) for p in queryset],
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
def profile_export(request):
    if not check_api_version(request):
        return error_response("API version header required", status.HTTP_400_BAD_REQUEST)

    if not is_authenticated(request):
        return error_response("Authentication required", status.HTTP_401_UNAUTHORIZED)

    queryset = Profile.objects.all()

    queryset, error = apply_filters(queryset, request)
    if error:
        return error_response(error, status.HTTP_400_BAD_REQUEST)

    queryset, error = apply_sorting(queryset, request)
    if error:
        return error_response(error, status.HTTP_400_BAD_REQUEST)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"profiles_{timestamp}.csv"

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'id', 'name', 'gender', 'gender_probability',
        'age', 'age_group', 'country_id', 'country_name',
        'country_probability', 'created_at'
    ])

    for profile in queryset:
        writer.writerow([
            str(profile.id),
            profile.name,
            profile.gender,
            profile.gender_probability,
            profile.age,
            profile.age_group,
            profile.country_id,
            profile.country_name,
            profile.country_probability,
            profile.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        ])

    return response


@api_view(["GET", "POST"])
def profiles_router(request):
    if not check_api_version(request):
        return error_response("API version header required", status.HTTP_400_BAD_REQUEST)

    if not is_authenticated(request):
        return error_response("Authentication required", status.HTTP_401_UNAUTHORIZED)

    if request.method == "GET":
        queryset = Profile.objects.all()

        queryset, error = apply_filters(queryset, request)
        if error:
            return error_response(error, status.HTTP_400_BAD_REQUEST)

        queryset, error = apply_sorting(queryset, request)
        if error:
            return error_response(error, status.HTTP_400_BAD_REQUEST)

        try:
            page = max(1, int(request.query_params.get("page", 1)))
            limit = min(50, max(1, int(request.query_params.get("limit", 10))))
        except ValueError:
            return error_response("Invalid query parameters", status.HTTP_400_BAD_REQUEST)

        total = queryset.count()
        self_link, next_link, prev_link, total_pages = build_pagination_links(
            request, page, limit, total
        )
        start = (page - 1) * limit
        end = start + limit
        paginated = queryset[start:end]

        return Response(
            {
                "status": "success",
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
                "links": {
                    "self": self_link,
                    "next": next_link,
                    "prev": prev_link,
                },
                "data": [format_profile_list(p) for p in paginated],
            },
            status=status.HTTP_200_OK,
        )

    elif request.method == "POST":
        if request.user.role != 'admin':
            return error_response("Admin access required", status.HTTP_403_FORBIDDEN)

        name = request.data.get("name", None)

        if name is None or name == "":
            return error_response("name is required.", status.HTTP_400_BAD_REQUEST)

        try:
            float(name)
            return error_response(
                "name must be a string.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except (ValueError, TypeError):
            pass

        existing = Profile.objects.filter(name__iexact=name).first()
        if existing:
            return Response(
                {
                    "status": "success",
                    "message": "Profile already exists",
                    "data": format_profile(existing),
                },
                status=status.HTTP_200_OK,
            )

        try:
            gender_resp = requests.get(f"https://api.genderize.io?name={name}", timeout=5)
            gender_data = gender_resp.json()
        except Exception:
            return error_response("Genderize returned an invalid response", status.HTTP_502_BAD_GATEWAY)

        try:
            age_resp = requests.get(f"https://api.agify.io?name={name}", timeout=5)
            age_data = age_resp.json()
        except Exception:
            return error_response("Agify returned an invalid response", status.HTTP_502_BAD_GATEWAY)

        try:
            nation_resp = requests.get(f"https://api.nationalize.io?name={name}", timeout=5)
            nation_data = nation_resp.json()
        except Exception:
            return error_response("Nationalize returned an invalid response", status.HTTP_502_BAD_GATEWAY)

        if not gender_data.get("gender") or gender_data.get("count", 0) == 0:
            return error_response("Genderize returned an invalid response", status.HTTP_502_BAD_GATEWAY)

        if not age_data.get("age"):
            return error_response("Agify returned an invalid response", status.HTTP_502_BAD_GATEWAY)

        countries = nation_data.get("country", [])
        if not countries:
            return error_response("Nationalize returned an invalid response", status.HTTP_502_BAD_GATEWAY)

        gender = gender_data["gender"]
        gender_probability = gender_data["probability"]
        sample_size = gender_data["count"]
        age = age_data["age"]
        age_group = get_age_group(age)
        top_country = max(countries, key=lambda x: x["probability"])
        country_id = top_country["country_id"]
        country_probability = top_country["probability"]

        profile = Profile.objects.create(
            name=name.lower(),
            gender=gender,
            gender_probability=gender_probability,
            sample_size=sample_size,
            age=age,
            age_group=age_group,
            country_id=country_id,
            country_name=None,
            country_probability=country_probability,
        )

        return Response(
            {"status": "success", "data": format_profile(profile)},
            status=status.HTTP_201_CREATED,
        )