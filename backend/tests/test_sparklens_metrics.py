from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from backend.analyzer.sparklens_metrics import build_sparklens_report, build_sparklens_report_from_bytes


def _build_zip_bytes(events: list[dict]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("eventlog.json", "\n".join(json.dumps(event) for event in events))
    return buffer.getvalue()


def test_build_sparklens_report_from_bytes_computes_expected_metrics():
    events = [
        {"Event": "SparkListenerLogStart", "Spark Version": "3.3.1"},
        {"Event": "SparkListenerResourceProfileAdded", "Executor Resource Requests": {"cores": {"Amount": 2}, "memory": {"Amount": 4096}, "memoryOverhead": {"Amount": 512}}},
        {"Event": "SparkListenerApplicationStart", "App Name": "demo-app", "App ID": "app-1", "Timestamp": 1000},
        {"Event": "SparkListenerExecutorAdded", "Timestamp": 1000, "Executor ID": "1", "Executor Info": {"Host": "host-a", "Total Cores": 2}},
        {"Event": "SparkListenerExecutorAdded", "Timestamp": 1000, "Executor ID": "2", "Executor Info": {"Host": "host-b", "Total Cores": 2}},
        {"Event": "SparkListenerJobStart", "Job ID": 1, "Submission Time": 1100, "Stage Infos": [{"Stage ID": 10, "Number of Tasks": 4}, {"Stage ID": 11, "Number of Tasks": 2}]},
        {"Event": "SparkListenerStageSubmitted", "Stage Info": {"Stage ID": 10, "Stage Name": "read", "Number of Tasks": 4, "Submission Time": 1100, "Parent IDs": []}},
        {"Event": "SparkListenerStageSubmitted", "Stage Info": {"Stage ID": 11, "Stage Name": "write", "Number of Tasks": 2, "Submission Time": 1400, "Parent IDs": [10]}},
        {"Event": "SparkListenerTaskEnd", "Stage ID": 10, "Task Info": {"Task ID": 1, "Executor ID": "1", "Host": "host-a", "Launch Time": 1100, "Finish Time": 1300, "Failed": False}, "Task Metrics": {"Executor Run Time": 200, "JVM GC Time": 10, "Memory Bytes Spilled": 0, "Disk Bytes Spilled": 0, "Shuffle Read Metrics": {"Remote Bytes Read": 50, "Local Bytes Read": 50, "Fetch Wait Time": 20, "Total Records Read": 5}, "Shuffle Write Metrics": {"Shuffle Bytes Written": 100, "Shuffle Write Time": 30000000, "Shuffle Records Written": 5}, "Input Metrics": {"Bytes Read": 1000, "Records Read": 5}, "Output Metrics": {"Bytes Written": 200, "Records Written": 5}}},
        {"Event": "SparkListenerTaskEnd", "Stage ID": 10, "Task Info": {"Task ID": 2, "Executor ID": "2", "Host": "host-b", "Launch Time": 1100, "Finish Time": 1600, "Failed": False}, "Task Metrics": {"Executor Run Time": 500, "JVM GC Time": 20, "Memory Bytes Spilled": 0, "Disk Bytes Spilled": 10, "Shuffle Read Metrics": {"Remote Bytes Read": 30, "Local Bytes Read": 20, "Fetch Wait Time": 30, "Total Records Read": 2}, "Shuffle Write Metrics": {"Shuffle Bytes Written": 0, "Shuffle Write Time": 0, "Shuffle Records Written": 0}, "Input Metrics": {"Bytes Read": 500, "Records Read": 2}, "Output Metrics": {"Bytes Written": 100, "Records Written": 2}}},
        {"Event": "SparkListenerStageCompleted", "Stage Info": {"Stage ID": 10, "Stage Name": "read", "Number of Tasks": 4, "Submission Time": 1100, "Completion Time": 1600, "Parent IDs": []}},
        {"Event": "SparkListenerTaskEnd", "Stage ID": 11, "Task Info": {"Task ID": 3, "Executor ID": "1", "Host": "host-a", "Launch Time": 1400, "Finish Time": 1800, "Failed": False}, "Task Metrics": {"Executor Run Time": 400, "JVM GC Time": 60, "Memory Bytes Spilled": 0, "Disk Bytes Spilled": 0, "Shuffle Read Metrics": {"Remote Bytes Read": 200, "Local Bytes Read": 100, "Fetch Wait Time": 50, "Total Records Read": 10}, "Shuffle Write Metrics": {"Shuffle Bytes Written": 600, "Shuffle Write Time": 60000000, "Shuffle Records Written": 10}, "Input Metrics": {"Bytes Read": 0, "Records Read": 0}, "Output Metrics": {"Bytes Written": 300, "Records Written": 10}}},
        {"Event": "SparkListenerStageCompleted", "Stage Info": {"Stage ID": 11, "Stage Name": "write", "Number of Tasks": 2, "Submission Time": 1400, "Completion Time": 1800, "Parent IDs": [10]}},
        {"Event": "SparkListenerJobEnd", "Job ID": 1, "Completion Time": 1800},
        {"Event": "SparkListenerExecutorRemoved", "Timestamp": 2000, "Executor ID": "1"},
        {"Event": "SparkListenerExecutorRemoved", "Timestamp": 2000, "Executor ID": "2"},
        {"Event": "SparkListenerApplicationEnd", "Timestamp": 2000},
    ]

    zip_bytes = _build_zip_bytes(events)
    report = build_sparklens_report_from_bytes(zip_bytes)
    zip_path = Path(__file__).parent / "_tmp_sparklens_demo.zip"
    zip_path.write_bytes(zip_bytes)
    try:
        report_from_path = build_sparklens_report(str(zip_path))
    finally:
        zip_path.unlink(missing_ok=True)

    assert report["app"]["id"] == "app-1"
    assert report["app"]["spark_version"] == "3.3.1"
    assert report["cluster"]["executor_count"] == 2
    assert report["cluster"]["cores_per_executor"] == 2
    assert report["cluster"]["total_cores"] == 4
    assert report["cluster"]["available_core_hours"] == 0.001
    assert report["cluster"]["used_core_hours"] == 0.0
    assert len(report["jobs"]) == 1
    assert len(report["stages"]) == 2
    assert report["stages"][0]["stage_id"] == 10
    assert report["stages"][0]["task_run_ms_total"] == 700
    assert report["stages"][0]["task_count_accepted"] == 2
    assert report["stages"][0]["task_count_filtered"] == 0
    assert report["stages"][0]["one_core_hours"]["used_pct"] == 35.0
    assert report["stages"][0]["skew"]["task_skew"] == 1.0
    assert report["stages"][0]["skew"]["avg_task_ms"] == 350.0
    assert report["stages"][0]["skew"]["skew_avg_ratio"] == 1.429
    assert report["stages"][1]["time_distribution"]["gc_pct"] == 15.0
    assert report["stages"][1]["time_distribution"]["shuffle_write_pct"] == 15.0
    assert report["stages"][1]["time_distribution"]["shuffle_read_fetch_pct"] == 12.5
    assert report["stages"][1]["io"]["oi_ratio"] == 3.0
    # Per-stage percentages
    assert report["stages"][0]["percentages"]["wall_clock_pct"] > 0
    assert report["stages"][0]["percentages"]["task_runtime_pct"] > 0
    # Memory section
    assert "memory" in report["stages"][0]
    assert report["stages"][0]["memory"]["spill_disk_bytes"] == 10
    # Driver analysis
    assert "driver_analysis" in report
    assert report["driver_analysis"]["driver_time_ms"] == 300
    assert report["driver_analysis"]["driver_pct"] == 30.0
    assert len(report["driver_analysis"]["driver_intervals"]) == 2  # pre + post
    # Environment
    assert "environment" in report
    assert report["host_analysis"]["host-a"]["task_count"] == 2
    assert report["job_timelines"][0]["parallel_groups"][0]["stages"] == [10]
    assert report["job_timelines"][0]["parallel_groups"][1]["stages"] == [11]
    assert report["top_bottlenecks"][0]["stage_id"] == 10
    assert report["llm_context"]["app"]["id"] == "app-1"
    assert "driver_analysis" in report["llm_context"]
    assert "environment" in report["llm_context"]
    assert report_from_path["cluster"] == report["cluster"]


def test_failed_and_speculative_tasks_are_filtered():
    """Failed and speculative tasks must not contribute to metrics."""
    events = [
        {"Event": "SparkListenerApplicationStart", "App Name": "filter-test", "App ID": "app-filter", "Timestamp": 1000},
        {"Event": "SparkListenerExecutorAdded", "Timestamp": 1000, "Executor ID": "1", "Executor Info": {"Host": "h1", "Total Cores": 2}},
        {"Event": "SparkListenerJobStart", "Job ID": 0, "Submission Time": 1000, "Stage Infos": [{"Stage ID": 0, "Number of Tasks": 3}]},
        {"Event": "SparkListenerStageSubmitted", "Stage Info": {"Stage ID": 0, "Stage Name": "s0", "Number of Tasks": 3, "Submission Time": 1000, "Parent IDs": []}},
        # Good task
        {"Event": "SparkListenerTaskEnd", "Stage ID": 0, "Stage Attempt ID": 0,
         "Task Info": {"Task ID": 1, "Executor ID": "1", "Host": "h1", "Launch Time": 1000, "Finish Time": 1200, "Failed": False},
         "Task Metrics": {"Executor Run Time": 200, "JVM GC Time": 0, "Memory Bytes Spilled": 0, "Disk Bytes Spilled": 0,
                          "Shuffle Read Metrics": {}, "Shuffle Write Metrics": {}, "Input Metrics": {"Bytes Read": 100}, "Output Metrics": {}}},
        # Failed task — should be excluded
        {"Event": "SparkListenerTaskEnd", "Stage ID": 0, "Stage Attempt ID": 0,
         "Task Info": {"Task ID": 2, "Executor ID": "1", "Host": "h1", "Launch Time": 1000, "Finish Time": 1500, "Failed": True},
         "Task Metrics": {"Executor Run Time": 500, "JVM GC Time": 0, "Memory Bytes Spilled": 0, "Disk Bytes Spilled": 0,
                          "Shuffle Read Metrics": {}, "Shuffle Write Metrics": {}, "Input Metrics": {"Bytes Read": 9999}, "Output Metrics": {}}},
        # Speculative task — should be excluded
        {"Event": "SparkListenerTaskEnd", "Stage ID": 0, "Stage Attempt ID": 0,
         "Task Info": {"Task ID": 3, "Executor ID": "1", "Host": "h1", "Launch Time": 1000, "Finish Time": 1300, "Failed": False, "Speculative": True},
         "Task Metrics": {"Executor Run Time": 300, "JVM GC Time": 0, "Memory Bytes Spilled": 0, "Disk Bytes Spilled": 0,
                          "Shuffle Read Metrics": {}, "Shuffle Write Metrics": {}, "Input Metrics": {"Bytes Read": 8888}, "Output Metrics": {}}},
        {"Event": "SparkListenerStageCompleted", "Stage Info": {"Stage ID": 0, "Submission Time": 1000, "Completion Time": 1500}},
        {"Event": "SparkListenerJobEnd", "Job ID": 0, "Completion Time": 1500},
        {"Event": "SparkListenerApplicationEnd", "Timestamp": 2000},
    ]
    report = build_sparklens_report_from_bytes(_build_zip_bytes(events))
    stage = report["stages"][0]
    # Only the good task should be counted
    assert stage["task_count_accepted"] == 1
    assert stage["task_count_filtered"] == 2
    assert stage["task_run_ms_total"] == 200
    assert stage["io"]["input_bytes"] == 100  # not 100+9999+8888


def test_stage_attempt_uses_latest_only():
    """When a stage has multiple attempts, only the latest attempt's tasks are used."""
    events = [
        {"Event": "SparkListenerApplicationStart", "App Name": "retry-test", "App ID": "app-retry", "Timestamp": 1000},
        {"Event": "SparkListenerExecutorAdded", "Timestamp": 1000, "Executor ID": "1", "Executor Info": {"Host": "h1", "Total Cores": 2}},
        {"Event": "SparkListenerJobStart", "Job ID": 0, "Submission Time": 1000, "Stage Infos": [{"Stage ID": 0, "Number of Tasks": 1}]},
        # Attempt 0 — will be superseded
        {"Event": "SparkListenerStageSubmitted", "Stage Info": {"Stage ID": 0, "Stage Attempt ID": 0, "Stage Name": "s0", "Number of Tasks": 1, "Submission Time": 1000, "Parent IDs": []}},
        {"Event": "SparkListenerTaskEnd", "Stage ID": 0, "Stage Attempt ID": 0,
         "Task Info": {"Task ID": 1, "Executor ID": "1", "Host": "h1", "Launch Time": 1000, "Finish Time": 1200, "Failed": False},
         "Task Metrics": {"Executor Run Time": 200, "JVM GC Time": 0, "Memory Bytes Spilled": 0, "Disk Bytes Spilled": 0,
                          "Shuffle Read Metrics": {}, "Shuffle Write Metrics": {}, "Input Metrics": {"Bytes Read": 100}, "Output Metrics": {}}},
        # Attempt 1 — should replace attempt 0
        {"Event": "SparkListenerStageSubmitted", "Stage Info": {"Stage ID": 0, "Stage Attempt ID": 1, "Stage Name": "s0-retry", "Number of Tasks": 1, "Submission Time": 1300, "Parent IDs": []}},
        {"Event": "SparkListenerTaskEnd", "Stage ID": 0, "Stage Attempt ID": 1,
         "Task Info": {"Task ID": 2, "Executor ID": "1", "Host": "h1", "Launch Time": 1300, "Finish Time": 1600, "Failed": False},
         "Task Metrics": {"Executor Run Time": 300, "JVM GC Time": 10, "Memory Bytes Spilled": 0, "Disk Bytes Spilled": 0,
                          "Shuffle Read Metrics": {}, "Shuffle Write Metrics": {}, "Input Metrics": {"Bytes Read": 500}, "Output Metrics": {}}},
        {"Event": "SparkListenerStageCompleted", "Stage Info": {"Stage ID": 0, "Stage Attempt ID": 1, "Submission Time": 1300, "Completion Time": 1600}},
        {"Event": "SparkListenerJobEnd", "Job ID": 0, "Completion Time": 1600},
        {"Event": "SparkListenerApplicationEnd", "Timestamp": 2000},
    ]
    report = build_sparklens_report_from_bytes(_build_zip_bytes(events))
    stage = report["stages"][0]
    # Should only reflect attempt 1 data
    assert stage["task_run_ms_total"] == 300
    assert stage["io"]["input_bytes"] == 500
    assert stage["task_count_accepted"] == 1


def test_driver_overhead_bottleneck_detected():
    """When driver time exceeds 20% of app time, a driver_overhead bottleneck should be flagged."""
    events = [
        {"Event": "SparkListenerApplicationStart", "App Name": "driver-test", "App ID": "app-drv", "Timestamp": 0},
        {"Event": "SparkListenerExecutorAdded", "Timestamp": 0, "Executor ID": "1", "Executor Info": {"Host": "h1", "Total Cores": 2}},
        # Job runs from 500-600 (only 10% of 1000ms total)
        {"Event": "SparkListenerJobStart", "Job ID": 0, "Submission Time": 500, "Stage Infos": [{"Stage ID": 0, "Number of Tasks": 1}]},
        {"Event": "SparkListenerStageSubmitted", "Stage Info": {"Stage ID": 0, "Stage Name": "s0", "Number of Tasks": 1, "Submission Time": 500, "Parent IDs": []}},
        {"Event": "SparkListenerTaskEnd", "Stage ID": 0, "Stage Attempt ID": 0,
         "Task Info": {"Task ID": 1, "Executor ID": "1", "Host": "h1", "Launch Time": 500, "Finish Time": 600, "Failed": False},
         "Task Metrics": {"Executor Run Time": 100, "JVM GC Time": 0, "Memory Bytes Spilled": 0, "Disk Bytes Spilled": 0,
                          "Shuffle Read Metrics": {}, "Shuffle Write Metrics": {}, "Input Metrics": {}, "Output Metrics": {}}},
        {"Event": "SparkListenerStageCompleted", "Stage Info": {"Stage ID": 0, "Submission Time": 500, "Completion Time": 600}},
        {"Event": "SparkListenerJobEnd", "Job ID": 0, "Completion Time": 600},
        {"Event": "SparkListenerApplicationEnd", "Timestamp": 1000},
    ]
    report = build_sparklens_report_from_bytes(_build_zip_bytes(events))
    assert report["driver_analysis"]["driver_pct"] == 90.0
    driver_bottlenecks = [b for b in report["top_bottlenecks"] if b["type"] == "driver_overhead"]
    assert len(driver_bottlenecks) == 1
    assert driver_bottlenecks[0]["metric_value"] == 90.0


def test_spill_bottleneck_detected():
    """Disk spill > 0 should generate a spill bottleneck."""
    events = [
        {"Event": "SparkListenerApplicationStart", "App Name": "spill-test", "App ID": "app-spill", "Timestamp": 0},
        {"Event": "SparkListenerExecutorAdded", "Timestamp": 0, "Executor ID": "1", "Executor Info": {"Host": "h1", "Total Cores": 2}},
        {"Event": "SparkListenerJobStart", "Job ID": 0, "Submission Time": 0, "Stage Infos": [{"Stage ID": 0, "Number of Tasks": 1}]},
        {"Event": "SparkListenerStageSubmitted", "Stage Info": {"Stage ID": 0, "Stage Name": "s0", "Number of Tasks": 1, "Submission Time": 0, "Parent IDs": []}},
        {"Event": "SparkListenerTaskEnd", "Stage ID": 0, "Stage Attempt ID": 0,
         "Task Info": {"Task ID": 1, "Executor ID": "1", "Host": "h1", "Launch Time": 0, "Finish Time": 1000, "Failed": False},
         "Task Metrics": {"Executor Run Time": 1000, "JVM GC Time": 0, "Memory Bytes Spilled": 500000, "Disk Bytes Spilled": 200000,
                          "Shuffle Read Metrics": {}, "Shuffle Write Metrics": {}, "Input Metrics": {}, "Output Metrics": {}}},
        {"Event": "SparkListenerStageCompleted", "Stage Info": {"Stage ID": 0, "Submission Time": 0, "Completion Time": 1000}},
        {"Event": "SparkListenerJobEnd", "Job ID": 0, "Completion Time": 1000},
        {"Event": "SparkListenerApplicationEnd", "Timestamp": 1000},
    ]
    report = build_sparklens_report_from_bytes(_build_zip_bytes(events))
    spill_bottlenecks = [b for b in report["top_bottlenecks"] if b["type"] == "spill"]
    assert len(spill_bottlenecks) == 1
    assert report["stages"][0]["memory"]["spill_disk_bytes"] == 200000


def test_environment_properties_captured():
    """SparkListenerEnvironmentUpdate properties should appear in the report."""
    events = [
        {"Event": "SparkListenerApplicationStart", "App Name": "env-test", "App ID": "app-env", "Timestamp": 0},
        {"Event": "SparkListenerEnvironmentUpdate", "Spark Properties": {
            "spark.executor.instances": "8",
            "spark.executor.memory": "4g",
            "spark.executor.cores": "4",
            "spark.sql.shuffle.partitions": "200",
            "spark.sql.adaptive.enabled": "true",
            "some.other.prop": "ignored",
        }},
        {"Event": "SparkListenerExecutorAdded", "Timestamp": 0, "Executor ID": "1", "Executor Info": {"Host": "h1", "Total Cores": 4}},
        {"Event": "SparkListenerJobStart", "Job ID": 0, "Submission Time": 0, "Stage Infos": [{"Stage ID": 0, "Number of Tasks": 1}]},
        {"Event": "SparkListenerStageSubmitted", "Stage Info": {"Stage ID": 0, "Stage Name": "s0", "Number of Tasks": 1, "Submission Time": 0, "Parent IDs": []}},
        {"Event": "SparkListenerTaskEnd", "Stage ID": 0, "Stage Attempt ID": 0,
         "Task Info": {"Task ID": 1, "Executor ID": "1", "Host": "h1", "Launch Time": 0, "Finish Time": 100, "Failed": False},
         "Task Metrics": {"Executor Run Time": 100, "JVM GC Time": 0, "Memory Bytes Spilled": 0, "Disk Bytes Spilled": 0,
                          "Shuffle Read Metrics": {}, "Shuffle Write Metrics": {}, "Input Metrics": {}, "Output Metrics": {}}},
        {"Event": "SparkListenerStageCompleted", "Stage Info": {"Stage ID": 0, "Submission Time": 0, "Completion Time": 100}},
        {"Event": "SparkListenerJobEnd", "Job ID": 0, "Completion Time": 100},
        {"Event": "SparkListenerApplicationEnd", "Timestamp": 1000},
    ]
    report = build_sparklens_report_from_bytes(_build_zip_bytes(events))
    env = report["environment"]
    assert env["spark.executor.instances"] == "8"
    assert env["spark.executor.memory"] == "4g"
    assert env["spark.sql.shuffle.partitions"] == "200"
    assert "some.other.prop" not in env


def test_peak_execution_memory_tracked():
    """Peak execution memory should be the max across all accepted tasks in a stage."""
    events = [
        {"Event": "SparkListenerApplicationStart", "App Name": "mem-test", "App ID": "app-mem", "Timestamp": 0},
        {"Event": "SparkListenerExecutorAdded", "Timestamp": 0, "Executor ID": "1", "Executor Info": {"Host": "h1", "Total Cores": 2}},
        {"Event": "SparkListenerJobStart", "Job ID": 0, "Submission Time": 0, "Stage Infos": [{"Stage ID": 0, "Number of Tasks": 2}]},
        {"Event": "SparkListenerStageSubmitted", "Stage Info": {"Stage ID": 0, "Stage Name": "s0", "Number of Tasks": 2, "Submission Time": 0, "Parent IDs": []}},
        {"Event": "SparkListenerTaskEnd", "Stage ID": 0, "Stage Attempt ID": 0,
         "Task Info": {"Task ID": 1, "Executor ID": "1", "Host": "h1", "Launch Time": 0, "Finish Time": 100, "Failed": False},
         "Task Metrics": {"Executor Run Time": 100, "Peak Execution Memory": 1048576, "JVM GC Time": 0,
                          "Memory Bytes Spilled": 0, "Disk Bytes Spilled": 0,
                          "Shuffle Read Metrics": {}, "Shuffle Write Metrics": {}, "Input Metrics": {}, "Output Metrics": {}}},
        {"Event": "SparkListenerTaskEnd", "Stage ID": 0, "Stage Attempt ID": 0,
         "Task Info": {"Task ID": 2, "Executor ID": "1", "Host": "h1", "Launch Time": 0, "Finish Time": 100, "Failed": False},
         "Task Metrics": {"Executor Run Time": 100, "Peak Execution Memory": 5242880, "JVM GC Time": 0,
                          "Memory Bytes Spilled": 0, "Disk Bytes Spilled": 0,
                          "Shuffle Read Metrics": {}, "Shuffle Write Metrics": {}, "Input Metrics": {}, "Output Metrics": {}}},
        {"Event": "SparkListenerStageCompleted", "Stage Info": {"Stage ID": 0, "Submission Time": 0, "Completion Time": 100}},
        {"Event": "SparkListenerJobEnd", "Job ID": 0, "Completion Time": 100},
        {"Event": "SparkListenerApplicationEnd", "Timestamp": 1000},
    ]
    report = build_sparklens_report_from_bytes(_build_zip_bytes(events))
    assert report["stages"][0]["memory"]["peak_execution_memory"] == 5242880


def test_cpu_pct_calculated():
    """CPU percentage should be computed from Executor CPU Time (ns) / Executor Run Time (ms)."""
    events = [
        {"Event": "SparkListenerApplicationStart", "App Name": "cpu-test", "App ID": "app-cpu", "Timestamp": 0},
        {"Event": "SparkListenerExecutorAdded", "Timestamp": 0, "Executor ID": "1", "Executor Info": {"Host": "h1", "Total Cores": 2}},
        {"Event": "SparkListenerJobStart", "Job ID": 0, "Submission Time": 0, "Stage Infos": [{"Stage ID": 0, "Number of Tasks": 1}]},
        {"Event": "SparkListenerStageSubmitted", "Stage Info": {"Stage ID": 0, "Stage Name": "s0", "Number of Tasks": 1, "Submission Time": 0, "Parent IDs": []}},
        {"Event": "SparkListenerTaskEnd", "Stage ID": 0, "Stage Attempt ID": 0,
         "Task Info": {"Task ID": 1, "Executor ID": "1", "Host": "h1", "Launch Time": 0, "Finish Time": 1000, "Failed": False},
         "Task Metrics": {"Executor Run Time": 1000, "Executor CPU Time": 800000000, "JVM GC Time": 0,
                          "Memory Bytes Spilled": 0, "Disk Bytes Spilled": 0,
                          "Shuffle Read Metrics": {}, "Shuffle Write Metrics": {}, "Input Metrics": {}, "Output Metrics": {}}},
        {"Event": "SparkListenerStageCompleted", "Stage Info": {"Stage ID": 0, "Submission Time": 0, "Completion Time": 1000}},
        {"Event": "SparkListenerJobEnd", "Job ID": 0, "Completion Time": 1000},
        {"Event": "SparkListenerApplicationEnd", "Timestamp": 1000},
    ]
    report = build_sparklens_report_from_bytes(_build_zip_bytes(events))
    # 800_000_000 ns CPU / (1000 ms * 1_000_000) = 80%
    assert report["stages"][0]["time_distribution"]["cpu_pct"] == 80.0
