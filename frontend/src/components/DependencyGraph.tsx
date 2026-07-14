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
          padding: 8,
          borderRadius: 8,
          border: isFlagged ? '2px solid #dc2626' : '1px solid #cbd5e1',
          background: n.doc_id === msaDocId ? '#eff6ff' : '#faf5ff',
        },
      }
    })

    const flowEdges: Edge[] = graph.edges.map((e, i) => ({
      id: `${e.source}->${e.target}-${i}`,
      source: e.source,
      target: e.target,
      label: e.kind === 'notwithstanding_override' ? 'overrides' : undefined,
      animated: e.kind === 'notwithstanding_override',
      style: { stroke: e.kind === 'notwithstanding_override' ? '#d97706' : '#94a3b8' },
      markerEnd: { type: MarkerType.ArrowClosed, color: e.kind === 'notwithstanding_override' ? '#d97706' : '#94a3b8' },
    }))

    return { nodes: flowNodes, edges: flowEdges }
  }, [graph, msaDocId, sowDocId, flaggedNodeIds])

  return (
    <div className="h-[70vh] w-full rounded-lg border border-slate-200 bg-white">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        onNodeClick={(_, node) => onSelectClause?.(node.id)}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
      >
        <Background />
        <Controls />
        <MiniMap pannable zoomable />
      </ReactFlow>
    </div>
  )
}
