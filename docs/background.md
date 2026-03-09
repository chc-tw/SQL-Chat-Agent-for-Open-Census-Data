# Goal
We are working on US Open Census Dataset on snowflake. We want to create a web application of an interactive chat-based agent  that can answer natural language questions based on this data set. 

# Features List

## Basic
- Login with account credentials. no creation required
- Save and load chat history for each user
 
## Agent
- The agent must preserve conversation context; the user can answer multiple follow-up questions, and the agent should respond appropriately.
- Apply guardrails to ensure the agent does not answer off topic questions or provide “not safe for work” responses.
- Stream the output to the frontend

### SQL writing and data retrieval
- The agent should be able to write SQL queries based on the user's questions and execute them against the census dataset.
- The agent should think if the info from the census dataset is enough to answer the question and if not, it should further retrieve more data.

### Planning and database routing
- Agent should be able to understand the database structure and use metadata to find the relevant table and columns for the user's question.
- If the agent needs to retrieve data from multiple tables, it should join them appropriately.

## UI/UX
- Left Side showing a collapsible chat history, right side showing conversation with input field
- Showing current steps of agnet (planning, thinking, tool calling, etc.)
- Use Markdown format for rendering agnet's answer.

# Tech Stack Requirements

Below is the tech stack used in this project. If you have better suggestions, please let me know and we can try to use different tools.

**Backend**
- Python + FastAPI
- uv (build tool and dependency manager)
- pytest (test runner)
- Anthropic Claude API (native SDK, we should self-implement Agent loop)
- OpenAI API (embedding provider)
- chromadb (local vector database)
- Snowflake Python Connector
- Pydantic (data validation + automatic OpenAPI schema generation)
- `pydantic-settings` (environment variable management)
- `python-jose` (JWT generation and verification)
- Google Cloud Firestore (chat history persistence)

**Frontend**
- React + TypeScript
- Vite (build tool)
- vitest (test runner)
- pnpm (package manager)
- `openapi-typescript` (automatic API type generation)

**Deployment**
- GCP Cloud Run (backend)
- Firebase Hosting (frontend)
- GCP Secret Manager (secret management)
- GCP Artifact Registry (Docker image registry)
- GCP Firestore (chat history database)

**CI/CD**
- GitHub Actions (automated build + deploy)

**Development Tools**
- Docker (local development + Cloud Run deployment)
- `.env` + `.env.example` (local secret management)

# Dataflow