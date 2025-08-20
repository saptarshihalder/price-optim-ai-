# Backend Application

This directory contains the backend application for the Price Optimization AI project. It is built using FastAPI and handles API routing, authentication, and integration with various services.

## Project Structure

- `main.py`: The main entry point for the FastAPI application. It handles router imports, authentication configuration, and application creation.
- `app/apis/`: Contains subdirectories for different API modules (e.g., `competitor_scraping`, `price_optimization`). Each subdirectory is expected to have an `__init__.py` file that exposes a FastAPI `APIRouter` instance.
- `app/auth/`: Contains authentication-related logic, including user authorization.
- `app/libs/`: Contains shared libraries and utility functions, such as database interactions and product matching.
- `databutton_app/mw/`: Middleware for the Databutton application, including authentication middleware.
- `routers.json`: (Expected) A JSON file that defines the API routers and their authentication settings. This file is not version controlled and is expected to be generated or provided at runtime.

## Dependencies

The backend dependencies are managed using `poetry` and are listed in `pyproject.toml` and `requirements.txt`. Key dependencies include:

- `fastapi`: Web framework for building APIs.
- `uvicorn`: ASGI server for running the FastAPI application.
- `databutton`: (Specific to Databutton platform)
- `openai`: For AI model interactions.
- `beautifulsoup4`, `requests`, `aiohttp`, `lxml`: For web scraping.
- `asyncpg`: For asynchronous PostgreSQL database interactions.

## Setup and Running

To set up and run the backend, refer to the `install.sh` and `run.sh` scripts in this directory.

## API Endpoints

API endpoints are dynamically loaded from the `app/apis/` directory. Each API module is expected to expose a FastAPI `APIRouter`. Authentication for each router can be configured via the `routers.json` file.

## Authentication

The application supports Firebase authentication. The Firebase configuration is loaded from the `DATABUTTON_EXTENSIONS` environment variable.