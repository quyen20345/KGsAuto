# KGsAuto Frontend

React SPA for browsing, searching, merging, and chatting with a Vietnamese knowledge graph built from UET markdown sources.

## Overview

```mermaid
flowchart LR
    subgraph Frontend["React SPA (Vite)"]
        direction TB
        Pages[Pages]
        API[api.js service]
    end

    subgraph GraphAPI["Graph API :8000"]
        G1[Entity CRUD]
        G2[Search]
        G3[Cypher Query]
        G4[Merge]
    end

    subgraph ChatAPI["Chat API :8002"]
        C1[Modes]
        C2[Stream Completions]
    end

    subgraph Infra["Infrastructure"]
        Neo4j[(Neo4j)]
        Qdrant[(Qdrant)]
    end

    Pages --> API
    API --> GraphAPI
    API --> ChatAPI
    GraphAPI --> Neo4j
    ChatAPI --> Neo4j
    ChatAPI --> Qdrant
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 19 |
| Bundler | Vite 8 |
| Routing | React Router DOM 7 |
| Markdown | react-markdown + remark-gfm |
| Graph viz | react-force-graph-2d |
| Styling | Plain CSS with custom properties |
| Linting | ESLint 9 |

## File Structure

```
src/
├── main.jsx                    # Entry point
├── App.jsx                     # Router + global layout
├── index.css                   # Global styles + design tokens
├── services/
│   └── api.js                  # All backend API calls
├── components/
│   ├── Header.jsx              # App header + nav + search
│   ├── EntityLink.jsx          # Link with hover popover
│   ├── EntityPopover.jsx       # Portal-based entity preview
│   └── RelationshipTooltip.jsx # Relationship description tooltip
└── pages/
    ├── Home.jsx                # Random triplets explorer
    ├── Search.jsx              # Lexical/hybrid entity search
    ├── Entity.jsx              # Entity detail + duplicates
    ├── Merge.jsx               # Cypher console + merge tools
    └── chat/
        ├── index.jsx           # Chat orchestrator (state + streaming)
        ├── ChatSidebar.jsx     # Mode/TopK/starters/reset
        ├── ChatComposer.jsx    # Textarea + send/abort
        ├── ChatMessage.jsx     # Message bubble + actions
        ├── MarkdownContent.jsx # ReactMarkdown wrapper
        ├── ReasoningPanel.jsx  # Collapsible reasoning trace
        ├── EvidencePanel.jsx   # Evidence cards
        ├── EmptyState.jsx      # Landing screen
        ├── Icons.jsx           # Inline SVG icons
        └── chat.css            # Chat-scoped styles
```

## Routing

| Path | Page | Description |
|------|------|-------------|
| `/` | Home | Random knowledge graph triplets |
| `/search` | Search | Entity search (empty state) |
| `/search/:query` | Search | Entity search with query |
| `/chat` | Chat | RAG chatbot interface |
| `/entity/:id` | Entity | Entity detail view |
| `/merge` | Merge | Cypher console + merge tools |

## Component Hierarchy

```mermaid
flowchart TB
    App[App.jsx]
    Header[Header]
    Home[Home]
    Search[Search]
    Entity[Entity]
    Merge[Merge]
    Chat[Chat]

    App --> Header
    App --> Home
    App --> Search
    App --> Entity
    App --> Merge
    App --> Chat

    subgraph SharedComponents["Shared Components"]
        EL[EntityLink]
        EP[EntityPopover]
        RT[RelationshipTooltip]
    end

    Home --> EL
    Home --> RT
    Search --> EL
    Entity --> EL
    Entity --> RT
    EL --> EP

    subgraph ChatComponents["Chat Components"]
        CS[ChatSidebar]
        CC[ChatComposer]
        CM[ChatMessage]
        ES[EmptyState]
        MC[MarkdownContent]
        RP[ReasoningPanel]
        EVP[EvidencePanel]
    end

    Chat --> CS
    Chat --> CC
    Chat --> CM
    Chat --> ES
    CM --> MC
    CM --> RP
    CM --> EVP
```

## Chat Streaming Flow

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Chat as Chat Page
    participant API as api.js
    participant Backend as Chat API :8002

    User->>Chat: Type message + Enter
    Chat->>Chat: Create user message + placeholder assistant
    Chat->>Chat: Set isLoading=true, create AbortController

    Chat->>API: streamChatMessage({ message, mode, signal, onEvent })
    API->>Backend: POST /v1/chat/completions (stream: true)

    loop SSE Events
        Backend-->>API: data: { choices, kgsauto }
        API-->>Chat: onEvent(parsed)
        Chat->>Chat: Append token / update status / accumulate reasoning
    end

    Backend-->>API: data: [DONE]
    API-->>Chat: Promise resolves
    Chat->>Chat: Clear status, set isLoading=false

    alt User clicks Stop
        User->>Chat: Click abort button
        Chat->>Chat: abortController.abort()
        API-->>Chat: AbortError caught silently
        Chat->>Chat: Keep partial content, clear status
    end

    alt Backend error
        Backend-->>API: HTTP error or network failure
        API-->>Chat: Error thrown
        Chat->>Chat: Mark message as error, show retry button
    end
```

## API Service Reference

### Graph API (`GRAPH_API_BASE` — default `http://localhost:8000`)

| Method | Endpoint | Used by |
|--------|----------|---------|
| `getRandomTriplets(limit)` | `GET /api/random_triplets` | Home |
| `search(query)` | `GET /api/search` | — |
| `searchLexical(query, topK, labelFilter)` | `GET /api/search/lexical` | Search, Entity |
| `searchHybrid(query, topK, labelFilter)` | `GET /api/search/hybrid` | Search |
| `getEntity(id)` | `GET /api/entity/:id` | Entity, EntityPopover |
| `mergeEntities({ canonical_id, merge_ids })` | `POST /api/entity/merge` | Merge |
| `runCypher(cypher)` | `POST /api/query` | Merge |
| `getGraphMetadata()` | `GET /api/graph/metadata` | Search |

### Chat API (`CHAT_API_BASE` — default `http://localhost:8002`)

| Method | Endpoint | Used by |
|--------|----------|---------|
| `getChatModes()` | `GET /modes` | Chat |
| `sendChatMessage(...)` | `POST /query` | (available, not used by UI) |
| `streamChatMessage(...)` | `POST /v1/chat/completions` | Chat |

## Styling

### Design Tokens (`:root` in `index.css`)

```css
--primary: #336699;
--text: #333;
--bg: #fff;
--border: #e0e0e0;
```

### Chat-scoped Tokens (`.chat-shell` in `chat.css`)

```css
--chat-text: #1f2937;
--chat-text-muted: #667085;
--chat-text-soft: #475467;
--chat-surface: #ffffff;
--chat-surface-soft: #f9fafb;
--chat-surface-tint: #f8fbff;
--chat-border: var(--border);
--chat-border-strong: #d0d5dd;
--chat-user-bg: #eff6ff;
--chat-user-border: #bfdbfe;
--chat-danger: #b42318;
--chat-danger-bg: #fffbfa;
--chat-danger-border: #fda29b;
--chat-radius-sm: 10px;
--chat-radius-md: 12px;
--chat-radius-lg: 16px;
--chat-shadow-card: 0 8px 30px rgba(15, 23, 42, 0.06);
```

### Conventions

- Global styles use semantic class names (`.entity-title`, `.merge-button`)
- Chat uses `chat-` prefix for all selectors — fully isolated from other pages
- No Tailwind, no CSS modules, no CSS-in-JS
- Responsive breakpoint at `860px` (single-column collapse)

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `VITE_GRAPH_API_BASE_URL` | Graph/admin API base | `http://localhost:8000` |
| `VITE_API_BASE_URL` | Backward-compatible alias | `http://localhost:8000` |
| `VITE_CHAT_API_BASE_URL` | Chat API base | `http://localhost:8002` |

## Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Production build
npm run build

# Lint
npm run lint

# Preview production build
npm run preview
```

### Prerequisites

- Node.js 18+
- Graph API running on `:8000` (for Home, Search, Entity, Merge)
- Chat API running on `:8002` (for Chat page)
- Neo4j populated with graph data
- Qdrant with indexed markdown chunks (for semantic/hybrid chat modes)

## Key Design Patterns

| Pattern | Where | Purpose |
|---------|-------|---------|
| Manual SSE streaming | `api.js` → Chat | Token-by-token UI updates |
| AbortController | Chat, Search | User-cancelable requests + timeouts |
| Optimistic placeholder | Chat | Insert assistant bubble before stream starts |
| Incremental metadata | Chat | Accumulate reasoning steps during stream |
| On-demand hover fetch | EntityPopover | Load entity data only when popover opens |
| Portal overlays | EntityPopover | Escape stacking context issues |
| Route-driven state | Search, Entity | URL params drive data fetching |
| Local persistence | Merge | Last Cypher query saved to localStorage |
