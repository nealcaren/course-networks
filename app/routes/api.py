from flask import Blueprint, request, jsonify
from app.services.data_store import DataStore
from app.services.centrality import CentralityService

api_bp = Blueprint('api', __name__)


@api_bp.route('/register', methods=['POST'])
def register():
    """Register a student with their courses."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Validate student ID
    student_id = data.get('student_id', '')
    is_valid, result = DataStore.validate_student_id(student_id)

    if not is_valid:
        return jsonify({'error': result}), 400

    student_id = result  # Normalized ID

    # Parse and validate courses
    raw_courses = data.get('courses', [])
    if not raw_courses:
        return jsonify({'error': 'At least one course is required'}), 400

    courses = []
    for course in raw_courses:
        parsed = DataStore.parse_course(course)
        if parsed:
            courses.append(parsed)
        else:
            return jsonify({
                'error': f'Invalid course format: "{course}". Use format like "SOCI 101" or "PSYC210"'
            }), 400

    # Remove duplicates while preserving order
    seen = set()
    unique_courses = []
    for c in courses:
        if c not in seen:
            seen.add(c)
            unique_courses.append(c)

    # Save registration
    DataStore.add_student(student_id, unique_courses)

    return jsonify({
        'success': True,
        'student_id': student_id,
        'courses': unique_courses
    }), 201


@api_bp.route('/students', methods=['GET'])
def get_students():
    """Get all registered students."""
    students = DataStore.get_students()
    return jsonify({'students': students})


@api_bp.route('/student/<student_id>', methods=['DELETE'])
def delete_student(student_id):
    """Remove a student registration."""
    # Validate and normalize ID
    is_valid, result = DataStore.validate_student_id(student_id)
    if not is_valid:
        return jsonify({'error': result}), 400

    student_id = result

    if DataStore.remove_student(student_id):
        return jsonify({'success': True, 'message': f'Student {student_id} removed'})
    else:
        return jsonify({'error': 'Student not found'}), 404


@api_bp.route('/network/students', methods=['GET'])
def student_network():
    """Get student network data in D3 format."""
    students = DataStore.get_students()
    network_data = CentralityService.get_student_network_d3(students)
    return jsonify(network_data)


@api_bp.route('/network/courses', methods=['GET'])
def course_network():
    """Get course network data in D3 format."""
    students = DataStore.get_students()
    network_data = CentralityService.get_course_network_d3(students)
    return jsonify(network_data)


@api_bp.route('/stats', methods=['GET'])
def stats():
    """Get cached centrality metrics and network statistics."""
    students = DataStore.get_students()
    cached = DataStore.get_cached_centrality()

    # Get basic stats (these are quick to compute)
    overview = CentralityService.get_network_stats(students)

    return jsonify({
        'overview': overview,
        'student_centralities': cached.get('students', {}),
        'course_centralities': cached.get('courses', {})
    })


@api_bp.route('/status', methods=['GET'])
def status():
    """Get last_updated timestamp for polling."""
    metadata = DataStore.get_status()
    return jsonify(metadata)


@api_bp.route('/centrality/student/<student_id>', methods=['GET'])
def student_centrality(student_id):
    """Get cached centrality metrics for a specific student."""
    cached = DataStore.get_cached_centrality()
    student_centralities = cached.get('students', {})

    if student_id not in student_centralities:
        return jsonify({'error': 'Student not found'}), 404

    return jsonify({
        'id': student_id,
        'centrality': student_centralities.get(student_id, {})
    })


@api_bp.route('/centrality/course/<path:course_id>', methods=['GET'])
def course_centrality(course_id):
    """Get cached centrality metrics for a specific course."""
    cached = DataStore.get_cached_centrality()
    course_centralities = cached.get('courses', {})

    if course_id not in course_centralities:
        return jsonify({'error': 'Course not found'}), 404

    return jsonify({
        'id': course_id,
        'centrality': course_centralities.get(course_id, {})
    })
