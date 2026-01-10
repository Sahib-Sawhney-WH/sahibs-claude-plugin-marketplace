---
description: Scaffold a new Python application with Dataverse integration
argument-hint: "[app_name]"
allowed-tools:
  - Read
  - Write
  - Bash
  - AskUserQuestion
---

# Dataverse Scaffold App Command

Create a new Python application project with Dataverse integration pre-configured.

## Instructions

When the user runs `/dataverse:scaffold-app [name]`:

1. **Get app name**
   - Use provided name or ask for one
   - Create directory with that name

2. **Choose app type**
   - Flask API
   - FastAPI API
   - CLI tool
   - Data pipeline script

3. **Create project structure**
   - Generate appropriate files based on type
   - Include Dataverse client setup
   - Add configuration templates

4. **Set up dependencies**
   - Create requirements.txt
   - Include all needed packages

5. **Generate starter code**
   - Main application file
   - Dataverse client module
   - Configuration handling
   - Example endpoints/commands

### Flask API Structure
```
{app_name}/
├── app/
│   ├── __init__.py
│   ├── dataverse_client.py
│   ├── config.py
│   └── routes/
│       ├── __init__.py
│       └── accounts.py
├── requirements.txt
├── .env.example
├── run.py
└── README.md
```

### FastAPI Structure
```
{app_name}/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── dataverse_client.py
│   ├── config.py
│   ├── models/
│   │   └── account.py
│   └── routers/
│       └── accounts.py
├── requirements.txt
├── .env.example
└── README.md
```

### CLI Tool Structure
```
{app_name}/
├── {app_name}/
│   ├── __init__.py
│   ├── cli.py
│   ├── dataverse_client.py
│   └── commands/
│       └── accounts.py
├── requirements.txt
├── .env.example
├── setup.py
└── README.md
```

### Data Pipeline Structure
```
{app_name}/
├── pipeline/
│   ├── __init__.py
│   ├── extract.py
│   ├── transform.py
│   ├── load.py
│   └── dataverse_client.py
├── requirements.txt
├── .env.example
├── run_pipeline.py
└── README.md
```

### Files to Generate

1. **dataverse_client.py** - Singleton client setup
2. **config.py** - Environment variable handling
3. **.env.example** - Template for environment variables
4. **requirements.txt** - Python dependencies
5. **README.md** - Project documentation
6. **Main app file** - Entry point with example code

### Post-Scaffold Instructions

After generating, tell user to:
1. Copy `.env.example` to `.env`
2. Fill in Dataverse credentials
3. Install dependencies: `pip install -r requirements.txt`
4. Run the application
