from __future__ import annotations

from celery import Celery

from stock_strategy_growth_crew.bootstrap import initialize_database, seed_demo_data
from stock_strategy_growth_crew.db import SessionLocal
from stock_strategy_growth_crew.main import demo_run
from stock_strategy_growth_crew.settings import settings


celery_app = Celery("robot_company", broker=settings.redis_url, backend=settings.redis_url)


@celery_app.task(name="robot_company.seed_demo_data")
def seed_demo_data_task() -> str:
    initialize_database()
    with SessionLocal() as db:
        seed_demo_data(db)
    return "seeded"


@celery_app.task(name="robot_company.generate_demo_outputs")
def generate_demo_outputs_task() -> str:
    demo_run()
    return "generated"


def run_worker() -> None:
    celery_app.worker_main(
        [
            "worker",
            "--loglevel=INFO",
        ]
    )


if __name__ == "__main__":
    run_worker()
