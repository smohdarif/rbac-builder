# RBAC Builder for LaunchDarkly

A Python/Streamlit application that allows Solution Architects to design RBAC (Role-Based Access Control) policies for LaunchDarkly through an interactive UI matrix interface.

## Features

- **Interactive Permission Matrix** - Design RBAC visually like a spreadsheet
- **Two Modes of Operation**:
  - **Connected Mode** - Fetch projects/environments from LaunchDarkly API
  - **Manual Mode** - Enter details manually without API access
- **Direct Deployment** - Deploy RBAC directly to LaunchDarkly via API
- **Configuration Persistence** - Save/load configurations as JSON
- **Validation** - Validate configurations before deployment

## Quick Start

### Prerequisites

- Python 3.10+
- LaunchDarkly account (for deployment)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/rbac-builder.git
cd rbac-builder

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`.

## Usage

### Stage 1: Setup

1. Enter customer name
2. Choose mode:
   - **Connected Mode**: Enter LaunchDarkly API key to auto-fetch projects and environments
   - **Manual Mode**: Enter projects, environments, and teams manually
3. Define teams/functional roles

### Stage 2: Design Matrix

1. Use the permission matrix to assign permissions to teams
2. Columns are grouped by:
   - Project-scoped actions (apply to all environments)
   - Environment-scoped actions (per environment)
3. Check/uncheck permissions as needed

### Stage 3: Review & Deploy

1. Review the deployment summary
2. Check validation status
3. Save configuration and/or deploy to LaunchDarkly

## Project Structure

```
rbac-builder/
├── app.py                    # Main entry point
├── requirements.txt          # Python dependencies
├── models/                   # Data models
├── core/                     # Constants and mappings
├── services/                 # Business logic
├── ui/                       # Streamlit UI components
├── configs/                  # Saved configurations
├── templates/                # Starter templates
└── tests/                    # Unit tests
```

## Documentation

- [Design Document](./RBAC_BUILDER_DESIGN.md) - Detailed architecture and implementation guide

## License

MIT License
