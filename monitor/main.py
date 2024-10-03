import time
from typing import Tuple, Optional, Dict
import docker
import json
from sqlalchemy import event
from sqlalchemy.orm import Session

PIPELINE_CONTAINER = "chai-oss-pipeline-1"
DATABASE_CONTAINER = "chai-oss-db-1"


def get_container_stats(
    container: docker.models.containers.Container,
) -> Optional[Dict[str, float]]:
    stats = container.stats(stream=False)
    cpu_stats = stats.get("cpu_stats", {})
    precpu_stats = stats.get("precpu_stats", {})
    memory_stats = stats.get("memory_stats", {})

    # in case it exits with a code of 1
    # TODO: i'm not really sure we need to do this, since the container status
    # should change to exited
    if not cpu_stats or not precpu_stats or not memory_stats:
        return None

    cpu_usage = (
        cpu_stats["cpu_usage"]["total_usage"] - precpu_stats["cpu_usage"]["total_usage"]
    )
    system_cpu_usage = cpu_stats["system_cpu_usage"] - precpu_stats["system_cpu_usage"]
    number_cpus = cpu_stats["online_cpus"]
    cpu_percent = (cpu_usage / system_cpu_usage) * number_cpus * 100.0

    memory_usage = memory_stats["usage"] / (1024 * 1024)  # Convert to MB
    memory_limit = memory_stats["limit"] / (1024 * 1024)  # Convert to MB

    return {
        "cpu_percent": cpu_percent,
        "memory_usage": memory_usage,
        "memory_limit": memory_limit,
    }


def read_logs(logs: str) -> Tuple[int, int, float]:
    select_count = 0
    insert_count = 0
    total_sql_time = 0

    for line in logs.split("\n"):
        if "Executed" in line:
            if "SELECT" in line:
                select_count += 1
            elif "INSERT" in line:
                insert_count += 1
            elif "Execution time:" in line:
                total_sql_time += float(line.split("Execution time:")[1].strip())

    return select_count, insert_count, total_sql_time


def monitor_pipeline() -> None:
    client = docker.from_env()
    pipeline_container = None
    database_container = None
    start_time = time.time()

    # detect the containers
    while not pipeline_container and not database_container:
        try:
            pipeline_container = client.containers.get(PIPELINE_CONTAINER)
            database_container = client.containers.get(DATABASE_CONTAINER)
        except docker.errors.NotFound:
            time.sleep(1)

    # get the pipeline container stats
    max_cpu_percent = 0
    max_memory_usage = 0

    while pipeline_container.status == "running":
        stats = get_container_stats(pipeline_container)

        if stats is None:
            print("pipeline container stats not found...exiting")
            break

        max_cpu_percent = max(max_cpu_percent, stats["cpu_percent"])
        max_memory_usage = max(max_memory_usage, stats["memory_usage"])
        time.sleep(1)

    end_time = time.time()
    total_runtime = end_time - start_time

    # parse db logs to extract query info
    # logs = database_container.logs().decode("utf-8")
    # select_count, insert_count, total_sql_time = read_logs(logs)

    # prep report!
    report = {
        "total_runtime": total_runtime,
        "max_cpu_percent": max_cpu_percent,
        "max_memory_usage": max_memory_usage,
        # "select_count": select_count,
        # "insert_count": insert_count,
    }

    print("report:")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    monitor_pipeline()
