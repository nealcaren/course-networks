from flask import Blueprint, render_template

views_bp = Blueprint('views', __name__)


@views_bp.route('/student-network')
def student_network():
    """Student network visualization page."""
    return render_template('student_network.html')


@views_bp.route('/course-network')
def course_network():
    """Course network visualization page."""
    return render_template('course_network.html')


@views_bp.route('/stats')
def stats():
    """Statistics and centrality metrics page."""
    return render_template('stats.html')
