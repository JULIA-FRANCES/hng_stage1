import requests
from datetime import datetime, timezone

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Profile


def error_response(message, http_status):
    return Response(
        {"status": "error", "message": message},
        status=http_status,
    )


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
        "sample_size": profile.sample_size,
        "age": profile.age,
        "age_group": profile.age_group,
        "country_id": profile.country_id,
        "country_probability": profile.country_probability,
        "created_at": profile.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def format_profile_list(profile):
    return {
        "id": str(profile.id),
        "name": profile.name,
        "gender": profile.gender,
        "age": profile.age,
        "age_group": profile.age_group,
        "country_id": profile.country_id,
    }


@api_view(["GET", "DELETE"])
def profile_detail(request, pk):
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
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
@api_view(["GET", "POST"])
def profiles_router(request):
    if request.method == "GET":
        queryset = Profile.objects.all()

        gender = request.query_params.get("gender")
        country_id = request.query_params.get("country_id")
        age_group = request.query_params.get("age_group")

        if gender:
            queryset = queryset.filter(gender__iexact=gender)
        if country_id:
            queryset = queryset.filter(country_id__iexact=country_id)
        if age_group:
            queryset = queryset.filter(age_group__iexact=age_group)

        return Response(
            {
                "status": "success",
                "count": queryset.count(),
                "data": [format_profile_list(p) for p in queryset],
            },
            status=status.HTTP_200_OK,
        )

    elif request.method == "POST":
        # Get name from request body
        name = request.data.get("name", None)

        # Validate name
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

        # Check if profile already exists
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

        # Call all three APIs
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

        # Check edge cases
        if not gender_data.get("gender") or gender_data.get("count", 0) == 0:
            return error_response("Genderize returned an invalid response", status.HTTP_502_BAD_GATEWAY)

        if not age_data.get("age"):
            return error_response("Agify returned an invalid response", status.HTTP_502_BAD_GATEWAY)

        countries = nation_data.get("country", [])
        if not countries:
            return error_response("Nationalize returned an invalid response", status.HTTP_502_BAD_GATEWAY)

        # Process the data
        gender = gender_data["gender"]
        gender_probability = gender_data["probability"]
        sample_size = gender_data["count"]
        age = age_data["age"]
        age_group = get_age_group(age)
        top_country = max(countries, key=lambda x: x["probability"])
        country_id = top_country["country_id"]
        country_probability = top_country["probability"]

        # Save to database
        profile = Profile.objects.create(
            name=name.lower(),
            gender=gender,
            gender_probability=gender_probability,
            sample_size=sample_size,
            age=age,
            age_group=age_group,
            country_id=country_id,
            country_probability=country_probability,
        )

        return Response(
            {"status": "success", "data": format_profile(profile)},
            status=status.HTTP_201_CREATED,
        )