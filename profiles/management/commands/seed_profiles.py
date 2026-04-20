import json
import os
from django.core.management.base import BaseCommand
from profiles.models import Profile

class Command(BaseCommand):
    help = 'Seed database with 2026 profiles'

    def handle(self, *args, **kwargs):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        json_path = os.path.join(base_dir, 'seed_profiles.json')

        with open(json_path, 'r') as f:
            data = json.load(f)

        profiles = data['profiles']
        
        # Get existing names to skip duplicates
        existing_names = set(
            Profile.objects.values_list('name', flat=True)
        )

        new_profiles = [
            Profile(
                name=p['name'],
                gender=p['gender'],
                gender_probability=p['gender_probability'],
                age=p['age'],
                age_group=p['age_group'],
                country_id=p['country_id'],
                country_name=p['country_name'],
                country_probability=p['country_probability'],
            )
            for p in profiles
            if p['name'] not in existing_names
        ]

        Profile.objects.bulk_create(new_profiles, ignore_conflicts=True)
        
        self.stdout.write(f'✅ Done! Inserted: {len(new_profiles)} new profiles, Skipped: {len(existing_names)} existing')