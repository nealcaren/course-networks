import json
import re
from datetime import datetime
from pathlib import Path
from filelock import FileLock
from flask import current_app


class DataStore:
    """Thread-safe JSON file storage for student registrations."""

    @staticmethod
    def _get_paths():
        """Get data file and lock file paths from app config."""
        data_file = current_app.config['DATA_FILE']
        lock_file = Path(str(data_file) + '.lock')
        return data_file, lock_file

    @staticmethod
    def _init_data():
        """Return initial empty data structure."""
        return {
            'students': [],
            'metadata': {
                'last_updated': datetime.utcnow().isoformat() + 'Z',
                'total_registrations': 0
            },
            'cached_centrality': {
                'students': {},
                'courses': {}
            }
        }

    @classmethod
    def read(cls):
        """Read all data from the JSON file."""
        data_file, lock_file = cls._get_paths()

        with FileLock(lock_file):
            if not data_file.exists():
                return cls._init_data()
            try:
                with open(data_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return cls._init_data()

    @classmethod
    def write(cls, data):
        """Write data to the JSON file."""
        data_file, lock_file = cls._get_paths()

        # Update metadata
        data['metadata']['last_updated'] = datetime.utcnow().isoformat() + 'Z'

        with FileLock(lock_file):
            data_file.parent.mkdir(parents=True, exist_ok=True)
            with open(data_file, 'w') as f:
                json.dump(data, f, indent=2)

    @classmethod
    def add_student(cls, student_id, courses):
        """Add or update a student registration and recompute centrality."""
        data = cls.read()

        # Remove existing registration if present
        data['students'] = [s for s in data['students'] if s['id'] != student_id]

        # Add new registration
        data['students'].append({
            'id': student_id,
            'courses': courses,
            'registered_at': datetime.utcnow().isoformat() + 'Z'
        })

        data['metadata']['total_registrations'] = len(data['students'])

        # Recompute and cache centrality
        data = cls._recompute_centrality(data)

        cls.write(data)
        return True

    @classmethod
    def remove_student(cls, student_id):
        """Remove a student registration and recompute centrality."""
        data = cls.read()

        original_count = len(data['students'])
        data['students'] = [s for s in data['students'] if s['id'] != student_id]

        if len(data['students']) < original_count:
            data['metadata']['total_registrations'] = len(data['students'])
            # Recompute and cache centrality
            data = cls._recompute_centrality(data)
            cls.write(data)
            return True
        return False

    @classmethod
    def get_students(cls):
        """Get all registered students."""
        return cls.read()['students']

    @classmethod
    def get_status(cls):
        """Get just the metadata for polling."""
        return cls.read()['metadata']

    @classmethod
    def get_cached_centrality(cls):
        """Get pre-computed centrality data."""
        data = cls.read()
        return data.get('cached_centrality', {'students': {}, 'courses': {}})

    @classmethod
    def _recompute_centrality(cls, data):
        """Recompute and cache all centrality metrics."""
        from app.services.centrality import CentralityService

        students = data['students']

        if not students:
            data['cached_centrality'] = {'students': {}, 'courses': {}}
            return data

        # Build networks and compute centrality
        student_graph = CentralityService.build_student_network(students)
        course_graph = CentralityService.build_course_network(students)

        student_centralities = CentralityService.calculate_centralities(student_graph)
        course_centralities = CentralityService.calculate_centralities(course_graph)

        data['cached_centrality'] = {
            'students': student_centralities,
            'courses': course_centralities
        }

        return data

    @staticmethod
    def parse_course(course_input):
        """
        Parse and normalize a course string.

        Input examples: "SOCI 101.002", "psyc210", "ECON 101"
        Output: "SOCI 101", "PSYC 210", "ECON 101"

        Returns None if invalid format.
        """
        if not course_input:
            return None

        # Strip section number (anything after .)
        course = course_input.split('.')[0].strip()

        # Uppercase and remove extra spaces
        course = course.upper().strip()

        # Try to extract department and number
        # Match patterns like "SOCI 101" or "SOCI101"
        match = re.match(r'^([A-Z]{4})\s*(\d{2,3})$', course)

        if match:
            dept, num = match.groups()
            return f"{dept} {num}"

        return None

    @staticmethod
    def validate_student_id(student_id):
        """
        Validate student ID format: 1 letter + 4 digits.

        Returns (is_valid, normalized_id or error_message)
        """
        if not student_id:
            return False, "Student ID is required"

        student_id = student_id.strip().upper()

        if not re.match(r'^[A-Z]\d{4}$', student_id):
            return False, "Student ID must be 1 letter followed by 4 digits (e.g., C1234)"

        return True, student_id
