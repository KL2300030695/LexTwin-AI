import { useMemo, useState } from 'react'
import dagre from 'dagre'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  MarkerType,
  type Edge,
  type Node,
} from 'reactflow'
import 'reactflow/dist/style.css'
import type { GraphAnalysis } from '../types/graph'
import type { RiskFlag } from '../lib/riskFlags'

const NODE_WIDTH = 340
const NODE_HEIGHT = 56
const REGION_PADDING = 40

/** Auto-layout via dagre instead of a manual two-column grid: node positions
 * are computed from the actual edge structure (minimizing crossings), rather
 * than a fixed column-per-document + row-per-index arrangement that ignored
 * where edges actually pointed. MSA vs SOW is still visually distinguished
 * by node background color (see COLORS below), just not by forcing them
 * into separate physical columns anymore. */
function layoutWithDagre(nodes: Node[], edges: Edge[]): Node[] {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'TB', nodesep: 40, ranksep: 90 })

  for (const node of nodes) {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT })
  }
  for (const edge of edges) {
    g.setEdge(edge.source, edge.target)
  }

  dagre.layout(g)

  return nodes.map((node) => {
    const { x, y } = g.node(node.id)
    // dagre positions are node centers; React Flow expects top-left.
    return { ...node, position: { x: x - NODE_WIDTH / 2, y: y - NODE_HEIGHT / 2 } }
  })
}

// Mirrors the design tokens in index.css -- React Flow renders nodes/edges via
// inline styles and raw SVG attributes, so Tailwind utility classes don't
// reach them; these are the same hex values kept in sync by hand.
const COLORS = {
  sealBlueTint: '#e8edf5',
  sealBlue: '#2e4e82',
  clayTint: '#f3e9e0',
  clay: '#96603a',
  redline: '#9c2b37',
  redlineTint: 'rgba(156, 43, 55, 0.08)',
  seal: '#1f6f5c',
  sealAmber: '#b07c25',
  ledger: '#dce0e8',
  slateBody: '#4a5268',
  ink: '#151a2d',
}

const REGION_MSA_ID = '__region_msa__'
const REGION_SOW_ID = '__region_sow__'

// Stable, module-level references -- we use only React Flow's default node/edge
// rendering (no custom types), but passing a fresh {} object as nodeTypes/
// edgeTypes on every render still trips React Flow's "new nodeTypes or
// edgeTypes object" warning (reactflow.dev/error#002). Defining them once
// here, outside the component, keeps the reference stable across renders.
const NODE_TYPES = {}
const EDGE_TYPES = {}

function naturalSectionKey(section: string): (number | string)[] {
  return section.split('.').map((part) => {
    const n = Number(part)
    return Number.isNaN(n) ? part : n
  })
}

function compareSections(a: string, b: string): number {
  const ka = naturalSectionKey(a)
  const kb = naturalSectionKey(b)
  const len = Math.max(ka.length, kb.length)
  for (let i = 0; i < len; i++) {
    const av = ka[i]
    const bv = kb[i]
    if (av === undefined) return -1
    if (bv === undefined) return 1
    if (av === bv) continue
    if (typeof av === 'number' && typeof bv === 'number') return av - bv
    return String(av).localeCompare(String(bv))
  }
  return 0
}

function edgeKey(source: string, target: string): string {
  return `${source}->${target}`
}

/** Computes a padded bounding-box background node for a cluster of laid-out
 * nodes, rendered behind the real nodes so MSA vs SOW remain visually
 * grouped even though dagre's free-form layout no longer forces them into
 * strict columns. Stacking is via array order (these are placed first in
 * the nodes[] array, so they paint before -- i.e. behind -- the real clause
 * nodes), deliberately NOT via a negative zIndex: a negative z-index inside
 * React Flow's nested stacking contexts can escape further than intended
 * and render behind an ancestor's own background instead, making the node
 * invisible against the white canvas -- verified this was actually
 * happening (regions were completely invisible with zIndex: -1 set). */
function buildRegionNode(id: string, label: string, tint: string, borderColor: string, members: Node[]): Node | null {
  if (members.length === 0) return null
  const minX = Math.min(...members.map((n) => n.position.x))
  const minY = Math.min(...members.map((n) => n.position.y))
  const maxX = Math.max(...members.map((n) => n.position.x + NODE_WIDTH))
  const maxY = Math.max(...members.map((n) => n.position.y + NODE_HEIGHT))
  const width = maxX - minX + REGION_PADDING * 2
  const height = maxY - minY + REGION_PADDING * 2 + 24
  return {
    id,
    position: { x: minX - REGION_PADDING, y: minY - REGION_PADDING - 24 },
    data: { label },
    draggable: false,
    selectable: false,
    connectable: false,
    // Top-level width/height (distinct from style.width/height) so React
    // Flow's fitView can account for this node's true size in its bounds
    // calculation immediately, before the DOM has actually measured it via
    // ResizeObserver -- without these, fitView could compute bounds from a
    // stale/default size on first render and clip part of the graph.
    width,
    height,
    style: {
      width,
      height,
      background: tint,
      border: `2px dashed ${borderColor}`,
      borderRadius: 10,
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'flex-start',
      padding: 8,
      fontFamily: '"IBM Plex Mono", ui-monospace, monospace',
      fontSize: 12,
      fontWeight: 700,
      letterSpacing: '0.06em',
      color: borderColor,
      pointerEvents: 'none',
    },
  }
}

interface EdgeFilters {
  reference: boolean
  override: boolean
  cycleOnly: boolean
}

export default function DependencyGraph({
  graph,
  msaDocId,
  sowDocId,
  selectedFlag,
  onSelectClause,
}: {
  graph: GraphAnalysis
  msaDocId: string
  sowDocId: string
  /** When the selected Risk Flag is a circular_reference / override_conflict,
   * its exact cycle is highlighted distinctly from other flagged-but-unselected
   * cycles elsewhere in the graph. */
  selectedFlag?: RiskFlag | null
  onSelectClause?: (clauseId: string) => void
}) {
  const [edgeFilters, setEdgeFilters] = useState<EdgeFilters>({ reference: true, override: true, cycleOnly: true })

  const flaggedNodeIds = useMemo(() => {
    const ids = new Set<string>()
    for (const group of graph.circular_references) {
      for (const id of group.clause_ids) ids.add(id)
    }
    return ids
  }, [graph])

  const cycleEdgeKeys = useMemo(() => {
    const keys = new Set<string>()
    for (const group of graph.circular_references) {
      for (const e of group.edges) keys.add(edgeKey(e.source, e.target))
    }
    return keys
  }, [graph])

  const isCycleFlagSelected = selectedFlag?.kind === 'circular_reference' || selectedFlag?.kind === 'override_conflict'
  const selectedNodeIds = useMemo(
    () => (isCycleFlagSelected ? new Set(selectedFlag!.clauseIds) : new Set<string>()),
    [isCycleFlagSelected, selectedFlag],
  )
  const selectedEdgeKeys = useMemo(() => {
    if (!isCycleFlagSelected || !selectedFlag?.cycleEdges) return new Set<string>()
    return new Set(selectedFlag.cycleEdges.map((e) => edgeKey(e.source, e.target)))
  }, [isCycleFlagSelected, selectedFlag])
  const hasActiveSelection = selectedNodeIds.size > 0

  const { nodes, edges } = useMemo(() => {
    const msaNodes = graph.nodes.filter((n) => n.doc_id === msaDocId).sort((a, b) => compareSections(a.section_number, b.section_number))
    const sowNodes = graph.nodes.filter((n) => n.doc_id === sowDocId).sort((a, b) => compareSections(a.section_number, b.section_number))

    const unpositionedNodes: Node[] = [...msaNodes, ...sowNodes].map((n) => {
      const isSelected = selectedNodeIds.has(n.id)
      const isFlagged = flaggedNodeIds.has(n.id)
      let border = `1px solid ${COLORS.ledger}`
      if (isSelected) {
        border = `3px solid ${COLORS.seal}`
      } else if (isFlagged) {
        border = hasActiveSelection ? `2px solid ${COLORS.redline}66` : `2px solid ${COLORS.redline}`
      }
      return {
        id: n.id,
        position: { x: 0, y: 0 }, // overwritten by layoutWithDagre below
        data: { label: `${n.section_number} ${n.heading ?? ''}`.trim() },
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
        style: {
          width: NODE_WIDTH,
          fontSize: 12,
          fontFamily: '"IBM Plex Mono", ui-monospace, monospace',
          padding: 10,
          borderRadius: 4,
          border,
          boxShadow: isSelected ? `0 0 0 3px ${COLORS.redlineTint}` : undefined,
          background: n.doc_id === msaDocId ? COLORS.sealBlueTint : COLORS.clayTint,
          color: COLORS.ink,
        },
      }
    })

    // dagre lays out from the FULL edge set (best positions regardless of
    // what's currently toggled visible); the edge-type filter below only
    // decides which edges are actually rendered, not repositioned.
    const allFlowEdges: Edge[] = graph.edges.map((e, i) => {
      const isOverride = e.kind === 'notwithstanding_override'
      const isSelectedEdge = selectedEdgeKeys.has(edgeKey(e.source, e.target))
      const dim = hasActiveSelection && !isSelectedEdge
      const stroke = isSelectedEdge ? COLORS.seal : isOverride ? COLORS.sealAmber : COLORS.slateBody
      return {
        id: `${e.source}->${e.target}-${i}`,
        source: e.source,
        target: e.target,
        label: isOverride ? 'overrides' : undefined,
        labelStyle: { fontFamily: '"IBM Plex Mono", ui-monospace, monospace', fontSize: 10, fill: COLORS.sealAmber, fontWeight: 600 },
        animated: isOverride || isSelectedEdge,
        style: {
          stroke,
          strokeWidth: isSelectedEdge ? 3 : 1.5,
          strokeDasharray: isOverride || isSelectedEdge ? undefined : '4 3',
          opacity: dim ? 0.25 : 1,
        },
        markerEnd: { type: MarkerType.ArrowClosed, color: stroke },
      }
    })

    const visibleEdges = allFlowEdges.filter((_, i) => {
      const e = graph.edges[i]
      const isCycleEdge = cycleEdgeKeys.has(edgeKey(e.source, e.target))
      return (
        (e.kind === 'reference' && edgeFilters.reference) ||
        (e.kind === 'notwithstanding_override' && edgeFilters.override) ||
        (isCycleEdge && edgeFilters.cycleOnly)
      )
    })

    // Laid out as two SEPARATE dagre passes (MSA's own cross-references,
    // then SOW's own), stacked MSA-above-SOW, rather than one shared dagre
    // pass -- a single pass let cross-document edges freely interleave MSA
    // and SOW nodes into whatever rank the edge structure implied, which
    // read as visually inconsistent/scattered rather than as two documents.
    // Cross-document edges (the ones that actually matter for spotting a
    // contradiction) still render correctly afterward, as longer lines
    // connecting the two bands.
    const msaNodeIds = new Set(msaNodes.map((n) => n.id))
    const sowNodeIds = new Set(sowNodes.map((n) => n.id))
    const msaUnpositioned = unpositionedNodes.filter((n) => msaNodeIds.has(n.id))
    const sowUnpositioned = unpositionedNodes.filter((n) => sowNodeIds.has(n.id))
    const msaInternalEdges = allFlowEdges.filter((e) => msaNodeIds.has(e.source) && msaNodeIds.has(e.target))
    const sowInternalEdges = allFlowEdges.filter((e) => sowNodeIds.has(e.source) && sowNodeIds.has(e.target))

    const msaLaidOut = layoutWithDagre(msaUnpositioned, msaInternalEdges)
    const sowLaidOutRaw = layoutWithDagre(sowUnpositioned, sowInternalEdges)

    const STACK_GAP = 140
    const msaMaxY = msaLaidOut.length > 0 ? Math.max(...msaLaidOut.map((n) => n.position.y + NODE_HEIGHT)) : 0
    const sowLaidOut = sowLaidOutRaw.map((n) => ({
      ...n,
      position: { x: n.position.x, y: n.position.y + msaMaxY + STACK_GAP },
    }))

    const laidOutNodes = [...msaLaidOut, ...sowLaidOut]

    const regionMsa = buildRegionNode(REGION_MSA_ID, 'MSA', 'rgba(46, 78, 130, 0.1)', COLORS.sealBlue, msaLaidOut)
    const regionSow = buildRegionNode(REGION_SOW_ID, 'SOW', 'rgba(150, 96, 58, 0.1)', COLORS.clay, sowLaidOut)
    const regionNodes = [regionMsa, regionSow].filter((n): n is Node => n !== null)

    return { nodes: [...regionNodes, ...laidOutNodes], edges: visibleEdges }
  }, [graph, msaDocId, sowDocId, flaggedNodeIds, cycleEdgeKeys, selectedNodeIds, selectedEdgeKeys, hasActiveSelection, edgeFilters])

  return (
    <div className="space-y-2.5">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 font-mono text-[11px] text-slate-body">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm border" style={{ background: COLORS.sealBlueTint, borderColor: COLORS.sealBlue }} />
          MSA clause
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm border" style={{ background: COLORS.clayTint, borderColor: COLORS.clay }} />
          SOW clause
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm border-2" style={{ borderColor: COLORS.redline }} />
          circular / conflicting
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-px w-4" style={{ borderTop: `1.5px solid ${COLORS.sealAmber}` }} />
          notwithstanding override
        </span>
        {hasActiveSelection && (
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm border-2" style={{ borderColor: COLORS.seal }} />
            selected cycle
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[11px] text-slate-body">
        <span className="text-slate-body/70">Show:</span>
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input
            type="checkbox"
            checked={edgeFilters.reference}
            onChange={(e) => setEdgeFilters((f) => ({ ...f, reference: e.target.checked }))}
          />
          references
        </label>
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input
            type="checkbox"
            checked={edgeFilters.override}
            onChange={(e) => setEdgeFilters((f) => ({ ...f, override: e.target.checked }))}
          />
          overrides
        </label>
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input
            type="checkbox"
            checked={edgeFilters.cycleOnly}
            onChange={(e) => setEdgeFilters((f) => ({ ...f, cycleOnly: e.target.checked }))}
          />
          flagged / cycle edges
        </label>
      </div>

      <div className="h-[70vh] w-full overflow-hidden rounded-md border border-ledger bg-white">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={NODE_TYPES}
          edgeTypes={EDGE_TYPES}
          fitView
          onNodeClick={(_, node) => {
            if (node.id === REGION_MSA_ID || node.id === REGION_SOW_ID) return
            onSelectClause?.(node.id)
          }}
          nodesDraggable
          nodesConnectable={false}
          elementsSelectable
        >
          <Background color={COLORS.ledger} gap={16} size={1} />
          <Controls />
          <MiniMap
            pannable
            zoomable
            nodeColor={(n) => {
              if (n.id === REGION_MSA_ID || n.id === REGION_SOW_ID) return 'transparent'
              return n.id.startsWith(msaDocId) ? COLORS.sealBlue : COLORS.clay
            }}
            maskColor="rgba(245, 246, 248, 0.7)"
          />
        </ReactFlow>
      </div>
    </div>
  )
}
