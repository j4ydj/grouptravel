# Group Travel Optimiser MVP

An internal corporate tool for comparing workshop locations and date options for 10-30 attendees traveling from different origin airports. The tool outputs total estimated flight costs, arrival spreads, average travel times, connection rates, and ranked recommendations using a transparent scoring function.

## Features

- **Attendee Management**: Create and manage attendees with their home airports, travel preferences, and constraints
- **Event Creation**: Create events with multiple candidate locations and date windows
  - Form-based creation
  - AI-powered natural language intake
- **Simulation Engine**: Compare all location/date combinations and compute metrics:
  - Total estimated flight cost per option
  - Arrival spread (time range between earliest and latest arrival)
  - Average travel time
  - Connections rate
  - Ranked recommendations using transparent scoring
- **Per-Attendee Itineraries**: Detailed suggested itineraries for each attendee per option
- **LLM Features**:
  - Natural language event intake → structured spec
  - Executive summary of computed results
  - Q&A over results (with strict no-hallucination guardrails)
- **PII Protection**: Basic redaction in logs and LLM prompts exclude unnecessary PII

## Architecture

- **Backend**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0
- **Storage**: SQLite for MVP
- **Caching**: Local SQLite table + in-memory LRU cache
- **Frontend**: Streamlit
- **LLM**: Supports both OpenAI and Vertex AI via abstraction layer
- **Container**: Docker + docker-compose

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and docker-compose (optional, for containerized deployment)

### Local Development

1. **Clone the repository**

```bash
git clone <repo-url>
cd GroupTravel
```

2. **Set up Python environment**

```bash
# Backend
cd app/backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r ../../requirements-backend.txt

# Frontend (in a separate terminal)
cd app/frontend
python -m venv venv
source venv/bin/activate
pip install -r ../../requirements-frontend.txt
```

3. **Configure environment variables**

Create a `.env` file in the project root (see `.env.example`):

```bash
DATABASE_URL=sqlite:///./data/grouptravel.db
LLM_PROVIDER=mock  # or 'openai' or 'vertex'
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...  # If using OpenAI
```

4. **Initialize database**

```bash
cd app/backend
python -m app.backend.db.init_db
```

5. **Run backend**

```bash
cd app/backend
uvicorn app.backend.main:app --reload --host 0.0.0.0 --port 8000
```

6. **Run frontend** (in a separate terminal)

```bash
cd app/frontend
streamlit run streamlit_app.py --server.port 8501
```

7. **Access the application**

- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Docker Deployment

1. **Create `.env` file** (copy from `.env.example`)

2. **Build and run**

```bash
docker-compose up --build
```

3. **Access the application**

- Frontend: http://localhost:8501
- Backend API: http://localhost:8000

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite database URL | `sqlite:///./data/grouptravel.db` |
| `LLM_PROVIDER` | LLM provider: `openai`, `vertex`, or `mock` | `mock` |
| `LLM_MODEL` | Model name (e.g., `gpt-4o`, `gemini-1.5-pro`) | `gpt-4o` |
| `OPENAI_API_KEY` | OpenAI API key (if using OpenAI) | - |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP credentials JSON (if using Vertex) | - |
| `VERTEX_PROJECT` | GCP project ID (if using Vertex) | - |
| `VERTEX_LOCATION` | GCP location (e.g., `us-central1`) | `us-central1` |
| `PRICING_PROVIDER` | Pricing provider: `mock` or `duffel` | `mock` |
| `DUFFEL_API_KEY` | Duffel API access token (required if `PRICING_PROVIDER=duffel`) | - |
| `PRICE_VOLATILITY` | Enable price volatility in mock pricing | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Switching LLM Providers

### Using OpenAI

1. Set `LLM_PROVIDER=openai` in `.env`
2. Set `OPENAI_API_KEY=sk-...` in `.env`
3. Set `LLM_MODEL=gpt-4o` (or another OpenAI model)

### Using Vertex AI

1. Set `LLM_PROVIDER=vertex` in `.env`
2. Set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json`
3. Set `VERTEX_PROJECT=your-project-id`
4. Set `VERTEX_LOCATION=us-central1` (or your preferred location)
5. Set `LLM_MODEL=gemini-1.5-pro` (or another Vertex model)

### Using Mock (Offline)

1. Set `LLM_PROVIDER=mock` in `.env`
2. No API keys needed - works offline with hardcoded responses

### Using Real Flight Data (Duffel)

1. Set `PRICING_PROVIDER=duffel` in `.env`
2. Set `DUFFEL_API_KEY=duffel_test_...` in `.env`
3. The system will use Duffel API for flight pricing
4. **Features**:
   - Automatic caching (SQLite + in-memory)
   - 30-second timeout protection
   - Automatic fallback to mock provider on API failure
5. Get your API key from: https://duffel.com/dashboard
6. **Note**: Duffel test keys have rate limits. For production, use a live API key.

## Usage Examples

### 1. Create Attendees

**Via CSV Upload:**
- Prepare CSV with columns: `employee_id`, `home_airport`
- Upload via Streamlit UI

**Via API:**
```bash
curl -X POST http://localhost:8000/api/attendees \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "EMP001",
    "home_airport": "JFK",
    "travel_class": "economy"
  }'
```

### 2. Create Event

**Via Form:**
- Use Streamlit UI "Create Event (Form)" page

**Via AI:**
- Use Streamlit UI "Create Event (AI)" page
- Paste natural language description:
  ```
  We're planning a 3-day workshop in either Lisbon or Munich next month.
  We need to accommodate 15 people traveling from various airports.
  ```

**Via API:**
```bash
curl -X POST http://localhost:8000/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Q2 Workshop",
    "candidate_locations": ["LIS", "MUC"],
    "candidate_date_windows": [
      {"start_date": "2024-06-01", "end_date": "2024-06-08"}
    ],
    "duration_days": 3,
    "created_by": "admin"
  }'
```

### 3. Attach Attendees to Event

```bash
curl -X POST http://localhost:8000/api/events/{event_id}/attendees \
  -H "Content-Type: application/json" \
  -d '{
    "attendee_ids": ["attendee_id_1", "attendee_id_2"]
  }'
```

### 4. Run Simulation

```bash
curl -X POST http://localhost:8000/api/events/{event_id}/simulate
```

### 5. View Results

```bash
curl http://localhost:8000/api/events/{event_id}/results/latest
```

### 6. Generate AI Summary

```bash
curl -X POST http://localhost:8000/api/events/{event_id}/ai/summary
```

### 7. Ask Questions

```bash
curl -X POST http://localhost:8000/api/events/{event_id}/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the cheapest option?"
  }'
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/attendees` | POST | Create attendee |
| `/api/attendees` | GET | List all attendees |
| `/api/attendees/{id}` | GET | Get attendee by ID |
| `/api/events` | POST | Create event |
| `/api/events/{id}` | GET | Get event by ID |
| `/api/events/{id}/attendees` | POST | Attach attendees to event |
| `/api/events/{id}/simulate` | POST | Run simulation |
| `/api/events/{id}/results/latest` | GET | Get latest simulation results |
| `/api/ai/parse_event_text` | POST | Parse natural language to EventDraft |
| `/api/events/{id}/ai/summary` | POST | Generate executive summary |
| `/api/events/{id}/ask` | POST | Q&A about simulation results |

## Scoring Function

The optimization score is calculated as:

```
score = (total_cost × 1.0) + (arrival_spread_minutes × 5) + 
        (avg_travel_time_minutes × 2) + (connections_rate × 500)
```

**Lower scores are better.** The function balances:
- Cost minimization (1x weight)
- Arrival synchronization (5x weight - important for group coordination)
- Travel time efficiency (2x weight)
- Direct flight preference (500x weight - strong preference for non-stop flights)

## Testing

Run tests with pytest:

```bash
cd app/backend
pytest
```

Run specific test files:

```bash
pytest tests/test_pricing.py
pytest tests/test_optimiser.py
pytest tests/test_api.py
```

## Security Notes

### PII Handling

- **Logs**: All logs are filtered through a redaction service that removes emails and potential names
- **LLM Prompts**: Only include:
  - Employee IDs (not names)
  - Airport codes
  - Numeric metrics
  - No personal information beyond what's necessary
- **Database**: Stores employee_id, airport codes, and preferences only

### Authentication

For MVP, authentication is a placeholder. In production:
- Implement JWT-based authentication
- Add role-based access control
- Secure API endpoints

## Architecture Notes

### Pricing Provider

- **MVP**: Uses `MockPricingProvider` with deterministic fake data
- **Future**: Stub classes included for:
  - `TravelpayoutsProvider`
  - `DuffelProvider`
  - `ConcurProvider`

To swap providers, modify `app/backend/services/optimiser.py` to use a different provider instance.

### Caching

- **In-memory**: LRU cache (max 1000 entries) for pricing results
- **SQLite**: Persistent cache table for pricing results across restarts

### Database

- **MVP**: SQLite (file-based)
- **Production**: Can be swapped to PostgreSQL by changing `DATABASE_URL`

## Limitations (MVP)

- **No real booking**: This is a simulation tool only
- **Mock pricing**: Uses deterministic fake data
- **No ticket issuance**: No actual flight booking capabilities
- **Basic authentication**: Placeholder only
- **SQLite only**: Not optimized for high concurrency

## Future Enhancements

- Real pricing provider integration (Travelpayouts, Duffel, Concur)
- PostgreSQL support for production
- JWT authentication
- WebSocket support for real-time simulation progress
- Export results to PDF/Excel
- Historical comparison of simulations
- Multi-currency support
- Hotel pricing integration

## Troubleshooting

### Database errors

- Ensure `data/` directory exists and is writable
- Check `DATABASE_URL` in `.env`

### LLM errors

- Verify API keys are set correctly
- Check network connectivity
- For Vertex AI, ensure credentials file path is correct

### Port conflicts

- Backend default: 8000
- Frontend default: 8501
- Modify in `docker-compose.yml` or command-line arguments

## License

Internal use only.

## Support

For issues or questions, contact the development team.
