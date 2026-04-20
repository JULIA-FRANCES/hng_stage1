# HNG Stage 2 - Intelligence Query Engine

A REST API for Insighta Labs that stores demographic profiles and supports advanced filtering, sorting, pagination, and natural language search.

## Live URL
https://hngstage1-production-f968.up.railway.app

## GitHub
https://github.com/JULIA-FRANCES/hng_stage1

## Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/profiles | Get all profiles with filters, sorting, pagination |
| GET | /api/profiles/search | Natural language search |
| GET | /api/profiles/{id} | Get single profile |
| POST | /api/profiles | Create a profile |
| DELETE | /api/profiles/{id} | Delete a profile |

## Filtering, Sorting & Pagination

### Filters
| Parameter | Description | Example |
|-----------|-------------|---------|
| gender | Filter by gender | gender=male |
| age_group | Filter by age group | age_group=adult |
| country_id | Filter by country code | country_id=NG |
| min_age | Minimum age | min_age=20 |
| max_age | Maximum age | max_age=30 |
| min_gender_probability | Minimum gender confidence | min_gender_probability=0.9 |
| min_country_probability | Minimum country confidence | min_country_probability=0.8 |

### Sorting
| Parameter | Options |
|-----------|---------|
| sort_by | age, created_at, gender_probability |
| order | asc, desc |

### Pagination
| Parameter | Default | Max |
|-----------|---------|-----|
| page | 1 | - |
| limit | 10 | 50 |

### Example
```
GET /api/profiles?gender=male&country_id=NG&min_age=25&sort_by=age&order=desc&page=1&limit=10
```

## Natural Language Search

### Endpoint
```
GET /api/profiles/search?q=young males from nigeria
```

### How It Works
The parser uses rule-based keyword matching. It scans the query for known keywords and converts them into database filters.

### Supported Keywords

| Keyword | Maps To |
|---------|---------|
| male, males | gender=male |
| female, females | gender=female |
| young | min_age=16, max_age=24 |
| adult, adults | age_group=adult |
| teenager, teenagers | age_group=teenager |
| child, children | age_group=child |
| senior, seniors | age_group=senior |
| above {n} | min_age=n |
| below {n} | max_age=n |
| older than {n} | min_age=n |
| younger than {n} | max_age=n |
| from {country} | country_id=ISO code |
| in {country} | country_id=ISO code |

### Supported Countries
Nigeria (NG), Ghana (GH), Kenya (KE), Tanzania (TZ), Uganda (UG),
Ethiopia (ET), South Africa (ZA), Egypt (EG), Angola (AO), Cameroon (CM),
Senegal (SN), Sudan (SD), USA (US), UK (GB), India (IN), France (FR),
Germany (DE), Brazil (BR), Canada (CA), and more.

### Example Mappings
| Query | Filters Applied |
|-------|----------------|
| young males | gender=male, min_age=16, max_age=24 |
| females above 30 | gender=female, min_age=30 |
| people from angola | country_id=AO |
| adult males from kenya | gender=male, age_group=adult, country_id=KE |
| seniors from nigeria | age_group=senior, country_id=NG |

### Unrecognised Queries
If no keywords are found, the API returns:
```json
{"status": "error", "message": "Unable to interpret query"}
```

## Limitations

- Country matching requires "from {country}" or "in {country}" — bare country names like just "nigeria" won't work
- Only supports one gender at a time — "male and female" will default to female
- "young" is a parser-only concept — it is not a stored age_group
- Spelling variations or abbreviations are not supported (e.g. "fem" won't work)
- Only supports English queries
- Complex queries like "not male" or "except nigeria" are not supported

## Tech Stack
- Python / Django
- Django REST Framework
- PostgreSQL (Supabase)
- Deployed on Railway