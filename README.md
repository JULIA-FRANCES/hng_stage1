# HNG Stage 1 - Profile API

A REST API that accepts a name and returns predicted gender, age, and nationality using external APIs.

## Live URL
https://hngstage1-production-f968.up.railway.app

## Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| POST | /api/profiles | Create a profile |
| GET | /api/profiles | Get all profiles |
| GET | /api/profiles/{id} | Get single profile |
| DELETE | /api/profiles/{id} | Delete a profile |

## Tech Stack
- Python / Django
- Django REST Framework
- PostgreSQL (Supabase)
- Deployed on Railway