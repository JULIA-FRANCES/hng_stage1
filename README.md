# Insighta Labs+ — Backend

A secure, role-based Profile Intelligence API built with Django REST Framework.

## System Architecture

```
insighta-cli  ──┐
                ├──▶  Django Backend (Railway)  ──▶  Supabase PostgreSQL
insighta-web  ──┘
```

- **Backend**: Django 6 + DRF, hosted on Railway
- **Database**: Supabase PostgreSQL
- **Auth**: GitHub OAuth 2.0 + PKCE, JWT access/refresh tokens
- **Roles**: `admin` and `analyst`, enforced on every endpoint

## Authentication Flow

1. Client generates PKCE `code_verifier` + `code_challenge`
2. Client redirects to `GET /auth/github` with challenge + state + redirect_uri
3. Django redirects to GitHub OAuth
4. GitHub redirects back with `code`
5. Client sends `code` + `code_verifier` to `GET /auth/github/callback`
6. Django exchanges code with GitHub, fetches user info, creates/updates user
7. Django returns `access_token` (3 min) + `refresh_token` (5 min) + user info

## Token Handling

| Token | Expiry | Purpose |
|-------|--------|---------|
| Access Token | 180s (3 min) | Authenticate API requests via `Authorization: Bearer` header |
| Refresh Token | 300s (5 min) | Obtain new access token via `POST /auth/refresh` |

- Refresh tokens are stored in the database and invalidated after use (rotation)
- Expired/used refresh tokens return `401`

## Role Enforcement Logic

| Role | Permissions |
|------|-------------|
| `admin` | Full CRUD on profiles, CSV export, user management |
| `analyst` | Read-only access to profiles, search, export |

- Role is embedded in the JWT payload
- Every protected endpoint checks `request.user.role`
- Middleware validates token signature and expiry on every request

## API Versioning

All requests must include the header:
```
X-API-Version: 1
```

## Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/github` | Initiate GitHub OAuth |
| GET | `/auth/github/callback` | Handle OAuth callback |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Invalidate refresh token |
| GET | `/auth/whoami` | Get current user info |

### Profiles
| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| GET | `/api/profiles` | List profiles with filters/pagination | All |
| POST | `/api/profiles` | Create profile (Agify/Genderize/Nationalize) | Admin |
| GET | `/api/profiles/:id` | Get single profile | All |
| DELETE | `/api/profiles/:id` | Delete profile | Admin |
| GET | `/api/profiles/search` | Natural language search | All |
| GET | `/api/profiles/export` | Export CSV | All |

## Pagination Shape

```json
{
  "status": "success",
  "total": 100,
  "page": 1,
  "limit": 10,
  "total_pages": 10,
  "links": {
    "next": "/api/profiles?page=2",
    "prev": null
  },
  "data": []
}
```

## Natural Language Parsing

The `/api/profiles/search?q=` endpoint parses queries like:
- `"young males from Nigeria"` → filters gender=male, age_group=young adult, country=NG
- `"females over 30"` → filters gender=female, min_age=30
- `"seniors"` → filters age_group=senior

Parsing uses keyword matching and regex on the query string.

## Rate Limiting

- `/auth/*` endpoints: 10 requests/minute
- All other endpoints: 60 requests/minute

## Setup & Running Locally

```bash
git clone https://github.com/JULIA-FRANCES/hng_stage1
cd hng_stage1
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # fill in your values
python manage.py migrate
python manage.py runserver
```

## Environment Variables

```
SECRET_KEY=
DEBUG=False
DATABASE_URL=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_REDIRECT_URI=
ACCESS_TOKEN_EXPIRY=180
REFRESH_TOKEN_EXPIRY=300
```

## Live URL

`https://hngstage1-production-f968.up.railway.app`