# LLMHive - Next Generation AI Assistant Interface

LLMHive is a comprehensive AI assistant platform that leverages multiple specialized AI agents working in concert to provide superior responses with enhanced accuracy, transparency, and verification.

## Key Features

### 🐝 Multi-Agent System
- **Specialist AI Agents**: Legal, Code, Research, Math, Creative, and General experts
- **Agent Collaboration**: Multiple agents work together on each query
- **Consensus Building**: Automated debate and fact-checking between agents
- **Transparency**: View which agents contributed to each response

### 🎛️ Dynamic Criteria Equalizer
- **Accuracy Control**: Adjust how thorough the AI verification process is
- **Speed Control**: Balance between quick responses and deep analysis
- **Creativity Control**: Tune the creative vs. factual balance
- **Presets**: Quick settings for Balanced, Fast, Precise, and Creative modes

### 🔍 Enhanced Transparency
- **Agent Insights Panel**: See detailed breakdown of agent contributions
- **Confidence Scores**: Real-time consensus confidence metrics
- **Inline Citations**: All factual claims are cited and verified
- **Incognito Mode**: Toggle between showing/hiding agent details

### ⚡ Advanced Reasoning Modes
- **Deep Reasoning**: Maximum accuracy with step-by-step analysis
- **Standard Mode**: Balanced performance for general queries
- **Fast Mode**: Quick responses for simple questions

### 🔗 Integration Support
- **GitHub**: Connect repositories for code analysis and PR generation
- **Google Cloud**: Access BigQuery, Cloud Storage, and AI services
- **Vercel**: Deploy projects directly from chat

### 🎨 Premium Design
- **Bronze/Gold Theme**: Sophisticated color scheme matching the hexagonal brand
- **Hexagonal Motifs**: Subtle honeycomb patterns throughout the interface
- **Hive Activity Indicator**: Visual feedback when agents are processing
- **Responsive Design**: Works seamlessly on desktop and mobile

### 💬 Collaboration Features
- **Team Workspaces**: Share conversations with team members
- **Role Management**: Owner, Editor, and Viewer permissions
- **Real-time Status**: See who's online and actively working
- **Project Organization**: Group related conversations into projects

### 🛠️ Developer Tools
- **Code Execution**: Run JavaScript/TypeScript code directly in chat
- **Artifact Generation**: Create and view code, documents, and visualizations
- **File Uploads**: Support for images, PDFs, and documents with vision models
- **Multi-Model Support**: Switch between OpenAI, Anthropic, Google, xAI, and Meta models

## Architecture

LLMHive uses a revolutionary multi-agent architecture:

1. **Query Reception**: User input is analyzed to determine required expertise
2. **Agent Dispatch**: Relevant specialist agents are activated in parallel
3. **Parallel Processing**: Each agent generates its perspective independently
4. **Consensus Building**: Agents debate and verify each other's outputs
5. **Fact Checking**: Claims are verified against trusted sources
6. **Response Synthesis**: A unified response is created from agent inputs
7. **Transparency Layer**: User can view the full collaboration process

## Technology Stack

- **Framework**: Next.js 16 with App Router
- **AI SDK**: Vercel AI SDK v5 with AI Gateway
- **Styling**: Tailwind CSS v4 with custom bronze/gold theme
- **UI Components**: shadcn/ui with custom enhancements
- **Real-time**: Streaming responses with React hooks
- **Type Safety**: TypeScript throughout

## Getting Started

1. Clone the repository
2. Install dependencies: `npm install`
3. Run development server: `npm run dev`
4. Open [http://localhost:3000](http://localhost:3000)

## Vision Document Features Implementation

✅ Multi-agent system with specialist AI avatars
✅ Dynamic Criteria Equalizer (accuracy/speed/creativity sliders)
✅ Agent transparency & insights panel
✅ Confidence scores and consensus indicators
✅ Hexagonal/honeycomb brand motif
✅ Hive activity indicators showing parallel AI processing
✅ Incognito mode to show/hide agent contributions
✅ Inline citations with source verification
✅ Integration panel for GitHub, Google Cloud, Vercel
✅ Collaboration features with team management
✅ Advanced reasoning modes (deep, standard, fast)
✅ File upload with vision support
✅ Code execution environment
✅ Artifact generation and viewing
✅ Projects and conversation organization
✅ Comprehensive settings panel

## PR1-PR8: Elite Orchestration Features (NEW)

### PR1: OpenRouter Dynamic Rankings Integration
✅ Live model catalog from OpenRouter (340+ models)
✅ Dynamic rankings based on internal telemetry
✅ Model selection based on task type and performance data
✅ Cloud Scheduler job for regular sync

### PR2: Extended Strategy Memory
✅ Strategy usage logging with model team info
✅ Strategy memory storage for learning
✅ Performance tracking per strategy

### PR3: Verification Fallback & Refinement
✅ `retry_with_high_accuracy()` for verification failures
✅ Automatic escalation to stronger models
✅ Configurable refinement loops (1-5 iterations)

### PR4: Tool/RAG Broker Enhancement
✅ Web search integration (Tavily)
✅ Calculator tool for math queries
✅ RAG retrieval with domain filtering
✅ Tool decision logic in orchestrator

### PR5: Budget-Aware Routing
✅ `max_cost_usd` constraint support
✅ Cost-aware model scoring algorithm
✅ Model cost profiles (input/output per 1M tokens)
✅ Budget preference controls (prefer cheaper models)

### PR6: Orchestration Studio UI
✅ Elite strategy selector (7 strategies)
✅ Model team configuration
✅ Budget controls (max cost slider, prefer cheaper toggle)
✅ Live orchestration dashboard
✅ Strategy, Budget, and Engines tabs

### PR7: Prompt Suite Update
✅ MODEL_TEAM_ASSEMBLY_PROMPT for dynamic team composition
✅ ROUTER_SYSTEM_PROMPT_V2 with budget awareness
✅ VERIFIER_ENHANCED_PROMPT with 5-phase verification
✅ SYNTHESIZER_FUSION_PROMPT for multi-model fusion
✅ Dynamic model context injection

### PR8: Testing & Telemetry Dashboard
✅ E2E tests for orchestration scenarios
✅ Budget-aware routing tests
✅ Ambiguous query flow tests
✅ Verification fallback tests
✅ Tool usage tests
✅ OrchestratorMetricsDashboard component
✅ Backend telemetry module for strategy tracking
✅ Aggregated metrics (strategies, models, tools)

## The LLMHive Difference

Unlike traditional single-model chatbots, LLMHive represents a 10-year evolution:

- **Single Model → Agent Hive**: Multiple specialists instead of one generalist
- **Black Box → Transparency**: See exactly how responses are generated
- **Static → Dynamic**: Tune AI behavior in real-time with equalizer
- **Isolated → Integrated**: Deep integration with developer tools
- **Individual → Collaborative**: Team workspaces and sharing

## Elite Orchestration Strategies

LLMHive supports 7 elite orchestration strategies:

| Strategy | Description | Best For |
|----------|-------------|----------|
| **Automatic** | AI selects optimal strategy | General use |
| **Single Best** | Use highest-ranked model | Speed-critical tasks |
| **Parallel Race** | Run models in parallel, take fastest | Time-sensitive queries |
| **Best of N** | Generate N responses, select best | Quality-focused tasks |
| **Fusion** | Weighted merge of multiple outputs | Complex synthesis |
| **Expert Panel** | Domain experts collaborate | Multi-domain queries |
| **Challenge & Refine** | Iterative critique and improvement | Critical accuracy |

## Model Team Roles

Each orchestration uses a model team with defined roles:

| Role | Purpose |
|------|---------|
| **Primary** | Main response generator |
| **Validator** | Verifies and critiques output |
| **Fallback** | Backup if primary fails |
| **Specialist** | Domain-specific expert |

## Future Roadmap

- [ ] Dev Mode with integrated code editor
- [ ] Voice conversations with multi-agent processing
- [ ] Agent library with custom agent creation
- [ ] Enterprise admin dashboard
- [ ] Mobile app with full feature parity
- [ ] Public API for programmatic access
- [ ] Advanced telemetry analytics dashboard
- [ ] Custom strategy builder
- [ ] A/B testing for orchestration strategies

---

Built with ❤️ by the LLMHive team
