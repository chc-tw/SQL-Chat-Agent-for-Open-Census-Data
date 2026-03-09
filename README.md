 # 2026 Snowflake Applied AI Home Work Assignment
 
## How to access

Go to the website [link](https://chc-snowflake-agent.web.app/) and use one of the following accounts to login. Note that different account will have different session and have different chat history records.

> Note that initial access might be delayed due to Cloud Run cold starts

| account | password |
| --- | --- |
| user1 | password1 |
| user2 | password2 |
| user3 | password1 |
| user4 | password2 |
| user5 | password1 |

## Development Process
- Timeline

| time | progress |
| --- | --- |
| 0 hr ~ 4 hr | database understanding |
| 4 hr ~ 10 hr | documents writing |
| 10 hr ~ 20 hr | code implementation (1st ver) |
| 20 hr ~ 23 hr | feature updating |
| 23 hr ~ 26 gr | agent validation and improvement |
| 26 hr ~ 30 hr | deployment & conclusion |

At first, I invested a lot of time to write documents about project structure, agent design and system design to make sure the process of developement can be stable and I can utilize these docs to guide AI to support me develope the code. (All under the `docs` folder). List of docs:
1. `docs/background.md`: The main doc about feature and tech stack
2. `docs/agent_design`: The design of agent
3. `docs/agent_evaluation.md`: The mechanism of agent validation
4. `docs/context_management.md`: The mechanism of dynamic context management for knowledge loading.
5. `docs/database_structure.md`: The explanation docs of database structure.

### Implementation details

Instead of using library such as Langchain or CrewAI, I choosed to use native API to build agent engin on my own to have fully controll about its behavior. I initially tried to use Typescript for full-stack development, but I noticed the SDK support of Claude API in typescript is not as good as Python, so I changed the tech stack using Python to build backend. 

The development process is:
agent logic -> API Endpoint -> Frontend -> features adding -> agent validation and improvement

The most challenging part is to make agent successfully write the correct SQL, because it contains the complex metadata mapping and join operation. 

## Future Improvement
### Agent
[] add more knowledges to improve performance
[] add human-in-loop to clarify user's intention. For example, when use says "New York", agent should ask is it New York city or New York state.

### Web
[] enable chat edit
[] enable terminate response