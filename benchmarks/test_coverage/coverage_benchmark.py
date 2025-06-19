import argparse
import json
import os
import re
from typing import Dict, List

GROUND_TRUTHS_DIR = os.path.join(os.path.dirname(__file__), "ground_truths")

# TODO: Need to adapt this to read what is actually in the ground truth file, and extract the endpoints
#       and verbs from there.
#       The benchmark should be able to receive the ground truth file and execute the coverage benchmark
#       for each endpoint and verb.
#       I need to implement the model graded eval.


def load_ground_truth(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def sanitize_endpoint(endpoint: str) -> str:
    return endpoint.strip("/").replace("/", "_").replace("{", "").replace("}", "")


def parse_test_file(path: str) -> List[str]:
    with open(path, "r") as f:
        content = f.read()
    suite_match = re.search(r"describe\(\s*[\"']([^\"']+)[\"']", content)
    suite = suite_match.group(1) if suite_match else "Unknown Suite"
    tests = re.findall(r"it\(\s*[\"']([^\"']+)[\"']", content)
    return [f"{suite}::{t}" for t in tests]


def collect_tests(framework_path: str) -> List[str]:
    tests_path = os.path.join(framework_path, "src", "tests")
    pattern = "*.spec.ts"
    collected: List[str] = []
    if not os.path.isdir(tests_path):
        return collected
    for file in os.listdir(tests_path):
        if re.fullmatch(pattern.replace("*", ".*"), file):
            collected.extend(parse_test_file(os.path.join(tests_path, file)))
    return collected


def calculate_coverage(ground_truth_tests: str, actual_tests: List[str]) -> Dict:
    gt_set = set(ground_truth_tests)
    actual_set = set(actual_tests)
    matched = gt_set & actual_set
    extra = actual_set - gt_set
    coverage = round(len(matched) / len(gt_set) * 100, 2) if gt_set else 0.0
    return {"coverage_percent": coverage, "extra_tests": sorted(extra), "matched_tests": sorted(matched)}


def run_test_design_coverage(args: argparse.Namespace):
    ground_truth_tests = load_ground_truth(args.ground_truth)
    actual_tests = collect_tests(args.framework_path)
    results = calculate_coverage(ground_truth_tests, actual_tests)
    print(json.dumps(results, indent=2))
