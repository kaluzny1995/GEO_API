"""Run the FastAPI application with uvicorn."""

import uvicorn

from model.config import AppRunConfig

if __name__ == "__main__":
    app_run_config = AppRunConfig.from_json()
    uvicorn.run("main:app", **app_run_config.model_dump())
