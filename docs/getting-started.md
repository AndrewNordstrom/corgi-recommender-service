# Getting Started

This guide will help you set up and run the Corgi Recommender Service locally for development or testing.

## Prerequisites

Before starting, ensure you have the following installed:

- Python 3.9+
- PostgreSQL 13+
- `pip` (Python package manager)
- Git (for cloning the repository)

## Installation

1. **Clone the repository**:

```bash
git clone https://github.com/yourusername/corgi-recommender-service.git
cd corgi-recommender-service
```

2. **Create a virtual environment** (optional but recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:

```bash
pip install -r requirements.txt
```

## Configuration

The service uses environment variables for configuration. Create a `.env` file in the project root or set these variables in your environment:

```
# Database configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=corgi_recommender
POSTGRES_USER=postgres
POSTGRES_PASSWORD=yourpassword

# Service configuration
DEBUG=True
HOST=0.0.0.0
PORT=5001
USER_HASH_SALT=yourrandomsalt  # Important for privacy protection
```

## Database Setup

1. **Create the PostgreSQL database**:

```bash
createdb corgi_recommender
```

2. **Run the setup script** to create the database schema:

```bash
./setup_db.sh
```

Alternatively, you can run:

```bash
python -c "from db.connection import init_db; init_db()"
```

## Running the Service

1. **Start the service**:

```bash
python -m flask --app app run --host=0.0.0.0 --port=5001
```

Or use the convenience script:

```bash
./start.sh
```

2. **Verify the service is running** by accessing the health endpoint:

```bash
curl http://localhost:5001/api/v1/health
```

You should see a JSON response with status information.

## Running the Validator

The service includes a validation tool to verify functionality:

```bash
python corgi_validator.py --verbose
```

This will:
- Create synthetic users and posts
- Simulate interactions
- Test recommendation generation
- Verify privacy controls
- Generate a validation report

## Next Steps

Once you have the service running, you can:

1. [Explore the API endpoints](endpoints/interactions.md)
2. Review the [architecture documentation](architecture.md)
3. [Integrate with your client application](client/README.md)