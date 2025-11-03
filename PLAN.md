# reAItor - AI-Powered Real Estate Platform

## Project Overview
An intelligent real estate platform that uses multiple AI agents to find, evaluate, and present property listings tailored to user preferences. The system employs a multi-agent architecture with scraping agents, evaluation agents, argumentative agents, and a learning presentation layer.

## Architecture

### High-Level Flow
```
User (Chat) → Conversational Agent → Scraper Agents → Evaluation Agent → Argumentative Agents → Compilation Agent → Presentation Agent → User (Swipe)
                                                              ↓
                                                         ChromaDB (RAG)
```

## Tech Stack

### Frontend
- **Next.js 14** (App Router)
- **TypeScript**
- **Tailwind CSS** for styling
- **Framer Motion** for Tinder-style swipe animations
- **Zustand** for state management
- **Vercel AI SDK** (or similar) for chatbot UI components

### Backend
- **Python FastAPI**
- **Pydantic** for data validation
- **uvicorn** as ASGI server

### AI Agents
- **Conversational Intake Agent**: Direct Anthropic Claude API for preference gathering chatbot
- **Scraper Agents**: Python classes with Playwright (Zillow, Redfin, Realtor.com)
- **Letta Framework** for advanced agents:
  - Evaluation agent (with RAG)
  - Pro/Con argumentative agents
  - Compilation agent
  - Presentation/recommendation agent

### Vector Database
- **ChromaDB** for storing and retrieving similar past evaluations

### Additional Tools
- **Playwright** for web scraping
- **Letta** for agent framework and RAG
- **Anthropic Claude API** for LLM calls

## Agent Architecture

### 1. Conversational Intake Agent
**Responsibilities:**
- Engage user in natural conversation to gather preferences
- Ask clarifying questions about:
  - Budget and price range
  - Location preferences (city, neighborhood, proximity to work)
  - Property specifications (bedrooms, bathrooms, square footage)
  - Must-have features vs. nice-to-have features
  - Lifestyle preferences (walkability, schools, nightlife, etc.)
  - Deal-breakers (no HOA, must have garage, etc.)
- Extract structured data from conversational input
- Handle ambiguous responses gracefully
- Build UserPreferences object from conversation

**Conversational Flow Examples:**
- "What's your budget for your new home?"
- "Which areas are you looking in? Any specific neighborhoods?"
- "How many bedrooms do you need? Any flexibility on that?"
- "What matters most to you - proximity to work, good schools, or nightlife?"
- "Are there any absolute deal-breakers for you?"

**Inputs:**
- User messages (text)
- Conversation history

**Outputs:**
- UserPreferences object (once conversation is complete)
- Conversational responses (streaming)

### 2. Scraper Agents (3 agents)
Each agent is dedicated to one real estate platform:
- **ZillowScraperAgent**
- **RedfinthScraperAgent**
- **RealtorComScraperAgent**

**Responsibilities:**
- Accept user preferences (price range, bedrooms, bathrooms, sqft, location)
- Scrape respective platforms for matching listings
- Extract: address, price, beds, baths, sqft, images, description, URL
- Return structured listing data

**Communication:**
- Receives preferences from API endpoint
- Sends results to Evaluation Agent

### 2. Evaluation Agent
**Responsibilities:**
- Combine listings from all scraper agents
- Evaluate against user's explicit preferences
- Enhance with additional factors:
  - Crime rate data (via external APIs)
  - School proximity and ratings
  - Walkability scores
  - Public transport access
  - Local amenities affordability
  - Property tax estimates
  - HOA fees
  - Days on market
- Query ChromaDB for 5 most similar past evaluations (RAG)
- Generate comprehensive evaluation report

**Inputs:**
- Combined listings from scrapers
- User preferences
- Similar past evaluations from ChromaDB

**Outputs:**
- Structured evaluation report for each listing

### 3. Argumentative Agents (2 agents)

#### Pro Agent
**Responsibilities:**
- Review listing details and evaluation report
- Construct persuasive arguments FOR purchasing
- Highlight strengths matching user preferences
- Identify value propositions and opportunities

#### Con Agent
**Responsibilities:**
- Review listing details and evaluation report
- Construct critical arguments AGAINST purchasing
- Identify potential flaws, risks, and red flags
- Point out mismatches with user preferences

**Communication:**
- Both receive evaluation report
- Send arguments to Compilation Agent

### 4. Compilation Agent
**Responsibilities:**
- Receive evaluation report and pro/con arguments
- Synthesize all information
- Generate balanced final report
- Assign score out of 10 (weighted algorithm)
- Create executive summary

**Scoring Weights:**
- User preference match: 40%
- Additional factors (crime, schools, etc): 30%
- Pro/Con argument balance: 20%
- RAG similarity insights: 10%

### 5. Presentation Agent
**Responsibilities:**
- Order listings by score
- Learn from user swipes (right = like, left = dislike)
- Build preference profile over time
- Re-rank listings based on learned preferences
- Implement collaborative filtering for recommendations

**Learning Mechanism:**
- Track which features correlate with right swipes
- Adjust feature weights dynamically
- Store preference vectors in ChromaDB

## Data Models

### UserPreferences
```python
class UserPreferences(BaseModel):
    price_min: int
    price_max: int
    bedrooms_min: int
    bedrooms_max: int
    bathrooms_min: float
    bathrooms_max: float
    sqft_min: int
    sqft_max: int
    location: str  # city, zip code, or coordinates
    property_types: List[str]  # house, condo, townhouse, etc.
    additional_features: Optional[List[str]]  # pool, garage, etc.
```

### Listing
```python
class Listing(BaseModel):
    id: str
    source: str  # zillow, redfin, realtor.com
    url: str
    address: str
    city: str
    state: str
    zip_code: str
    price: int
    bedrooms: int
    bathrooms: float
    sqft: int
    property_type: str
    description: str
    images: List[str]
    listing_date: str
    days_on_market: int
```

### EvaluationReport
```python
class EvaluationReport(BaseModel):
    listing_id: str
    preference_match_score: float  # 0-10
    crime_score: float  # 0-10
    school_score: float  # 0-10
    walkability_score: float  # 0-10
    affordability_score: float  # 0-10
    similar_evaluations: List[str]  # from RAG
    strengths: List[str]
    concerns: List[str]
```

### ArgumentReport
```python
class ArgumentReport(BaseModel):
    listing_id: str
    pro_arguments: List[str]
    con_arguments: List[str]
```

### FinalReport
```python
class FinalReport(BaseModel):
    listing: Listing
    evaluation: EvaluationReport
    arguments: ArgumentReport
    final_score: float  # 0-10
    executive_summary: str
    recommendation: str  # "Strong Buy", "Consider", "Pass"
```

## API Endpoints

### Backend API (FastAPI)
```
POST /api/chat/start
- Returns: chat_session_id

POST /api/chat/{session_id}/message
- Body: { message: string }
- Returns: { response: string, preferences_complete: boolean }
- Streaming support for real-time responses

GET /api/chat/{session_id}/preferences
- Returns: UserPreferences (extracted so far)

POST /api/search/start
- Body: { chat_session_id: string }
- Initiates scraping with extracted preferences
- Returns: search_session_id

GET /api/search/{session_id}/status
- Returns: processing status and progress

GET /api/search/{session_id}/results
- Returns: List[FinalReport] (ordered by score)

POST /api/feedback
- Body: { listing_id, action: "like" | "dislike" }
- Updates user preference model

GET /api/listings/{session_id}/next
- Returns: Next best listing based on learned preferences
```

## Implementation Plan

### Phase 1: Project Setup
1. Initialize Next.js frontend with TypeScript
2. Set up FastAPI backend with Python virtual environment
3. Install dependencies:
   - Frontend: next, react, typescript, tailwind, framer-motion, zustand
   - Backend: fastapi, uvicorn, pydantic, uagents, chromadb, langchain, beautifulsoup4, playwright
4. Create project structure:
   ```
   reAItor/
   ├── frontend/           # Next.js app
   │   ├── app/
   │   ├── components/
   │   └── lib/
   ├── backend/            # FastAPI app
   │   ├── agents/
   │   ├── api/
   │   ├── models/
   │   └── services/
   └── PLAN.md
   ```

### Phase 2: Backend Core
1. Set up FastAPI application structure
2. Define Pydantic models for all data structures
3. Create API endpoint stubs
4. Set up ChromaDB connection and collections
5. Implement session management

### Phase 3: Conversational Intake Agent
1. Implement conversational agent with LLM
2. Create conversation flow and prompt templates
3. Build preference extraction logic
4. Implement conversation state management
5. Add validation for extracted preferences
6. Create "preferences complete" detection

### Phase 4: Scraper Agents
1. Implement base scraper agent class
2. Create ZillowScraperAgent with Playwright
3. Create RedfinhScraperAgent with Playwright
4. Create RealtorComScraperAgent with Playwright
5. Implement error handling and rate limiting
6. Add data normalization pipeline

### Phase 5: Evaluation Agent
1. Implement listing aggregation logic
2. Integrate external APIs:
   - Crime data (FBI Crime Data API or similar)
   - School ratings (GreatSchools API)
   - Walkability (Walk Score API)
3. Build RAG pipeline with ChromaDB
4. Implement similarity search for past evaluations
5. Create evaluation scoring algorithm

### Phase 6: Argumentative Agents
1. Implement Pro Agent with LLM integration
2. Implement Con Agent with LLM integration
3. Create prompts for structured argument generation
4. Add argument quality validation

### Phase 7: Compilation Agent
1. Implement report synthesis logic
2. Create weighted scoring algorithm
3. Generate executive summaries with LLM
4. Store final reports in ChromaDB

### Phase 8: Presentation Agent
1. Implement basic recommendation ordering
2. Build user preference learning model
3. Create feedback processing pipeline
4. Implement dynamic re-ranking

### Phase 9: Frontend - Chatbot Interface
1. Create chatbot UI component (message bubbles, input field)
2. Implement streaming message responses
3. Add typing indicators and animations
4. Build conversation state management
5. Create "Start Search" button when preferences complete
6. Add ability to review/edit extracted preferences
7. Implement conversation history display

### Phase 10: Frontend - Presentation UI
1. Build Tinder-style card component
2. Implement swipe gestures (Framer Motion)
3. Create listing detail view
4. Add image carousel
5. Display evaluation reports and arguments
6. Show final score visualization

### Phase 11: Integration & Testing
1. Connect frontend to backend API
2. Test complete user flow end-to-end
3. Add error handling and loading states
4. Implement retry logic
5. Performance optimization

### Phase 12: Polish & Features
1. Add listing comparison feature
2. Implement favorites/saved listings
3. Create email notifications for new matches
4. Add export to PDF functionality
5. Mobile responsive design

## External APIs & Services

### Required API Keys
1. **OpenAI API** or **Anthropic API** - For LLM calls
2. **Walk Score API** - Walkability scores
3. **GreatSchools API** - School ratings
4. **FBI Crime Data API** or **CrimeReports.com** - Crime statistics
5. **Google Maps API** - Geocoding and location services

### Optional Enhancements
- **Zillow API** (if available) - Official data access
- **Redfin API** (if available) - Official data access
- **Realtor.com API** (if available) - Official data access

## Deployment Considerations

### Development
- Frontend: `npm run dev` on localhost:3000
- Backend: `uvicorn main:app --reload` on localhost:8000

### Production
- Frontend: Vercel (Next.js native platform)
- Backend: Railway, Render, or AWS EC2
- ChromaDB: Self-hosted or cloud instance
- Environment variables for API keys

## Scalability Considerations

1. **Rate Limiting**: Implement scraping rate limits to avoid IP bans
2. **Caching**: Cache listings for 24 hours to reduce scraping load
3. **Async Processing**: Use background tasks for agent workflows
4. **Queue System**: Consider Celery or RQ for job queuing
5. **Database**: Transition to PostgreSQL for production persistence

## Legal & Ethical Considerations

1. **Web Scraping**: Respect robots.txt, rate limits, and ToS
2. **Data Accuracy**: Disclaimer that scraped data may be outdated
3. **Fair Housing**: Ensure no discriminatory filtering or recommendations
4. **Privacy**: Don't store personally identifiable information
5. **API Compliance**: Follow all external API terms of service

## Future Enhancements

1. User authentication and saved searches
2. Real-time listing updates via webhooks
3. Mortgage calculator integration
4. Virtual tour integration
5. Agent contact and appointment scheduling
6. Market trends and analytics dashboard
7. Multi-user collaboration (family decision-making)
8. Mobile app (React Native)

## Success Metrics

1. Listing relevance accuracy (user swipe right rate)
2. Time to find suitable listings
3. Presentation agent learning effectiveness
4. User engagement and session duration
5. Listing coverage across platforms

---

## Getting Started

Once this plan is approved, we'll begin with Phase 1: Project Setup, creating the directory structure and installing dependencies.
