import argparse
import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

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


def run_benchmark(args: argparse.Namespace):
    """Main function to run the benchmark."""
    benchmark_logger = _setup_benchmark_logger()
    load_dotenv(override=True)

    benchmark_logger.info("🚀 Starting API Generation Agent Benchmark 🚀")
    benchmark_logger.info(f"OpenAPI Spec: {args.openapi_spec}")
    benchmark_logger.info(f"Endpoint: {args.endpoint if args.endpoint else 'All'}")
    benchmark_logger.info(f"LLMs to benchmark: {[llm.name for llm in args.llms]}")

    benchmark_results: List[Dict[str, Any]] = []

    for llm_model_enum in args.llms:
        llm_model_name = llm_model_enum.name
        llm_model_value = llm_model_enum.value
        benchmark_logger.info(f"--- Running benchmark for LLM: {llm_model_name} ({llm_model_value}) ---")

        current_llm_result_data = {
            "llm_model_name": llm_model_name,
            "llm_model_value": llm_model_value,
            "status": "PENDING",
            "error_message": None,
            "metrics": None,
        }

        try:
            # Initialize DI Container and Config
            config_adapter = DevConfigAdapter()  # Uses .env for keys
            processors_adapter = ProcessorsAdapter(config=config_adapter.config)
            container = Container(config_adapter=config_adapter, processors_adapter=processors_adapter)
            container.init_resources()

            config: Config = container.config()

            # Update Config FIRST for the current LLM and paths
            config.update(
                {
                    "api_definition": args.openapi_spec,
                    "endpoints": [args.endpoint] if args.endpoint else [],
                    "generate": GenerationOptions.MODELS_AND_TESTS,
                    "model": llm_model_enum,
                    # data_source will be updated after its determination below
                    "use_existing_framework": False,
                    "list_endpoints": False,
                    "debug": False,  # Agent's logger debug level (True/False)
                }
            )

            # NOW, configure the agent's logger using the updated config
            SrcLogger.configure_logger(config)

            # Determine data source. The logger passed here is for set_data_source internal logging.
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

            benchmark_logger.info("Processing API definition...")
            api_definitions = framework_generator.process_api_definition()

            benchmark_logger.info("Setting up framework structure...")
            framework_generator.setup_framework(api_definitions)
            benchmark_logger.info("Creating .env file for framework...")
            framework_generator.create_env_file(api_definitions)

            benchmark_logger.info(f"Generating {config.generate.value} using {llm_model_name}...")
            framework_generator.generate(api_definitions, config.generate)

            benchmark_logger.info("Running final checks on generated files...")
            test_files_details = framework_generator.run_final_checks(config.generate)  # List[Dict[str,str]]

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
                    # All generated files are considered skipped if run_tests_flow returns None
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
            benchmark_logger.info(f"Metrics for {llm_model_name}: {current_llm_result_data['metrics']}")

        except Exception as e:
            benchmark_logger.error(f"Error during benchmark for LLM {llm_model_name}: {e}", exc_info=True)
            current_llm_result_data["status"] = "FAILED"
            current_llm_result_data["error_message"] = str(e)

        finally:
            benchmark_results.append(current_llm_result_data)
            benchmark_logger.info(f"--- Finished processing LLM: {llm_model_name} ---")

    # Generate and save/print report
    report_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_report_path = os.path.join(args.output_dir, f"benchmark_report_{report_timestamp}.json")
    with open(json_report_path, "w") as f:
        json.dump(benchmark_results, f, indent=4)
    benchmark_logger.info(f"Detailed benchmark report saved to: {json_report_path}")

    summary_report_path = os.path.join(args.output_dir, f"benchmark_summary_{report_timestamp}.txt")
    with open(summary_report_path, "w") as f_summary:
        benchmark_logger.info("--- Benchmark Summary ---")
        f_summary.write("--- Benchmark Summary ---\n")
        for result in benchmark_results:
            summary_lines = [
                f"LLM: {result['llm_model_name']} ({result['llm_model_value']})",
                f"  Status: {result['status']}",
            ]
            if result["status"] == "FAILED":
                summary_lines.append(f"  Error: {result['error_message']}")

            if result["metrics"]:
                metrics = result["metrics"]
                summary_lines.extend(
                    [
                        f"  Generated Test Files: {metrics['generated_test_files_count']}",
                        f"  Files Skipped (Compilation Errors): {metrics['skipped_compilation_files_count']}",
                        f"  Runnable Test Files: {metrics['runnable_test_files_count']}",
                        f"  Total Tests Executed: {metrics['total_tests_executed']}",
                        f"  Passed Tests: {metrics['passed_tests']}",
                        f"  Tests to Review: {metrics['review_tests']}",
                    ]
                )

            for line in summary_lines:
                benchmark_logger.info(line)
                f_summary.write(line + "\n")

    benchmark_logger.info(f"Benchmark summary report saved to: {summary_report_path}")
    benchmark_logger.info("🏁 Benchmark finished 🏁")


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
        "--endpoint",
        type=str,
        help="Optional: Specific endpoint to target. If not provided, all endpoints will be targeted.",
    )
    parser.add_argument(
        "--llms",
        type=parse_llms,
        required=True,
        help=f"Comma-separated list of LLM models to benchmark. " f"Choices: {', '.join(get_llm_choices())}",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmarks/reports",
        help="Directory to save benchmark reports (default: benchmarks/reports).",
    )

    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Configure logger for the benchmark script itself
    _setup_benchmark_logger()

    run_benchmark(args)


if __name__ == "__main__":
    main()
