// Student network D3.js visualization

let simulation = null;
let svg = null;
let g = null;
let zoom = null;
let lastUpdated = null;
const POLL_INTERVAL = 5000;

let currentHighlight = null;
let allNodes = [];
let allLinks = [];

document.addEventListener('DOMContentLoaded', function() {
    initializeGraph();
    fetchNetworkData();
    setInterval(checkForUpdates, POLL_INTERVAL);

    document.getElementById('reset-zoom').addEventListener('click', resetZoom);
    document.getElementById('search-btn').addEventListener('click', searchNode);
    document.getElementById('clear-search').addEventListener('click', clearSearch);
    document.getElementById('node-search').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') searchNode();
    });
});

function initializeGraph() {
    const container = document.getElementById('network-graph');
    const width = container.clientWidth;
    const height = container.clientHeight || 500;

    // Clear loading message
    container.innerHTML = '';

    svg = d3.select('#network-graph')
        .append('svg')
        .attr('width', '100%')
        .attr('height', '100%')
        .attr('viewBox', [0, 0, width, height]);

    // Add zoom behavior
    zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        });

    svg.call(zoom);

    // Create container group for zoom/pan
    g = svg.append('g');

    // Initialize simulation
    simulation = d3.forceSimulation()
        .force('link', d3.forceLink().id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(30));
}

function updateStatusIndicator(isLive) {
    const dot = document.querySelector('.status-dot');
    const text = document.getElementById('status-text');
    if (isLive) {
        dot.classList.add('live');
        text.textContent = 'Live';
    } else {
        dot.classList.remove('live');
        text.textContent = 'Updating...';
    }
}

async function fetchNetworkData() {
    updateStatusIndicator(false);

    try {
        const response = await fetch('/api/network/students');
        const data = await response.json();
        updateGraph(data);
        updateStatusIndicator(true);
    } catch (error) {
        console.error('Error fetching network data:', error);
        updateStatusIndicator(false);
    }
}

async function checkForUpdates() {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();

        if (lastUpdated !== status.last_updated) {
            lastUpdated = status.last_updated;
            await fetchNetworkData();
        }
    } catch (error) {
        console.error('Error checking status:', error);
    }
}

function updateGraph(data) {
    const { nodes, links } = data;

    // Store for search functionality
    allNodes = nodes;
    allLinks = links;

    // Handle empty data
    if (nodes.length === 0) {
        g.selectAll('*').remove();
        g.append('text')
            .attr('x', svg.attr('viewBox').split(' ')[2] / 2)
            .attr('y', svg.attr('viewBox').split(' ')[3] / 2)
            .attr('text-anchor', 'middle')
            .attr('class', 'empty-message')
            .text('No students registered yet');
        return;
    }

    // Node size scale based on course count
    const nodeSizeScale = d3.scaleLinear()
        .domain([0, d3.max(nodes, d => d.course_count) || 1])
        .range([8, 25]);

    // Edge thickness scale based on weight
    const edgeScale = d3.scaleLinear()
        .domain([1, d3.max(links, d => d.weight) || 1])
        .range([1, 6]);

    // Color scale for nodes - light pastels for readability
    const colorScale = d3.scaleLinear()
        .domain([0, d3.max(nodes, d => d.course_count) || 1])
        .range(['#bfdbfe', '#60a5fa']);  // Light blue to medium blue

    // DATA JOIN for links
    const link = g.selectAll('.link')
        .data(links, d => `${d.source.id || d.source}-${d.target.id || d.target}`);

    // EXIT old links
    link.exit().remove();

    // ENTER new links
    const linkEnter = link.enter()
        .append('line')
        .attr('class', 'link')
        .attr('stroke', '#999')
        .attr('stroke-opacity', 0.6);

    // UPDATE all links
    const linkMerge = linkEnter.merge(link)
        .attr('stroke-width', d => edgeScale(d.weight));

    // DATA JOIN for nodes
    const node = g.selectAll('.node')
        .data(nodes, d => d.id);

    // EXIT old nodes
    node.exit().remove();

    // ENTER new nodes
    const nodeEnter = node.enter()
        .append('g')
        .attr('class', 'node')
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag', dragged)
            .on('end', dragEnded));

    nodeEnter.append('circle')
        .attr('stroke', '#1e40af')
        .attr('stroke-width', 2);

    nodeEnter.append('text')
        .attr('dy', '.35em')
        .attr('text-anchor', 'middle')
        .attr('class', 'node-label');

    // Add tooltip
    nodeEnter.append('title');

    // UPDATE all nodes
    const nodeMerge = nodeEnter.merge(node);

    nodeMerge.select('circle')
        .attr('r', d => nodeSizeScale(d.course_count))
        .attr('fill', d => colorScale(d.course_count));

    nodeMerge.select('text')
        .text(d => d.id);

    nodeMerge.select('title')
        .text(d => `${d.id}\nCourses: ${d.course_count}`);

    // Update simulation
    simulation.nodes(nodes);
    simulation.force('link').links(links);
    simulation.alpha(0.3).restart();

    // Tick function
    simulation.on('tick', () => {
        linkMerge
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        nodeMerge.attr('transform', d => `translate(${d.x},${d.y})`);
    });
}

function dragStarted(event) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    event.subject.fx = event.subject.x;
    event.subject.fy = event.subject.y;
}

function dragged(event) {
    event.subject.fx = event.x;
    event.subject.fy = event.y;
}

function dragEnded(event) {
    if (!event.active) simulation.alphaTarget(0);
    event.subject.fx = null;
    event.subject.fy = null;
}

function resetZoom() {
    svg.transition().duration(500).call(
        zoom.transform,
        d3.zoomIdentity
    );
}

function searchNode() {
    const searchTerm = document.getElementById('node-search').value.trim().toUpperCase();
    if (!searchTerm) return;

    // Get simulation nodes which have x,y coordinates
    const simNodes = simulation.nodes();
    const foundNode = simNodes.find(n => n.id.toUpperCase() === searchTerm);

    // Remove any existing message and info panel
    const existingMsg = document.querySelector('.search-message');
    if (existingMsg) existingMsg.remove();
    const existingPanel = document.querySelector('.node-info-panel');
    if (existingPanel) existingPanel.remove();

    const searchBox = document.querySelector('.search-box');
    const msg = document.createElement('span');
    msg.className = 'search-message';

    if (foundNode) {
        msg.textContent = `Found ${foundNode.id}!`;
        msg.classList.add('found');
        highlightNode(foundNode);
        centerOnNode(foundNode);
        showNodeInfo(foundNode);
    } else {
        msg.textContent = `"${searchTerm}" not found`;
        msg.classList.add('not-found');
    }

    searchBox.appendChild(msg);
}

async function showNodeInfo(node) {
    // Remove existing panel
    const existingPanel = document.querySelector('.node-info-panel');
    if (existingPanel) existingPanel.remove();

    const container = document.querySelector('.network-container');
    const panel = document.createElement('div');
    panel.className = 'node-info-panel';

    let html = `<h4>${node.id}</h4>`;
    html += `<div class="info-row"><span>Courses:</span> <strong>${node.course_count}</strong></div>`;
    html += `<div class="info-row loading-metrics"><em>Loading metrics...</em></div>`;

    panel.innerHTML = html;
    container.appendChild(panel);

    // Fetch centrality data on demand
    try {
        const response = await fetch(`/api/centrality/student/${node.id}`);
        const data = await response.json();

        if (data.centrality) {
            const c = data.centrality;
            const metricsHtml = `
                <div class="info-row"><span>Degrees of Separation:</span> <strong>${c.avg_separation.toFixed(2)}</strong></div>
                <div class="info-row"><span>Betweenness (bridge score):</span> <strong>${c.betweenness.toFixed(3)}</strong></div>
                <div class="info-row"><span>Closeness:</span> <strong>${c.closeness.toFixed(3)}</strong></div>
                <div class="info-row"><span>Eigenvector:</span> <strong>${c.eigenvector.toFixed(3)}</strong></div>
            `;
            const loadingEl = panel.querySelector('.loading-metrics');
            if (loadingEl) {
                loadingEl.outerHTML = metricsHtml;
            }
        }
    } catch (error) {
        console.error('Error fetching centrality:', error);
        const loadingEl = panel.querySelector('.loading-metrics');
        if (loadingEl) {
            loadingEl.innerHTML = '<em>Could not load metrics</em>';
        }
    }
}

function highlightNode(targetNode) {
    currentHighlight = targetNode.id;

    // Find connected nodes using simulation's force links
    const connectedIds = new Set([targetNode.id]);
    const simLinks = simulation.force('link').links();
    simLinks.forEach(link => {
        const sourceId = link.source.id || link.source;
        const targetId = link.target.id || link.target;
        if (sourceId === targetNode.id) connectedIds.add(targetId);
        if (targetId === targetNode.id) connectedIds.add(sourceId);
    });

    // Dim non-connected nodes
    g.selectAll('.node')
        .transition()
        .duration(300)
        .style('opacity', d => connectedIds.has(d.id) ? 1 : 0.2);

    // Highlight the target node
    g.selectAll('.node')
        .filter(d => d.id === targetNode.id)
        .select('circle')
        .transition()
        .duration(300)
        .attr('stroke', '#f59e0b')
        .attr('stroke-width', 4);

    // Dim non-connected links
    g.selectAll('.link')
        .transition()
        .duration(300)
        .style('opacity', d => {
            const sourceId = d.source.id || d.source;
            const targetId = d.target.id || d.target;
            return (sourceId === targetNode.id || targetId === targetNode.id) ? 1 : 0.1;
        });
}

function centerOnNode(node) {
    // Wait for simulation to have valid positions
    if (isNaN(node.x) || isNaN(node.y)) {
        setTimeout(() => centerOnNode(node), 100);
        return;
    }

    const viewBox = svg.attr('viewBox').split(' ').map(Number);
    const width = viewBox[2];
    const height = viewBox[3];

    const scale = 1.5;
    const x = width / 2 - node.x * scale;
    const y = height / 2 - node.y * scale;

    svg.transition()
        .duration(500)
        .call(zoom.transform, d3.zoomIdentity.translate(x, y).scale(scale));
}

function clearSearch() {
    currentHighlight = null;
    document.getElementById('node-search').value = '';

    // Remove message and info panel
    const msg = document.querySelector('.search-message');
    if (msg) msg.remove();
    const panel = document.querySelector('.node-info-panel');
    if (panel) panel.remove();

    // Restore all nodes and links
    g.selectAll('.node')
        .transition()
        .duration(300)
        .style('opacity', 1);

    g.selectAll('.node')
        .select('circle')
        .transition()
        .duration(300)
        .attr('stroke', '#1e40af')
        .attr('stroke-width', 2);

    g.selectAll('.link')
        .transition()
        .duration(300)
        .style('opacity', 0.6);

    resetZoom();
}
