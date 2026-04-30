import jwt
import uuid
import requests
from datetime import datetime, timezone, timedelta
from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils import timezone as django_timezone
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle

from .models import User, RefreshToken


class AuthRateThrottle(AnonRateThrottle):
    rate = '10/minute'
    scope = 'auth'


def generate_access_token(user):
    payload = {
        'user_id': str(user.id),
        'username': user.username,
        'role': user.role,
        'exp': datetime.now(timezone.utc) + timedelta(seconds=settings.ACCESS_TOKEN_EXPIRY),
        'iat': datetime.now(timezone.utc),
        'type': 'access'
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def generate_refresh_token(user):
    payload = {
        'user_id': str(user.id),
        'exp': datetime.now(timezone.utc) + timedelta(seconds=settings.REFRESH_TOKEN_EXPIRY),
        'iat': datetime.now(timezone.utc),
        'type': 'refresh',
        'jti': str(uuid.uuid4())
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.REFRESH_TOKEN_EXPIRY)
    RefreshToken.objects.create(
        user=user,
        token=token,
        expires_at=expires_at
    )
    
    return token


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def github_login(request):
    client_id = settings.GITHUB_CLIENT_ID
    redirect_uri = request.GET.get('redirect_uri', settings.GITHUB_REDIRECT_URI)
    code_challenge = request.GET.get('code_challenge', '')
    code_challenge_method = request.GET.get('code_challenge_method', '')
    state = request.GET.get('state', str(uuid.uuid4()))
    
    github_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=read:user,user:email"
        f"&state={state}"
    )
    
    if code_challenge:
        github_url += f"&code_challenge={code_challenge}&code_challenge_method={code_challenge_method}"
    
    return HttpResponseRedirect(github_url)

@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def github_callback(request):
    """Handle GitHub OAuth callback"""
    code = request.GET.get('code')
    error = request.GET.get('error')
    state = request.GET.get('state')

    if not state:
        return Response(
            {"status": "error", "message": "Missing state parameter"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if error:
        return Response(
            {"status": "error", "message": "GitHub OAuth failed"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not code:
        return Response(
            {"status": "error", "message": "No code provided"},
            status=status.HTTP_400_BAD_REQUEST
        )

    code_verifier = request.GET.get('code_verifier', '')
    redirect_uri = request.GET.get('redirect_uri', settings.GITHUB_REDIRECT_URI)

    token_data = {
        'client_id': settings.GITHUB_CLIENT_ID,
        'client_secret': settings.GITHUB_CLIENT_SECRET,
        'code': code,
        'redirect_uri': redirect_uri,
    }

    if code_verifier:
        token_data['code_verifier'] = code_verifier
    
    try:
        token_response = requests.post(
            'https://github.com/login/oauth/access_token',
            data=token_data,
            headers={'Accept': 'application/json'},
            timeout=10
        )
        token_json = token_response.json()
    except Exception:
        return Response(
            {"status": "error", "message": "Failed to exchange code with GitHub"},
            status=status.HTTP_502_BAD_GATEWAY
        )
    
    github_access_token = token_json.get('access_token')
    if not github_access_token:
        return Response(
            {"status": "error", "message": "Failed to get GitHub access token"},
            status=status.HTTP_502_BAD_GATEWAY
        )
    
    try:
        user_response = requests.get(
            'https://api.github.com/user',
            headers={
                'Authorization': f'token {github_access_token}',
                'Accept': 'application/json'
            },
            timeout=10
        )
        github_user = user_response.json()
    except Exception:
        return Response(
            {"status": "error", "message": "Failed to get user info from GitHub"},
            status=status.HTTP_502_BAD_GATEWAY
        )
    
    email = github_user.get('email')
    if not email:
        try:
            email_response = requests.get(
                'https://api.github.com/user/emails',
                headers={
                    'Authorization': f'token {github_access_token}',
                    'Accept': 'application/json'
                },
                timeout=10
            )
            emails = email_response.json()
            primary = next((e for e in emails if e.get('primary')), None)
            email = primary['email'] if primary else None
        except Exception:
            email = None
    
    user, created = User.objects.get_or_create(
        github_id=str(github_user['id']),
        defaults={
            'username': github_user.get('login', ''),
            'email': email,
            'avatar_url': github_user.get('avatar_url', ''),
            'role': 'analyst',
        }
    )
    
    if not created:
        user.username = github_user.get('login', user.username)
        user.email = email or user.email
        user.avatar_url = github_user.get('avatar_url', user.avatar_url)
        user.last_login_at = django_timezone.now()
        user.save()
    
    if not user.is_active:
        return Response(
            {"status": "error", "message": "Account is disabled"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    access_token = generate_access_token(user)
    refresh_token = generate_refresh_token(user)
    
    return Response(
        {
            "status": "success",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "avatar_url": user.avatar_url,
                "role": user.role,
            }
        },
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def refresh_token_view(request):
    """Refresh access token using refresh token"""
    refresh_token = request.data.get('refresh_token')
    
    if not refresh_token:
        return Response(
            {"status": "error", "message": "Refresh token required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=['HS256']
        )
    except jwt.ExpiredSignatureError:
        return Response(
            {"status": "error", "message": "Refresh token has expired"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    except jwt.InvalidTokenError:
        return Response(
            {"status": "error", "message": "Invalid refresh token"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if payload.get('type') != 'refresh':
        return Response(
            {"status": "error", "message": "Invalid token type"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    try:
        token_obj = RefreshToken.objects.get(token=refresh_token, is_used=False)
    except RefreshToken.DoesNotExist:
        return Response(
            {"status": "error", "message": "Invalid or already used refresh token"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if token_obj.expires_at < django_timezone.now():
        return Response(
            {"status": "error", "message": "Refresh token has expired"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token_obj.is_used = True
    token_obj.save()
    
    try:
        user = User.objects.get(id=payload['user_id'])
    except User.DoesNotExist:
        return Response(
            {"status": "error", "message": "User not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if not user.is_active:
        return Response(
            {"status": "error", "message": "Account is disabled"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    new_access_token = generate_access_token(user)
    new_refresh_token = generate_refresh_token(user)
    
    return Response(
        {
            "status": "success",
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
        },
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
@throttle_classes([AuthRateThrottle])
def logout_view(request):
    """Invalidate refresh token"""
    refresh_token = request.data.get('refresh_token')
    
    if refresh_token:
        try:
            RefreshToken.objects.filter(token=refresh_token).update(is_used=True)
        except Exception:
            pass
    
    return Response(
        {"status": "success", "message": "Logged out successfully"},
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
def whoami_view(request):
    """Get current user info"""
    user = request.user
    return Response(
        {
            "status": "success",
            "data": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "avatar_url": user.avatar_url,
                "role": user.role,
                "last_login_at": user.last_login_at,
                "created_at": user.created_at,
            }
        },
        status=status.HTTP_200_OK
    )

@api_view(["GET"])
def users_me_view(request):
    user = request.user
    return Response({
        "status": "success",
        "data": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "last_login_at": user.last_login_at,
            "created_at": user.created_at,
        }
    }, status=status.HTTP_200_OK)