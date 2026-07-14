import { useMemo } from 'react'
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

// Mirrors the design tokens in index.css -- React Flow renders nodes/edges via
// inline styles and raw SVG attributes, so Tailwind utility classes don't
// reach them; these are the same hex values kept in sync by hand.
const COLORS = {
  sealBlueTint: '#e8edf5',
  sealBlue: '#2e4e82',
  clayTint: '#f3e9e0',
  clay: '#96603a',
  redline: '#9c2b37',
  sealAmber: '#b07c25',
  ledger: '#dce0e8',
  slateBody: '#4a5268',
  ink: '#151a2d',
}

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

export default function DependencyGraph({
  graph,
  msaDocId,
  sowDocId,
  onSelectClause,
}: {
  graph: GraphAnalysis
  msaDocId: string
  sowDocId: string
  onSelectClause?: (clauseId: string) => void
}) {
  const flaggedNodeIds = useMemo(() => {
    const ids = new Set<string>()
    for (const group of graph.circular_references) {
      for (const id of group.clause_ids) ids.add(id)
    }
    return ids
  }, [graph])

  const { nodes, edges } = useMemo(() => {
    const msaNodes = graph.nodes.filter((n) => n.doc_id === msaDocId).sort((a, b) => compareSections(a.section_number, b.section_number))
    const sowNodes = graph.nodes.filter((n) => n.doc_id === sowDocId).sort((a, b) => compareSections(a.section_number, b.section_number))

    const columnX: Record<string, number> = { [msaDocId]: 60, [sowDocId]: 480 }
    const rowHeight = 70

    const flowNodes: Node[] = [...msaNodes, ...sowNodes].map((n) => {
      const columnNodes = n.doc_id === msaDocId ? msaNodes : sowNodes
      const index = columnNodes.findIndex((c) => c.id === n.id)
      const isFlagged = flaggedNodeIds.has(n.id)
      return {
        id: n.id,
        position: { x: columnX[n.doc_id] ?? 60, y: index * rowHeight + 20 },
        data: { label: `${n.section_number} ${n.heading ?? ''}`.trim() },
        style: {
          width: 340,
          fontSize: 12,
          fontFamily: '"IBM Plex Mono", ui-monospace, monospace',
          padding: 10,
          borderRadius: 4,
          border: isFlagged ? `2px solid ${COLORS.redline}` : `1px solid ${COLORS.ledger}`,
          background: n.doc_id === msaDocId ? COLORS.sealBlueTint : COLORS.clayTint,
          color: COLORS.ink,
        },
      }
    })

    const flowEdges: Edge[] = graph.edges.map((e, i) => {
      const isOverride = e.kind === 'notwithstanding_override'
      return {
        id: `${e.source}->${e.target}-${i}`,
        source: e.source,
        target: e.target,
        label: isOverride ? 'overrides' : undefined,
        labelStyle: { fontFamily: '"IBM Plex Mono", ui-monospace, monospace', fontSize: 10, fill: COLORS.sealAmber, fontWeight: 600 },
        animated: isOverride,
        style: {
          stroke: isOverride ? COLORS.sealAmber : COLORS.slateBody,
          strokeWidth: 1.5,
          strokeDasharray: isOverride ? undefined : '4 3',
        },
        markerEnd: { type: MarkerType.ArrowClosed, color: isOverride ? COLORS.sealAmber : COLORS.slateBody },
      }
    })

    return { nodes: flowNodes, edges: flowEdges }
  }, [graph, msaDocId, sowDocId, flaggedNodeIds])

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
      </div>
      <div className="h-[70vh] w-full overflow-hidden rounded-md border border-ledger bg-white">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={NODE_TYPES}
          edgeTypes={EDGE_TYPES}
          fitView
          onNodeClick={(_, node) => onSelectClause?.(node.id)}
          nodesDraggable
          nodesConnectable={false}
          elementsSelectable
        >
          <Background color={COLORS.ledger} gap={16} size={1} />
          <Controls />
          <MiniMap
            pannable
            zoomable
            nodeColor={(n) => (n.id.startsWith(msaDocId) ? COLORS.sealBlue : COLORS.clay)}
            maskColor="rgba(245, 246, 248, 0.7)"
          />
        </ReactFlow>
      </div>
    </div>
  )
}
