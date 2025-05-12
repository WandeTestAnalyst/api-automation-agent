import argparse
import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from tabulate import tabulate
import time

# Add project root to Python path to allow importing project modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from dotenv import load_dotenv  # noqa: E402

from src.configuration.models import Model  # noqa: E402
from src.utils.logger import Logger as SrcLogger  # noqa: E402
from src.configuration.config import Config, GenerationOptions  # noqa: E402
from src.container import Container  # noqa: E402
from src.adapters.config_adapter import DevConfigAdapter  # noqa: E402
from src.adapters.processors_adapter import ProcessorsAdapter  # noqa: E402
from src.configuration.data_sources import get_processor_for_data_source  # noqa: E402
from src.processors.api_processor import APIProcessor  # noqa: E402
from src.framework_generator import FrameworkGenerator  # noqa: E402
from src.test_controller import TestController, TestRunMetrics  # noqa: E402


def _setup_benchmark_logger(level=logging.INFO):
    """Sets up a basic logger for the benchmark script itself."""
    logger = logging.getLogger("benchmark_runner")
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_llm_choices() -> List[str]:
    """Returns a list of available LLM model names."""
    return [model.name for model in Model]


def parse_llms(llm_string: str) -> List[Model]:
    """Parses a comma-separated string of LLM names into a list of Model enums."""
    llm_names = [name.strip() for name in llm_string.split(",")]
    valid_llms = []
    available_models = get_llm_choices()
    for name in llm_names:
        try:
            valid_llms.append(Model[name])
        except KeyError:
            raise argparse.ArgumentTypeError(
                f"Invalid LLM model: {name}. Choices are: {', '.join(available_models)}"
            )
    if not valid_llms:
        raise argparse.ArgumentTypeError("At least one LLM model must be specified.")
    return valid_llms


def _run_benchmark_for_llm(
    llm_model_enum: Model, args: argparse.Namespace, benchmark_logger: logging.Logger
) -> Dict[str, Any]:
    """Runs the benchmark for a single LLM model."""
    start_time = time.monotonic()
    llm_model_value = llm_model_enum.value

    current_llm_result_data = {
        "llm_model_value": llm_model_value,
        "api_definition": args.openapi_spec,
        "endpoints": args.endpoints if args.endpoints else [],
        "status": "PENDING",
        "error_message": None,
        "metrics": None,
        "duration_seconds": None,
    }

    try:
        # Initialize DI Container and Config
        config_adapter = DevConfigAdapter()  # Uses .env for keys
        processors_adapter = ProcessorsAdapter(config=config_adapter.config)
        container = Container(config_adapter=config_adapter, processors_adapter=processors_adapter)
        container.init_resources()

        config: Config = container.config()

        config.update(
            {
                "api_definition": args.openapi_spec,
                "destination_folder": f"{config.destination_folder}_benchmark_{llm_model_value}",
                "endpoints": args.endpoints if args.endpoints else [],
                "generate": GenerationOptions.MODELS_AND_TESTS,
                "model": llm_model_enum,
                "use_existing_framework": False,
                "list_endpoints": False,
                "debug": False,
            }
        )

        SrcLogger.configure_logger(config)

        agent_setup_logger = SrcLogger.get_logger(__name__ + ".agent_setup")
        data_source = APIProcessor.set_data_source(args.openapi_spec, agent_setup_logger)
        config.update({"data_source": data_source})

        benchmark_logger.info(
            f"Agent Config: Dest='{config.destination_folder}', Model='{config.model.value}', "
            f"Src='{config.data_source}', Debug={config.debug}"
        )

        api_processor_instance = get_processor_for_data_source(data_source, container)
        container.api_processor.override(api_processor_instance)

        framework_generator: FrameworkGenerator = container.framework_generator()
        test_controller: TestController = container.test_controller()

        api_definitions = framework_generator.process_api_definition()
        framework_generator.setup_framework(api_definitions)
        framework_generator.create_env_file(api_definitions)
        framework_generator.generate(api_definitions, config.generate)
        test_files_details = framework_generator.run_final_checks(config.generate)

        metrics_data: TestRunMetrics
        if not test_files_details:
            benchmark_logger.warning(
                "No test files were generated or passed final checks. Skipping test run."
            )
            metrics_data = TestRunMetrics(total_tests=0, passed_tests=0, review_tests=0, skipped_files=0)
        else:
            benchmark_logger.info(
                f"Proceeding to run tests for {len(test_files_details)} generated file(s)..."
            )
            metrics_result: Optional[TestRunMetrics] = test_controller.run_tests_flow(
                test_files_details, interactive=False
            )
            if metrics_result:
                metrics_data = metrics_result
            else:
                benchmark_logger.warning(
                    "Test run did not return metrics (e.g. skipped). Assuming 0 for all metrics."
                )
                metrics_data = TestRunMetrics(
                    total_tests=0, passed_tests=0, review_tests=0, skipped_files=len(test_files_details)
                )

        current_llm_result_data["metrics"] = {
            "generated_test_files_count": len(test_files_details) if test_files_details else 0,
            "skipped_compilation_files_count": metrics_data.skipped_files,
            "runnable_test_files_count": (len(test_files_details) if test_files_details else 0)
            - metrics_data.skipped_files,
            "total_tests_executed": metrics_data.total_tests,
            "passed_tests": metrics_data.passed_tests,
            "review_tests": metrics_data.review_tests,
        }

        current_llm_result_data["status"] = "COMPLETED"
        current_llm_result_data["generated_framework_path"] = config.destination_folder

    except Exception as e:
        benchmark_logger.error(f"Error during benchmark for LLM {llm_model_value}: {e}", exc_info=True)
        current_llm_result_data["status"] = "FAILED"
        current_llm_result_data["error_message"] = str(e)
    finally:
        end_time = time.monotonic()
        duration = end_time - start_time
        current_llm_result_data["duration_seconds"] = round(duration, 2)

    return current_llm_result_data


def _format_duration_for_display(duration_seconds: Optional[float]) -> str:
    """Formats duration in seconds to a human-readable string 'Xh Ym Zs', 'Ym Zs' or 'Ys'."""
    if isinstance(duration_seconds, (int, float)):
        hours = int(duration_seconds // 3600)
        remaining_seconds = duration_seconds % 3600
        minutes = int(remaining_seconds // 60)
        seconds = int(remaining_seconds % 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"
    return "N/A"


def _generate_reports(
    benchmark_results: List[Dict[str, Any]],
    output_dir: str,
    benchmark_logger: logging.Logger,
    report_timestamp: str,
    args: argparse.Namespace,
):
    """Generates and saves/prints benchmark reports."""
    json_report_path = os.path.join(output_dir, f"benchmark_report_{report_timestamp}.json")
    with open(json_report_path, "w") as f:
        json.dump(benchmark_results, f, indent=4)
    benchmark_logger.info(f"Detailed benchmark report saved to: {json_report_path}\n")

    print("--- Benchmark Summary Table ---\n")
    print(f"OpenAPI Spec: {args.openapi_spec}")
    print(f"Endpoints   : {', '.join(args.endpoints) if args.endpoints else 'All'}", "\n")

    headers = [
        "LLM Model",
        "Test Files",
        "Skipped Files",
        "Run Files",
        "Tests Run",
        "Passed",
        "Review",
        "Duration",
    ]
    table_data = []
    for result in benchmark_results:
        metrics = result.get("metrics")
        duration_seconds = result.get("duration_seconds")
        formatted_duration = _format_duration_for_display(duration_seconds)

        row = [
            result.get("llm_model_value", "N/A"),
        ]
        if metrics:
            row.extend(
                [
                    metrics.get("generated_test_files_count", "N/A"),
                    metrics.get("skipped_compilation_files_count", "N/A"),
                    metrics.get("runnable_test_files_count", "N/A"),
                    metrics.get("total_tests_executed", "N/A"),
                    metrics.get("passed_tests", "N/A"),
                    metrics.get("review_tests", "N/A"),
                    formatted_duration,
                ]
            )
        else:
            row.extend(["N/A"] * 6)
            row.append(formatted_duration)

        table_data.append(row)

    if table_data:
        table_string = tabulate(table_data, headers=headers, tablefmt="grid")
        for line in table_string.splitlines():
            print(line)

        print(
            f"\nFor detailed benchmark metadata, see the JSON report at: {os.path.normpath(json_report_path)}"
        )
    else:
        benchmark_logger.info("No benchmark data to display in table.")


def run_benchmark(args: argparse.Namespace):
    """Main function to run the benchmark."""
    benchmark_logger = _setup_benchmark_logger()
    load_dotenv(override=True)

    benchmark_logger.info("Starting API Generation Agent Benchmark")

    benchmark_results: List[Dict[str, Any]] = []
    report_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.load_results:
        benchmark_logger.info(f"Attempting to load results from: {args.load_results}")
        try:
            with open(args.load_results, "r") as f:
                benchmark_results = json.load(f)
            benchmark_logger.info(
                f"Successfully loaded {len(benchmark_results)} result(s) from {args.load_results}"
            )
        except FileNotFoundError:
            benchmark_logger.error(f"Error: Results file not found at {args.load_results}. Exiting.")
            sys.exit(1)
        except json.JSONDecodeError:
            benchmark_logger.error(
                f"Error: Could not decode JSON from {args.load_results}. "
                f"Ensure it is a valid JSON report. Exiting."
            )
            sys.exit(1)
    else:
        benchmark_logger.info(f"OpenAPI Spec: {args.openapi_spec}")
        benchmark_logger.info(f"Endpoints: {', '.join(args.endpoints) if args.endpoints else 'All'}")
        benchmark_logger.info(f"LLMs to benchmark: {[llm.value for llm in args.llms]}")

        for llm_model_enum in args.llms:
            benchmark_logger.info(f"--- Running benchmark for LLM: {llm_model_enum.value} ---")

            result_data = _run_benchmark_for_llm(llm_model_enum, args, benchmark_logger)
            benchmark_results.append(result_data)

            benchmark_logger.info(f"--- Finished processing LLM: {llm_model_enum.value} ---")

    if not benchmark_results:
        benchmark_logger.warning("No benchmark results to process. Exiting.")
        return

    _generate_reports(benchmark_results, args.output_dir, benchmark_logger, report_timestamp, args)

    print("\n🏁 Benchmark finished 🏁")


def main():
    """Parses CLI arguments and starts the benchmark."""
    parser = argparse.ArgumentParser(description="API Generation Agent Benchmark CLI")

    parser.add_argument(
        "--openapi-spec",
        type=str,
        required=True,
        help="Path to the OpenAPI specification file (JSON or YAML).",
    )
    parser.add_argument(
        "--endpoints",
        type=str,
        nargs="+",
        help="Optional: Specific endpoint(s) to target. If not provided, all endpoints will be targeted.",
    )
    parser.add_argument(
        "--llms",
        type=parse_llms,
        required=True,
        help=f"Comma-separated list of LLM models to benchmark. " f"Choices: {', '.join(get_llm_choices())}.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmarks/reports",
        help="Directory to save benchmark reports (default: benchmarks/reports).",
    )
    parser.add_argument(
        "--load-results",
        type=str,
        default=None,
        help="Optional: Path to a previously generated JSON report file to load results from. "
        "If provided, the benchmark generation and execution steps are skipped.",
    )

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    _setup_benchmark_logger()
    run_benchmark(args)


if __name__ == "__main__":
    main()
