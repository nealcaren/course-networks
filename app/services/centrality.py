"""Pure Python graph algorithms - no external dependencies."""

from collections import defaultdict, deque


class SimpleGraph:
    """Lightweight undirected weighted graph using adjacency lists."""

    def __init__(self):
        self.adj = defaultdict(dict)  # node -> {neighbor: weight}
        self.node_attrs = {}  # node -> {attr: value}

    def add_node(self, node, **attrs):
        if node not in self.adj:
            self.adj[node] = {}
        self.node_attrs[node] = attrs

    def add_edge(self, u, v, weight=1):
        self.adj[u][v] = weight
        self.adj[v][u] = weight
        # Ensure nodes exist
        if u not in self.node_attrs:
            self.node_attrs[u] = {}
        if v not in self.node_attrs:
            self.node_attrs[v] = {}

    def nodes(self):
        return list(self.adj.keys())

    def edges(self):
        seen = set()
        for u in self.adj:
            for v, w in self.adj[u].items():
                if (v, u) not in seen:
                    seen.add((u, v))
                    yield u, v, w

    def neighbors(self, node):
        return self.adj.get(node, {})

    def get_node_attr(self, node, attr, default=0):
        return self.node_attrs.get(node, {}).get(attr, default)

    def num_nodes(self):
        return len(self.adj)

    def num_edges(self):
        return sum(len(neighbors) for neighbors in self.adj.values()) // 2


def bfs_shortest_paths(graph, source):
    """BFS to find shortest path distances from source to all reachable nodes."""
    distances = {source: 0}
    queue = deque([source])

    while queue:
        node = queue.popleft()
        for neighbor in graph.neighbors(node):
            if neighbor not in distances:
                distances[neighbor] = distances[node] + 1
                queue.append(neighbor)

    return distances


def betweenness_centrality(graph):
    """
    Brandes algorithm for betweenness centrality.
    Simplified version that treats all edges as unweighted.
    """
    nodes = graph.nodes()
    betweenness = {node: 0.0 for node in nodes}

    for source in nodes:
        # BFS from source
        stack = []
        predecessors = {node: [] for node in nodes}
        sigma = {node: 0.0 for node in nodes}
        sigma[source] = 1.0
        dist = {node: -1 for node in nodes}
        dist[source] = 0

        queue = deque([source])
        while queue:
            v = queue.popleft()
            stack.append(v)
            for w in graph.neighbors(v):
                # First visit?
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    queue.append(w)
                # Shortest path to w via v?
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    predecessors[w].append(v)

        # Accumulation
        delta = {node: 0.0 for node in nodes}
        while stack:
            w = stack.pop()
            for v in predecessors[w]:
                delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
            if w != source:
                betweenness[w] += delta[w]

    # Normalize (undirected graph)
    n = len(nodes)
    if n > 2:
        norm = 2.0 / ((n - 1) * (n - 2))
        for node in betweenness:
            betweenness[node] *= norm

    return betweenness


def closeness_centrality(graph):
    """Closeness centrality based on shortest path distances."""
    nodes = graph.nodes()
    closeness = {}

    for node in nodes:
        distances = bfs_shortest_paths(graph, node)
        reachable = [d for n, d in distances.items() if n != node and d > 0]

        if reachable:
            avg_dist = sum(reachable) / len(reachable)
            closeness[node] = 1.0 / avg_dist if avg_dist > 0 else 0.0
        else:
            closeness[node] = 0.0

    return closeness


def eigenvector_centrality(graph, max_iter=100, tol=1e-6):
    """Power iteration method for eigenvector centrality."""
    nodes = graph.nodes()
    n = len(nodes)
    if n == 0:
        return {}

    # Initialize with uniform values
    centrality = {node: 1.0 / n for node in nodes}

    for _ in range(max_iter):
        prev = centrality.copy()

        # Power iteration step
        for node in nodes:
            centrality[node] = sum(
                prev.get(neighbor, 0) * weight
                for neighbor, weight in graph.neighbors(node).items()
            )

        # Normalize
        norm = sum(v * v for v in centrality.values()) ** 0.5
        if norm > 0:
            for node in nodes:
                centrality[node] /= norm

        # Check convergence
        diff = sum(abs(centrality[n] - prev[n]) for n in nodes)
        if diff < tol:
            break

    return centrality


def average_separation(graph):
    """Average shortest path length from each node to all reachable nodes."""
    avg_sep = {}

    for node in graph.nodes():
        distances = bfs_shortest_paths(graph, node)
        reachable = [d for n, d in distances.items() if n != node]

        if reachable:
            avg_sep[node] = sum(reachable) / len(reachable)
        else:
            avg_sep[node] = 0.0

    return avg_sep


class CentralityService:
    """Graph-based centrality calculations for student and course networks."""

    EXCLUDED_COURSE = "SOCI 101"

    @classmethod
    def build_student_network(cls, students):
        """
        Build a graph where students are nodes and edges connect
        students who share courses (excluding SOCI 101).
        """
        G = SimpleGraph()

        # Add all students as nodes
        for student in students:
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
        """
        G = SimpleGraph()

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
        """
        if G.num_nodes() == 0:
            return {}

        result = {}

        bc = betweenness_centrality(G)
        cc = closeness_centrality(G)
        ec = eigenvector_centrality(G)
        avg_sep = average_separation(G)

        for node in G.nodes():
            result[node] = {
                'betweenness': round(bc.get(node, 0), 4),
                'closeness': round(cc.get(node, 0), 4),
                'eigenvector': round(ec.get(node, 0), 4),
                'avg_separation': round(avg_sep.get(node, 0), 2)
            }

        return result

    @classmethod
    def get_network_stats(cls, students):
        """Calculate overall network statistics."""
        student_graph = cls.build_student_network(students)
        course_graph = cls.build_course_network(students)

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

        # Network density
        n = student_graph.num_nodes()
        e = student_graph.num_edges()
        if n > 1:
            max_edges = n * (n - 1) / 2
            density = e / max_edges if max_edges > 0 else 0
        else:
            density = 0

        return {
            'total_students': total_students,
            'total_courses': total_courses,
            'avg_courses_per_student': round(avg_courses, 2),
            'network_density': round(density, 4),
            'student_edges': student_graph.num_edges(),
            'course_edges': course_graph.num_edges()
        }

    @classmethod
    def get_student_network_d3(cls, students, min_edge_weight=2):
        """Get student network in D3.js format with edge filtering."""
        G = cls.build_student_network(students)

        links = []
        for u, v, weight in G.edges():
            if weight >= min_edge_weight:
                links.append({'source': u, 'target': v, 'weight': weight})

        nodes = []
        for node in G.nodes():
            nodes.append({
                'id': node,
                'course_count': G.get_node_attr(node, 'course_count', 0)
            })

        return {'nodes': nodes, 'links': links}

    @classmethod
    def get_course_network_d3(cls, students, min_edge_weight=3):
        """Get course network in D3.js format with edge filtering."""
        G = cls.build_course_network(students)

        links = []
        for u, v, weight in G.edges():
            if weight >= min_edge_weight:
                links.append({'source': u, 'target': v, 'weight': weight})

        nodes = []
        for node in G.nodes():
            nodes.append({
                'id': node,
                'enrollment': G.get_node_attr(node, 'enrollment', 0)
            })

        return {'nodes': nodes, 'links': links}

    @classmethod
    def get_full_stats(cls, students):
        """Get all statistics including centrality rankings."""
        stats = cls.get_network_stats(students)
        student_graph = cls.build_student_network(students)
        student_centralities = cls.calculate_centralities(student_graph)
        course_graph = cls.build_course_network(students)
        course_centralities = cls.calculate_centralities(course_graph)

        return {
            'overview': stats,
            'student_centralities': student_centralities,
            'course_centralities': course_centralities
        }
