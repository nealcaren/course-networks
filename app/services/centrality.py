import networkx as nx
from collections import defaultdict


class CentralityService:
    """NetworkX-based centrality calculations for student and course networks."""

    EXCLUDED_COURSE = "SOCI 101"

    @classmethod
    def build_student_network(cls, students):
        """
        Build a graph where students are nodes and edges connect
        students who share courses (excluding SOCI 101).

        Edge weight = number of shared courses.
        """
        G = nx.Graph()

        # Add all students as nodes with course count as attribute
        for student in students:
            filtered_courses = [c for c in student['courses'] if c != cls.EXCLUDED_COURSE]
            G.add_node(student['id'], course_count=len(student['courses']))

        # Build course -> students mapping (excluding SOCI 101)
        course_students = defaultdict(set)
        for student in students:
            for course in student['courses']:
                if course != cls.EXCLUDED_COURSE:
                    course_students[course].add(student['id'])

        # Create edges between students who share courses
        edge_weights = defaultdict(int)
        for course, student_set in course_students.items():
            student_list = list(student_set)
            for i in range(len(student_list)):
                for j in range(i + 1, len(student_list)):
                    s1, s2 = sorted([student_list[i], student_list[j]])
                    edge_weights[(s1, s2)] += 1

        # Add weighted edges
        for (s1, s2), weight in edge_weights.items():
            G.add_edge(s1, s2, weight=weight)

        return G

    @classmethod
    def build_course_network(cls, students):
        """
        Build a graph where courses are nodes and edges connect
        courses that share students (excluding SOCI 101).

        Edge weight = number of shared students.
        """
        G = nx.Graph()

        # Build course enrollment counts
        course_enrollment = defaultdict(int)
        for student in students:
            for course in student['courses']:
                if course != cls.EXCLUDED_COURSE:
                    course_enrollment[course] += 1

        # Add courses as nodes
        for course, count in course_enrollment.items():
            G.add_node(course, enrollment=count)

        # Build student -> courses mapping (excluding SOCI 101)
        student_courses = {}
        for student in students:
            filtered = [c for c in student['courses'] if c != cls.EXCLUDED_COURSE]
            if filtered:
                student_courses[student['id']] = filtered

        # Create edges between courses that share students
        edge_weights = defaultdict(int)
        for student_id, courses in student_courses.items():
            for i in range(len(courses)):
                for j in range(i + 1, len(courses)):
                    c1, c2 = sorted([courses[i], courses[j]])
                    edge_weights[(c1, c2)] += 1

        # Add weighted edges
        for (c1, c2), weight in edge_weights.items():
            G.add_edge(c1, c2, weight=weight)

        return G

    @classmethod
    def calculate_centralities(cls, G):
        """
        Calculate betweenness, closeness, eigenvector centrality, and avg separation.

        Returns dict with node -> {betweenness, closeness, eigenvector, avg_separation}
        """
        if len(G.nodes()) == 0:
            return {}

        result = {}

        # Betweenness centrality
        betweenness = nx.betweenness_centrality(G, weight='weight')

        # Closeness centrality
        closeness = nx.closeness_centrality(G)

        # Eigenvector centrality (may fail on disconnected graphs)
        try:
            eigenvector = nx.eigenvector_centrality(G, max_iter=1000, weight='weight')
        except nx.PowerIterationFailedConvergence:
            eigenvector = {node: 0.0 for node in G.nodes()}

        # Average degrees of separation (average shortest path length from each node)
        avg_separation = {}
        for node in G.nodes():
            try:
                path_lengths = nx.single_source_shortest_path_length(G, node)
                # Exclude self (distance 0)
                distances = [d for n, d in path_lengths.items() if n != node]
                if distances:
                    avg_separation[node] = sum(distances) / len(distances)
                else:
                    avg_separation[node] = 0.0
            except nx.NetworkXError:
                avg_separation[node] = 0.0

        for node in G.nodes():
            result[node] = {
                'betweenness': round(betweenness.get(node, 0), 4),
                'closeness': round(closeness.get(node, 0), 4),
                'eigenvector': round(eigenvector.get(node, 0), 4),
                'avg_separation': round(avg_separation.get(node, 0), 2)
            }

        return result

    @classmethod
    def get_network_stats(cls, students):
        """Calculate overall network statistics."""
        student_graph = cls.build_student_network(students)
        course_graph = cls.build_course_network(students)

        # Basic counts
        total_students = len(students)
        all_courses = set()
        for student in students:
            all_courses.update(student['courses'])
        total_courses = len(all_courses)

        # Average courses per student
        if total_students > 0:
            avg_courses = sum(len(s['courses']) for s in students) / total_students
        else:
            avg_courses = 0

        # Network density (excluding SOCI 101 connections)
        if len(student_graph.nodes()) > 1:
            density = nx.density(student_graph)
        else:
            density = 0

        return {
            'total_students': total_students,
            'total_courses': total_courses,
            'avg_courses_per_student': round(avg_courses, 2),
            'network_density': round(density, 4),
            'student_edges': student_graph.number_of_edges(),
            'course_edges': course_graph.number_of_edges()
        }

    @classmethod
    def get_student_network_d3(cls, students, min_edge_weight=2):
        """
        Get student network in D3.js force-directed graph format.

        Filters edges to only show connections with weight >= min_edge_weight
        to improve rendering performance.

        Returns: {nodes: [{id, course_count}], links: [{source, target, weight}]}
        """
        G = cls.build_student_network(students)

        # Filter to only show stronger connections for performance
        links = []
        connected_nodes = set()
        for u, v, data in G.edges(data=True):
            weight = data.get('weight', 1)
            if weight >= min_edge_weight:
                links.append({
                    'source': u,
                    'target': v,
                    'weight': weight
                })
                connected_nodes.add(u)
                connected_nodes.add(v)

        # Include all nodes (even if not connected at this threshold)
        nodes = []
        for node in G.nodes():
            nodes.append({
                'id': node,
                'course_count': G.nodes[node].get('course_count', 0)
            })

        return {'nodes': nodes, 'links': links}

    @classmethod
    def get_course_network_d3(cls, students, min_edge_weight=3):
        """
        Get course network in D3.js force-directed graph format.

        Filters edges to only show connections with weight >= min_edge_weight
        to improve rendering performance.

        Returns: {nodes: [{id, enrollment}], links: [{source, target, weight}]}
        """
        G = cls.build_course_network(students)

        # Filter to only show stronger connections for performance
        links = []
        for u, v, data in G.edges(data=True):
            weight = data.get('weight', 1)
            if weight >= min_edge_weight:
                links.append({
                    'source': u,
                    'target': v,
                    'weight': weight
                })

        # Include all nodes
        nodes = []
        for node in G.nodes():
            nodes.append({
                'id': node,
                'enrollment': G.nodes[node].get('enrollment', 0)
            })

        return {'nodes': nodes, 'links': links}

    @classmethod
    def get_full_stats(cls, students):
        """Get all statistics including centrality rankings."""
        stats = cls.get_network_stats(students)

        # Student centralities
        student_graph = cls.build_student_network(students)
        student_centralities = cls.calculate_centralities(student_graph)

        # Course centralities
        course_graph = cls.build_course_network(students)
        course_centralities = cls.calculate_centralities(course_graph)

        return {
            'overview': stats,
            'student_centralities': student_centralities,
            'course_centralities': course_centralities
        }
