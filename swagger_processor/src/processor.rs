use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use pyo3::exceptions::PyException;
use std::collections::HashMap;
use std::fs;
use std::time::Instant;
use reqwest;
use serde_json::{self, Value};
use serde_yaml;
use tokio;
use rayon::prelude::*;

use crate::types::{APIDef, APIPath, APIVerb, PathGroup};
use crate::logger::ThreadSafeLogger;
use crate::utils::{normalize_path, get_root_path};

#[pyclass]
pub struct APIDefinitionProcessor {
    logger: Option<ThreadSafeLogger>,
}

#[pymethods]
impl APIDefinitionProcessor {
    #[new]
    fn new(logger: Option<Py<PyAny>>) -> Self {
        APIDefinitionProcessor {
            logger: logger.map(ThreadSafeLogger::new)
        }
    }

    /// Processes an API definition by loading, splitting, and merging its components.
    ///
    /// Args:
    ///     api_definition_path (str): URL or path to the API definition.
    ///
    /// Returns:
    ///     list: List of dictionaries containing the processed API definitions.
    fn process_api_definition(&self, py: Python, api_definition_path: &str) -> PyResult<Py<PyList>> {
        if let Some(ref logger) = self.logger {
            logger.info(py, "Starting API processing");
        }

        let start_time = Instant::now();

        // Load, split, and merge using optimized Rust with multithreading
        let raw_definition = self.load_definition(py, api_definition_path)?;
        let split_definitions = self.split_definition_parallel(py, &raw_definition)?;
        let merged_definitions = self.merge_definitions_parallel(py, split_definitions)?;

        // Convert results to Python format
        let result_list = PyList::empty(py);

        // Convert definitions to Python dictionaries
        for definition in merged_definitions {
            let py_dict = PyDict::new(py);
            match definition {
                APIDef::Path(path) => {
                    py_dict.set_item("type", "path")?;
                    py_dict.set_item("path", &path.path)?;
                    py_dict.set_item("yaml", &path.yaml)?;
                }
                APIDef::Verb(verb) => {
                    py_dict.set_item("type", "verb")?;
                    py_dict.set_item("verb", &verb.verb)?;
                    py_dict.set_item("path", &verb.path)?;
                    py_dict.set_item("root_path", &verb.root_path)?;
                    py_dict.set_item("yaml", &verb.yaml)?;
                }
            }
            result_list.append(py_dict)?;
        }

        if let Some(ref logger) = self.logger {
            logger.info(py, "Successfully processed API definition.");
            let elapsed = start_time.elapsed();
            let time_msg = format!("Time taken to process API definition: {:.2} seconds", elapsed.as_secs_f64());
            logger.info(py, &time_msg);
        }

        Ok(result_list.into())
    }
}

impl APIDefinitionProcessor {
    // Optimized load with connection pooling and better error handling
    fn load_definition(&self, py: Python, api_definition: &str) -> PyResult<Value> {
        if let Some(ref logger) = self.logger {
            let debug_msg = format!("Loading API definition from: {}", api_definition);
            logger.debug(py, &debug_msg);
        }

        if api_definition.starts_with("http") &&
            (api_definition.ends_with(".json") ||
                api_definition.ends_with(".yaml") ||
                api_definition.ends_with(".yml")) {

            if let Some(ref logger) = self.logger {
                let debug_msg = format!("Loading API definition from URL: {}", api_definition);
                logger.debug(py, &debug_msg);
            }

            let rt = match tokio::runtime::Runtime::new() {
                Ok(runtime) => runtime,
                Err(e) => {
                    let error_msg = format!("Failed to create async runtime: {}", e);
                    if let Some(ref logger) = self.logger {
                        logger.error(py, &error_msg);
                    }
                    return Err(PyException::new_err(error_msg));
                }
            };

            // Use a client with connection pooling and timeout
            let client = match reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(5)) // Reduced timeout for tests
                .build() {
                    Ok(client) => client,
                    Err(e) => {
                        let error_msg = format!("Failed to create HTTP client: {}", e);
                        if let Some(ref logger) = self.logger {
                            logger.error(py, &error_msg);
                        }
                        return Err(PyException::new_err(error_msg));
                    }
                };

            let response = match rt.block_on(async {
                client.get(api_definition).send().await
            }) {
                Ok(response) => response,
                Err(e) => {
                    let error_msg = format!("Error fetching API definition: {}", e);
                    if let Some(ref logger) = self.logger {
                        logger.error(py, &error_msg);
                    }
                    return Err(PyException::new_err(error_msg));
                }
            };

            if !response.status().is_success() {
                let error_msg = format!("Error fetching API definition: {}", response.status());
                if let Some(ref logger) = self.logger {
                    logger.error(py, &error_msg);
                }
                return Err(PyException::new_err(error_msg));
            }

            let text = match rt.block_on(async {
                response.text().await
            }) {
                Ok(text) => text,
                Err(e) => {
                    let error_msg = format!("Error reading response text: {}", e);
                    if let Some(ref logger) = self.logger {
                        logger.error(py, &error_msg);
                    }
                    return Err(PyException::new_err(error_msg));
                }
            };

            if api_definition.ends_with(".json") {
                match serde_json::from_str(&text) {
                    Ok(value) => Ok(value),
                    Err(e) => {
                        let error_msg = format!("Error parsing JSON: {}", e);
                        if let Some(ref logger) = self.logger {
                            logger.error(py, &error_msg);
                        }
                        Err(PyException::new_err(error_msg))
                    }
                }
            } else {
                match serde_yaml::from_str(&text) {
                    Ok(value) => Ok(value),
                    Err(e) => {
                        let error_msg = format!("Error parsing YAML: {}", e);
                        if let Some(ref logger) = self.logger {
                            logger.error(py, &error_msg);
                        }
                        Err(PyException::new_err(error_msg))
                    }
                }
            }
        } else {
            if let Some(ref logger) = self.logger {
                let debug_msg = format!("Loading API definition from file: {}", api_definition);
                logger.debug(py, &debug_msg);
            }

            let file_content = match fs::read_to_string(api_definition) {
                Ok(content) => content,
                Err(e) => {
                    let error_msg = format!("Error reading file: {}", e);
                    if let Some(ref logger) = self.logger {
                        logger.error(py, &error_msg);
                    }
                    return Err(PyException::new_err(error_msg));
                }
            };

            // Determine format by file extension first, then try parsing
            if api_definition.ends_with(".json") {
                match serde_json::from_str(&file_content) {
                    Ok(value) => Ok(value),
                    Err(e) => {
                        let error_msg = format!("Error parsing JSON file: {}", e);
                        if let Some(ref logger) = self.logger {
                            logger.error(py, &error_msg);
                        }
                        Err(PyException::new_err(error_msg))
                    }
                }
            } else if api_definition.ends_with(".yaml") || api_definition.ends_with(".yml") {
                match serde_yaml::from_str(&file_content) {
                    Ok(value) => Ok(value),
                    Err(e) => {
                        let error_msg = format!("Error parsing YAML file: {}", e);
                        if let Some(ref logger) = self.logger {
                            logger.error(py, &error_msg);
                        }
                        Err(PyException::new_err(error_msg))
                    }
                }
            } else {
                // No clear extension, try both formats but be strict about errors
                let yaml_result = serde_yaml::from_str::<Value>(&file_content);
                let json_result = serde_json::from_str::<Value>(&file_content);
                
                match (yaml_result, json_result) {
                    (Ok(yaml_value), Ok(json_value)) => {
                        // Both parsed successfully, prefer JSON if they're different
                        // This shouldn't happen with valid content, but just in case
                        Ok(json_value)
                    }
                    (Ok(yaml_value), Err(_)) => {
                        // Only YAML parsed successfully
                        Ok(yaml_value)
                    }
                    (Err(_), Ok(json_value)) => {
                        // Only JSON parsed successfully
                        Ok(json_value)
                    }
                    (Err(yaml_err), Err(json_err)) => {
                        // Neither parsed successfully
                        let error_msg = format!("Error parsing file as JSON or YAML: YAML error: {}, JSON error: {}", yaml_err, json_err);
                        if let Some(ref logger) = self.logger {
                            logger.error(py, &error_msg);
                        }
                        Err(PyException::new_err(error_msg))
                    }
                }
            }
        }
    }

    fn split_definition_parallel(&self, py: Python, api_definition: &Value) -> PyResult<Vec<APIDef>> {
        let start_time = Instant::now();
        if let Some(ref logger) = self.logger {
            logger.info(py, "Splitting API definition into components...");
        }

        let paths = match api_definition.get("paths").and_then(|p| p.as_object()) {
            Some(paths) => paths,
            None => {
                if let Some(ref logger) = self.logger {
                    logger.info(py, "No paths found in API definition");
                }
                return Ok(Vec::new());
            }
        };

        // Group paths by normalized path to reduce copying
        let mut path_groups: HashMap<String, PathGroup> = HashMap::new();

        for (path, path_data) in paths.iter() {
            let normalized_path = normalize_path(path);
            path_groups
                .entry(normalized_path.clone())
                .or_insert_with(|| PathGroup::new(normalized_path))
                .add_path(path.clone(), path_data.clone());
        }

        // Process groups in parallel
        let results: Result<Vec<_>, PyErr> = path_groups
            .into_par_iter()
            .map(|(_, path_group)| {
                self.process_path_group(api_definition, path_group)
            })
            .collect();

        let api_definition_list: Vec<APIDef> = results?.into_iter().flatten().collect();

        if let Some(ref logger) = self.logger {
            logger.info(py, "Successfully split API definition.");
            let elapsed = start_time.elapsed();
            let time_msg = format!("Time taken to split API definition: {:.2} seconds", elapsed.as_secs_f64());
            logger.info(py, &time_msg);
        }

        Ok(api_definition_list)
    }

    fn process_path_group(&self, api_definition: &Value, path_group: PathGroup) -> PyResult<Vec<APIDef>> {
        let normalized_path = &path_group.normalized_path;
        let mut all_definitions = Vec::new();

        // Merge all paths in this group into a single path definition
        let merged_path_data = self.merge_path_data(&path_group)?;

        // Create the merged path definition with minimal copying
        let path_yaml = self.create_path_yaml(api_definition, normalized_path, &merged_path_data)?;

        all_definitions.push(APIDef::Path(APIPath {
            path: normalized_path.clone(),
            yaml: path_yaml,
        }));

        // Process each verb in the merged path data
        if let Some(merged_obj) = merged_path_data.as_object() {
            for (verb, verb_data) in merged_obj {
                let verb_yaml = self.create_verb_yaml(api_definition, normalized_path, verb, verb_data)?;

                all_definitions.push(APIDef::Verb(APIVerb {
                    verb: verb.to_uppercase(),
                    path: normalized_path.clone(),
                    root_path: get_root_path(normalized_path),
                    yaml: verb_yaml,
                }));
            }
        }

        Ok(all_definitions)
    }

    fn create_path_yaml(&self, api_definition: &Value, path: &str, path_data: &Value) -> PyResult<String> {
        let mut yaml_value = Value::Object(serde_json::Map::new());

        // Copy non-paths data from original
        if let Some(obj) = api_definition.as_object() {
            for (key, value) in obj {
                if key != "paths" {
                    if let Some(yaml_obj) = yaml_value.as_object_mut() {
                        yaml_obj.insert(key.clone(), value.clone());
                    }
                }
            }
        }

        // Add single path
        if let Some(yaml_obj) = yaml_value.as_object_mut() {
            let mut paths_obj = serde_json::Map::new();
            paths_obj.insert(path.to_string(), path_data.clone());
            yaml_obj.insert("paths".to_string(), Value::Object(paths_obj));
        }

        serde_yaml::to_string(&yaml_value).map_err(|e| {
            PyException::new_err(format!("Error converting to YAML: {}", e))
        })
    }

    fn create_verb_yaml(&self, api_definition: &Value, path: &str, verb: &str, verb_data: &Value) -> PyResult<String> {
        let mut yaml_value = Value::Object(serde_json::Map::new());

        // Copy non-paths data from original
        if let Some(obj) = api_definition.as_object() {
            for (key, value) in obj {
                if key != "paths" {
                    if let Some(yaml_obj) = yaml_value.as_object_mut() {
                        yaml_obj.insert(key.clone(), value.clone());
                    }
                }
            }
        }

        // Add single verb under single path
        if let Some(yaml_obj) = yaml_value.as_object_mut() {
            let mut verb_obj = serde_json::Map::new();
            verb_obj.insert(verb.to_string(), verb_data.clone());

            let mut paths_obj = serde_json::Map::new();
            paths_obj.insert(path.to_string(), Value::Object(verb_obj));

            yaml_obj.insert("paths".to_string(), Value::Object(paths_obj));
        }

        serde_yaml::to_string(&yaml_value).map_err(|e| {
            PyException::new_err(format!("Error converting to YAML: {}", e))
        })
    }

    // Helper method to merge multiple path data objects
    fn merge_path_data(&self, path_group: &PathGroup) -> PyResult<Value> {
        if path_group.len() == 1 {
            return Ok(path_group.path_entries[0].1.clone());
        }

        let mut merged_data = serde_json::Map::new();

        for (_, path_data) in &path_group.path_entries {
            if let Some(path_obj) = path_data.as_object() {
                for (verb, verb_data) in path_obj {
                    // If this verb doesn't exist in merged_data, add it
                    if !merged_data.contains_key(verb) {
                        merged_data.insert(verb.clone(), verb_data.clone());
                    }
                }
            }
        }

        Ok(Value::Object(merged_data))
    }

    // Simplified merge function since paths are properly grouped in split phase
    fn merge_definitions_parallel(&self, py: Python, api_definition_list: Vec<APIDef>) -> PyResult<Vec<APIDef>> {
        let start_time = Instant::now();

        // Separate paths and verbs
        let (paths, verbs): (Vec<_>, Vec<_>) = api_definition_list
            .into_iter()
            .partition(|item| matches!(item, APIDef::Path(_)));

        // Group paths by base path for final merging
        let mut path_groups: HashMap<String, Vec<APIDef>> = HashMap::new();
        for path in paths {
            if let APIDef::Path(ref path_data) = path {
                let base_path = get_root_path(&path_data.path);
                path_groups.entry(base_path).or_default().push(path);
            }
        }

        // Merge paths in parallel by group
        let merged_paths: Result<Vec<_>, PyErr> = path_groups
            .into_par_iter()
            .map(|(base_path, paths_to_merge)| {
                if paths_to_merge.len() == 1 {
                    // No merging needed, just update path
                    let mut path = paths_to_merge.into_iter().next().unwrap();
                    if let APIDef::Path(ref mut path_data) = path {
                        path_data.path = base_path;
                    }
                    Ok(path)
                } else {
                    // Merge multiple paths
                    self.merge_path_group(base_path, paths_to_merge)
                }
            })
            .collect();

        let mut final_definitions = merged_paths?;
        final_definitions.extend(verbs);

        if let Some(ref logger) = self.logger {
            let count_msg = format!("Merged {} API definitions", final_definitions.len());
            logger.info(py, &count_msg);

            let elapsed = start_time.elapsed();
            let time_msg = format!("Time taken to merge API definitions: {:.2} seconds", elapsed.as_secs_f64());
            logger.info(py, &time_msg);
        }

        Ok(final_definitions)
    }

    // Helper method to merge a group of paths with the same base path
    fn merge_path_group(&self, base_path: String, paths_to_merge: Vec<APIDef>) -> PyResult<APIDef> {
        let mut merged_yaml: Option<Value> = None;

        for path in paths_to_merge {
            if let APIDef::Path(path_data) = path {
                let path_yaml: Value = serde_yaml::from_str(&path_data.yaml).map_err(|e| {
                    PyException::new_err(format!("Error parsing YAML: {}", e))
                })?;

                match merged_yaml {
                    None => merged_yaml = Some(path_yaml),
                    Some(ref mut merged) => {
                        // Merge paths efficiently
                        if let (Some(path_paths), Some(merged_paths)) = (
                            path_yaml.get("paths").and_then(|p| p.as_object()),
                            merged.get_mut("paths").and_then(|p| p.as_object_mut())
                        ) {
                            for (path_key, path_data) in path_paths {
                                merged_paths.entry(path_key.clone()).or_insert_with(|| path_data.clone());
                            }
                        }
                    }
                }
            }
        }

        let final_yaml = merged_yaml.unwrap_or_else(|| Value::Object(serde_json::Map::new()));
        let merged_yaml_str = serde_yaml::to_string(&final_yaml).map_err(|e| {
            PyException::new_err(format!("Error converting to YAML: {}", e))
        })?;

        Ok(APIDef::Path(APIPath {
            path: base_path,
            yaml: merged_yaml_str,
        }))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{Arc, Mutex};
    use serde_json::json;
    use tempfile::NamedTempFile;
    use std::io::Write;
    use std::time::Duration;

    // Mock logger for testing
    #[pyclass]
    struct MockLogger {
        logs: Arc<Mutex<Vec<(String, String)>>>,
    }

    #[pymethods]
    impl MockLogger {
        #[new]
        fn new() -> Self {
            Self {
                logs: Arc::new(Mutex::new(Vec::new())),
            }
        }

        fn info(&self, message: &str) {
            self.logs.lock().unwrap().push(("info".to_string(), message.to_string()));
        }

        fn debug(&self, message: &str) {
            self.logs.lock().unwrap().push(("debug".to_string(), message.to_string()));
        }

        fn error(&self, message: &str) {
            self.logs.lock().unwrap().push(("error".to_string(), message.to_string()));
        }
    }

    fn setup_test_env() {
        pyo3::prepare_freethreaded_python();
    }

    fn create_sample_api_definition() -> Value {
        json!({
            "openapi": "3.0.0",
            "info": {
                "title": "Test API",
                "version": "1.0.0"
            },
            "paths": {
                "/api/v1/users": {
                    "get": {
                        "summary": "Get users"
                    },
                    "post": {
                        "summary": "Create user"
                    }
                },
                "/api/v1/posts": {
                    "get": {
                        "summary": "Get posts"
                    }
                }
            }
        })
    }

    #[test]
    fn test_processor_new_without_logger() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);
            assert!(processor.logger.is_none());
        });
    }

    #[test]
    fn test_processor_new_with_logger() {
        setup_test_env();
        Python::with_gil(|py| {
            let mock_logger = Py::new(py, MockLogger::new()).unwrap();
            let processor = APIDefinitionProcessor::new(Some(mock_logger.into()));
            assert!(processor.logger.is_some());
        });
    }

    #[test]
    fn test_load_definition_from_json_string() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let mut temp_file = NamedTempFile::with_suffix(".json").unwrap();
            let json_content = r#"{"openapi": "3.0.0", "info": {"title": "Test"}}"#;
            temp_file.write_all(json_content.as_bytes()).unwrap();

            let result = processor.load_definition(py, temp_file.path().to_str().unwrap());
            assert!(result.is_ok());

            let value = result.unwrap();
            assert_eq!(value["openapi"], "3.0.0");
            assert_eq!(value["info"]["title"], "Test");
        });
    }

    #[test]
    fn test_load_definition_from_yaml_string() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let mut temp_file = NamedTempFile::with_suffix(".yaml").unwrap();
            let yaml_content = r#"
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
"#;
            temp_file.write_all(yaml_content.as_bytes()).unwrap();

            let result = processor.load_definition(py, temp_file.path().to_str().unwrap());
            assert!(result.is_ok());

            let value = result.unwrap();
            assert_eq!(value["openapi"], "3.0.0");
            assert_eq!(value["info"]["title"], "Test API");
        });
    }

    #[test]
    fn test_load_definition_file_not_found() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);
            let result = processor.load_definition(py, "/nonexistent/file.json");
            assert!(result.is_err());
        });
    }

    #[test]
    fn test_load_definition_invalid_json() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let mut temp_file = NamedTempFile::with_suffix(".json").unwrap();
            temp_file.write_all(b"{invalid json}").unwrap();

            let result = processor.load_definition(py, temp_file.path().to_str().unwrap());
            assert!(result.is_err());
            let error = result.unwrap_err();
            let error_msg = error.to_string();
            assert!(error_msg.contains("Error parsing JSON file"));
        });
    }

    #[test]
    fn test_split_definition_no_paths() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);
            let api_def = json!({
                "openapi": "3.0.0",
                "info": {"title": "Test"}
            });
            let result = processor.split_definition_parallel(py, &api_def);
            assert!(result.is_ok());
            assert!(result.unwrap().is_empty());
        });
    }

    #[test]
    fn test_split_definition_with_paths() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);
            let api_def = create_sample_api_definition();
            let result = processor.split_definition_parallel(py, &api_def);
            assert!(result.is_ok());
            let definitions = result.unwrap();
            assert!(!definitions.is_empty());
            let paths: Vec<_> = definitions.iter().filter(|d| matches!(d, APIDef::Path(_))).collect();
            let verbs: Vec<_> = definitions.iter().filter(|d| matches!(d, APIDef::Verb(_))).collect();
            assert!(!paths.is_empty());
            assert!(!verbs.is_empty());
        });
    }

    #[test]
    fn test_process_path_group_single_path() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);
            let api_def = create_sample_api_definition();

            let mut path_group = PathGroup::new("/users".to_string());
            path_group.add_path("/api/v1/users".to_string(), json!({
                "get": {"summary": "Get users"},
                "post": {"summary": "Create user"}
            }));

            let result = processor.process_path_group(&api_def, path_group);
            assert!(result.is_ok());

            let definitions = result.unwrap();
            assert_eq!(definitions.len(), 3); // 1 path + 2 verbs
        });
    }

    #[test]
    fn test_create_path_yaml() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);
            let api_def = create_sample_api_definition();

            let path_data = json!({"get": {"summary": "Test"}});
            let result = processor.create_path_yaml(&api_def, "/test", &path_data);

            assert!(result.is_ok());
            let yaml_str = result.unwrap();
            assert!(yaml_str.contains("openapi"));
            assert!(yaml_str.contains("/test"));
        });
    }

    #[test]
    fn test_create_verb_yaml() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);
            let api_def = create_sample_api_definition();

            let verb_data = json!({"summary": "Test verb"});
            let result = processor.create_verb_yaml(&api_def, "/test", "get", &verb_data);

            assert!(result.is_ok());
            let yaml_str = result.unwrap();
            assert!(yaml_str.contains("openapi"));
            assert!(yaml_str.contains("/test"));
            assert!(yaml_str.contains("get"));
        });
    }

    #[test]
    fn test_merge_path_data_single_entry() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let mut path_group = PathGroup::new("/test".to_string());
            let path_data = json!({"get": {"summary": "Test"}});
            path_group.add_path("/test".to_string(), path_data.clone());

            let result = processor.merge_path_data(&path_group);
            assert!(result.is_ok());
            assert_eq!(result.unwrap(), path_data);
        });
    }

    #[test]
    fn test_merge_path_data_multiple_entries() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let mut path_group = PathGroup::new("/test".to_string());
            path_group.add_path("/v1/test".to_string(), json!({"get": {"summary": "Get"}}));
            path_group.add_path("/v2/test".to_string(), json!({"post": {"summary": "Post"}}));

            let result = processor.merge_path_data(&path_group);
            assert!(result.is_ok());

            let merged = result.unwrap();
            assert!(merged.get("get").is_some());
            assert!(merged.get("post").is_some());
        });
    }

    #[test]
    fn test_merge_definitions_parallel_empty() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);
            let result = processor.merge_definitions_parallel(py, Vec::new());
            assert!(result.is_ok());
            assert!(result.unwrap().is_empty());
        });
    }

    #[test]
    fn test_merge_definitions_parallel_with_data() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let path_def = APIDef::Path(APIPath {
                path: "/users".to_string(),
                yaml: "test: yaml".to_string(),
            });
            let verb_def = APIDef::Verb(APIVerb {
                verb: "GET".to_string(),
                path: "/users".to_string(),
                root_path: "/users".to_string(),
                yaml: "test: yaml".to_string(),
            });

            let definitions = vec![path_def, verb_def];
            let result = processor.merge_definitions_parallel(py, definitions);

            assert!(result.is_ok());
            let merged = result.unwrap();
            assert_eq!(merged.len(), 2);
        });
    }

    #[test]
    fn test_merge_path_group_single_path() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let path_def = APIDef::Path(APIPath {
                path: "/test".to_string(),
                yaml: serde_yaml::to_string(&json!({
                    "openapi": "3.0.0",
                    "paths": {"/test": {"get": {"summary": "Test"}}}
                })).unwrap(),
            });

            let result = processor.merge_path_group("/test".to_string(), vec![path_def]);
            assert!(result.is_ok());

            if let APIDef::Path(merged_path) = result.unwrap() {
                assert_eq!(merged_path.path, "/test");
                assert!(merged_path.yaml.contains("openapi"));
            } else {
                panic!("Expected Path variant");
            }
        });
    }

    #[test]
    fn test_process_api_definition_integration() {
        setup_test_env();
        Python::with_gil(|py| {
            let mock_logger = Py::new(py, MockLogger::new()).unwrap();
            let processor = APIDefinitionProcessor::new(Some(mock_logger.into()));

            let mut temp_file = NamedTempFile::new().unwrap();
            let api_content = serde_json::to_string_pretty(&create_sample_api_definition()).unwrap();
            temp_file.write_all(api_content.as_bytes()).unwrap();

            let result = processor.process_api_definition(py, temp_file.path().to_str().unwrap());
            assert!(result.is_ok());

            let py_list = result.unwrap();
            let list_len = py_list.bind(py).len();
            assert!(list_len > 0);
        });
    }

    #[test]
    fn test_process_api_definition_with_logging() {
        setup_test_env();
        Python::with_gil(|py| {
            let mock_logger = Py::new(py, MockLogger::new()).unwrap();
            let logs = mock_logger.borrow(py).logs.clone();
            let processor = APIDefinitionProcessor::new(Some(mock_logger.into()));

            let mut temp_file = NamedTempFile::new().unwrap();
            let api_content = serde_json::to_string_pretty(&create_sample_api_definition()).unwrap();
            temp_file.write_all(api_content.as_bytes()).unwrap();

            let result = processor.process_api_definition(py, temp_file.path().to_str().unwrap());
            assert!(result.is_ok());

            let logged_messages = logs.lock().unwrap();
            assert!(!logged_messages.is_empty());

            let info_messages: Vec<_> = logged_messages.iter()
                .filter(|(level, _)| level == "info")
                .collect();
            assert!(!info_messages.is_empty());
        });
    }

    #[test]
    fn test_error_handling_invalid_yaml_in_merge() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let invalid_path = APIDef::Path(APIPath {
                path: "/test".to_string(),
                yaml: "invalid: yaml: content: [".to_string(), // Invalid YAML
            });

            let result = processor.merge_path_group("/test".to_string(), vec![invalid_path]);
            assert!(result.is_err());
        });
    }

    #[test]
    fn test_parallel_processing_consistency() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let mut paths = serde_json::Map::new();
            for i in 0..100 {
                paths.insert(
                    format!("/api/v1/resource{}", i),
                    json!({
                        "get": {"summary": format!("Get resource {}", i)},
                        "post": {"summary": format!("Create resource {}", i)}
                    })
                );
            }

            let large_api_def = json!({
                "openapi": "3.0.0",
                "info": {"title": "Large API", "version": "1.0.0"},
                "paths": paths
            });

            let result = processor.split_definition_parallel(py, &large_api_def);
            assert!(result.is_ok());

            let definitions = result.unwrap();
            assert_eq!(definitions.len(), 300); // 100 paths + 200 verbs
        });
    }

    #[test]
    fn test_yaml_creation_preserves_structure() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let api_def = json!({
                "openapi": "3.0.0",
                "info": {
                    "title": "Test API",
                    "version": "1.0.0",
                    "description": "A test API"
                },
                "servers": [{"url": "https://api.example.com"}],
                "components": {
                    "schemas": {
                        "User": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "name": {"type": "string"}
                            }
                        }
                    }
                }
            });

            let path_data = json!({"get": {"summary": "Get users"}});
            let result = processor.create_path_yaml(&api_def, "/users", &path_data);

            assert!(result.is_ok());
            let yaml_str = result.unwrap();

            let parsed: Value = serde_yaml::from_str(&yaml_str).unwrap();
            assert_eq!(parsed["openapi"], "3.0.0");
            assert_eq!(parsed["info"]["title"], "Test API");
            assert!(parsed["servers"].is_array());
            assert!(parsed["components"]["schemas"]["User"].is_object());
            assert!(parsed["paths"]["/users"]["get"].is_object());
        });
    }

    #[test]
    fn test_verb_yaml_structure() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let api_def = json!({
                "openapi": "3.0.0",
                "info": {"title": "Test API"}
            });

            let verb_data = json!({
                "summary": "Create user",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/User"}
                        }
                    }
                },
                "responses": {
                    "201": {"description": "User created"}
                }
            });

            let result = processor.create_verb_yaml(&api_def, "/users", "post", &verb_data);
            assert!(result.is_ok());

            let yaml_str = result.unwrap();
            let parsed: Value = serde_yaml::from_str(&yaml_str).unwrap();

            assert_eq!(parsed["paths"]["/users"]["post"]["summary"], "Create user");
            assert!(parsed["paths"]["/users"]["post"]["requestBody"].is_object());
            assert!(parsed["paths"]["/users"]["post"]["responses"]["201"].is_object());
        });
    }

    #[test]
    fn test_empty_api_definition() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let empty_api_def = json!({
                "openapi": "3.0.0",
                "info": {"title": "Empty API"},
                "paths": {}
            });

            let result = processor.split_definition_parallel(py, &empty_api_def);
            assert!(result.is_ok());
            assert!(result.unwrap().is_empty());
        });
    }

    #[test]
    fn test_path_normalization_in_processing() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let api_def = json!({
                "openapi": "3.0.0",
                "info": {"title": "Test API"},
                "paths": {
                    "/api/v1/users": {"get": {"summary": "V1 Get users"}},
                    "/api/v2/users": {"post": {"summary": "V2 Create user"}},
                    "/v3/users": {"delete": {"summary": "V3 Delete user"}}
                }
            });

            let result = processor.split_definition_parallel(py, &api_def);
            assert!(result.is_ok());

            let definitions = result.unwrap();

            // All should normalize to /users
            let paths: Vec<_> = definitions.iter()
                .filter_map(|d| match d {
                    APIDef::Path(path) => Some(path.path.as_str()),
                    APIDef::Verb(verb) => Some(verb.path.as_str()),
                })
                .collect();

            // All paths should be normalized to /users
            for path in paths {
                assert_eq!(path, "/users");
            }
        });
    }

    #[test]
    fn test_concurrent_access_safety() {
        use std::thread;
        use std::sync::Arc;
        setup_test_env();
        let processor = Arc::new(APIDefinitionProcessor::new(None));
        let api_def = Arc::new(create_sample_api_definition());

        let handles: Vec<_> = (0..10).map(|_| {
            let processor_clone = processor.clone();
            let api_def_clone = api_def.clone();

            thread::spawn(move || {
                Python::with_gil(|py| {
                    let result = processor_clone.split_definition_parallel(py, &api_def_clone);
                    assert!(result.is_ok());
                    !result.unwrap().is_empty()
                })
            })
        }).collect();

        for handle in handles {
            assert!(handle.join().unwrap());
        }
    }

    #[test]
    fn test_memory_efficiency_large_dataset() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            // Create a very large API definition
            let mut paths = serde_json::Map::new();
            for i in 0..1000 {
                let mut verbs = serde_json::Map::new();
                for verb in &["get", "post", "put", "delete", "patch"] {
                    verbs.insert(verb.to_string(), json!({
                        "summary": format!("{} resource {} operation", verb, i),
                        "parameters": [
                            {"name": "id", "in": "path", "required": true, "schema": {"type": "integer"}}
                        ],
                        "responses": {
                            "200": {"description": "Success"}
                        }
                    }));
                }
                paths.insert(format!("/api/v1/resource{}", i), Value::Object(verbs));
            }

            let large_api_def = json!({
                "openapi": "3.0.0",
                "info": {"title": "Very Large API", "version": "1.0.0"},
                "paths": paths
            });

            let start_time = std::time::Instant::now();
            let result = processor.split_definition_parallel(py, &large_api_def);
            let duration = start_time.elapsed();

            assert!(result.is_ok());
            let definitions = result.unwrap();
            assert_eq!(definitions.len(), 6000); // 1000 paths + 5000 verbs

            // Should complete in reasonable time (less than 5 seconds)
            assert!(duration.as_secs() < 5);
        });
    }

    #[test]
    fn test_load_definition_from_url() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            // Create a mock HTTP server for testing
            let mut server = mockito::Server::new();
            let mock = server.mock("GET", "/api.json")
                .with_status(200)
                .with_header("content-type", "application/json")
                .with_body(r#"{"openapi": "3.0.0", "info": {"title": "Test API"}}"#)
                .create();

            let result = processor.load_definition(py, &format!("{}/api.json", server.url()));
            assert!(result.is_ok());
            mock.assert();
        });
    }

    #[test]
    fn test_load_definition_url_timeout() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            // Test with a URL that doesn't exist to trigger timeout/error
            let result = processor.load_definition(py, "http://invalid-url-12345.nonexistent/slow.json");
            assert!(result.is_err());
            let error = result.unwrap_err();
            let error_msg = error.to_string();
            assert!(error_msg.contains("Error fetching API definition"));
        });
    }

    #[test]
    fn test_load_definition_invalid_url() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let result = processor.load_definition(py, "http://invalid-url-that-does-not-exist.com/api.json");
            assert!(result.is_err());
        });
    }

    #[test]
    fn test_load_definition_unsupported_format() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let mut temp_file = NamedTempFile::new().unwrap();
            temp_file.write_all(b"unsupported format").unwrap();

            let result = processor.load_definition(py, temp_file.path().to_str().unwrap());
            
            assert!(result.is_err());
            let error = result.unwrap_err();
            let error_msg = error.to_string();
            assert!(error_msg.contains("Error parsing file as JSON or YAML"));
            assert!(error_msg.contains("YAML error"));
            assert!(error_msg.contains("JSON error"));
        });
    }

    #[test]
    fn test_split_definition_with_parameters() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let api_def = json!({
                "openapi": "3.0.0",
                "info": {"title": "Test API"},
                "paths": {
                    "/users/{id}": {
                        "get": {
                            "parameters": [
                                {
                                    "name": "id",
                                    "in": "path",
                                    "required": true,
                                    "schema": {"type": "integer"}
                                }
                            ],
                            "responses": {
                                "200": {"description": "Success"}
                            }
                        }
                    }
                }
            });

            let result = processor.split_definition_parallel(py, &api_def);
            assert!(result.is_ok());

            let definitions = result.unwrap();
            assert!(!definitions.is_empty());

            // Verify parameter handling
            let verb_defs: Vec<_> = definitions.iter()
                .filter_map(|d| match d {
                    APIDef::Verb(verb) => Some(verb),
                    _ => None,
                })
                .collect();

            assert!(!verb_defs.is_empty());
            let yaml_str = &verb_defs[0].yaml;
            assert!(yaml_str.contains("parameters"));
            assert!(yaml_str.contains("id"));
        });
    }

    #[test]
    fn test_split_definition_with_security() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let api_def = json!({
                "openapi": "3.0.0",
                "info": {"title": "Test API"},
                "components": {
                    "securitySchemes": {
                        "bearerAuth": {
                            "type": "http",
                            "scheme": "bearer"
                        }
                    }
                },
                "paths": {
                    "/secure": {
                        "get": {
                            "security": [{"bearerAuth": []}],
                            "responses": {"200": {"description": "Success"}}
                        }
                    }
                }
            });

            let result = processor.split_definition_parallel(py, &api_def);
            assert!(result.is_ok());

            let definitions = result.unwrap();
            assert!(!definitions.is_empty());

            // Verify security scheme is preserved
            let path_defs: Vec<_> = definitions.iter()
                .filter_map(|d| match d {
                    APIDef::Path(path) => Some(path),
                    _ => None,
                })
                .collect();

            assert!(!path_defs.is_empty());
            let yaml_str = &path_defs[0].yaml;
            assert!(yaml_str.contains("securitySchemes"));
            assert!(yaml_str.contains("bearerAuth"));
        });
    }

    #[test]
    fn test_split_definition_with_references() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let api_def = json!({
                "openapi": "3.0.0",
                "info": {"title": "Test API"},
                "components": {
                    "schemas": {
                        "User": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "name": {"type": "string"}
                            }
                        }
                    }
                },
                "paths": {
                    "/users": {
                        "get": {
                            "responses": {
                                "200": {
                                    "description": "Success",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/User"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            });

            let result = processor.split_definition_parallel(py, &api_def);
            assert!(result.is_ok());

            let definitions = result.unwrap();
            assert!(!definitions.is_empty());

            // Verify references are preserved
            let verb_defs: Vec<_> = definitions.iter()
                .filter_map(|d| match d {
                    APIDef::Verb(verb) => Some(verb),
                    _ => None,
                })
                .collect();

            assert!(!verb_defs.is_empty());
            let yaml_str = &verb_defs[0].yaml;
            assert!(yaml_str.contains("$ref"));
            assert!(yaml_str.contains("#/components/schemas/User"));
        });
    }

    #[test]
    fn test_memory_usage_with_large_responses() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            // Create a large response schema
            let mut large_schema = serde_json::Map::new();
            for i in 0..100 {
                large_schema.insert(
                    format!("field{}", i),
                    json!({
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                            "description": {"type": "string"}
                        }
                    })
                );
            }

            let api_def = json!({
                "openapi": "3.0.0",
                "info": {"title": "Test API"},
                "paths": {
                    "/large": {
                        "get": {
                            "responses": {
                                "200": {
                                    "description": "Success",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": large_schema
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            });

            let start_time = std::time::Instant::now();
            let result = processor.split_definition_parallel(py, &api_def);
            let duration = start_time.elapsed();

            assert!(result.is_ok());
            let definitions = result.unwrap();
            assert!(!definitions.is_empty());

            // Should complete in reasonable time
            assert!(duration.as_secs() < 2);
        });
    }

    #[test]
    fn test_api_version_compatibility() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            // Test OpenAPI 2.0 (Swagger)
            let swagger_def = json!({
                "swagger": "2.0",
                "info": {"title": "Test API"},
                "paths": {
                    "/users": {
                        "get": {"responses": {"200": {"description": "Success"}}}
                    }
                }
            });

            let result = processor.split_definition_parallel(py, &swagger_def);
            assert!(result.is_ok());

            // Test OpenAPI 3.1
            let openapi_31_def = json!({
                "openapi": "3.1.0",
                "info": {"title": "Test API"},
                "paths": {
                    "/users": {
                        "get": {"responses": {"200": {"description": "Success"}}}
                    }
                }
            });

            let result = processor.split_definition_parallel(py, &openapi_31_def);
            assert!(result.is_ok());
        });
    }

    #[test]
    fn test_yaml_format_validation() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let mut temp_file = NamedTempFile::with_suffix(".yaml").unwrap();
            let yaml_content = r#"
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /test:
    get:
      summary: Test endpoint
      responses:
        200:
          description: Success
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: integer
                  name:
                    type: string
"#;
            temp_file.write_all(yaml_content.as_bytes()).unwrap();

            let result = processor.load_definition(py, temp_file.path().to_str().unwrap());
            assert!(result.is_ok());

            let value = result.unwrap();
            assert_eq!(value["openapi"], "3.0.0");
            assert_eq!(value["info"]["title"], "Test API");
            assert!(value["paths"]["/test"]["get"]["responses"]["200"].is_object());
        });
    }

    #[test]
    fn test_error_handling_malformed_yaml() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let mut temp_file = NamedTempFile::with_suffix(".yaml").unwrap();
            let malformed_yaml = r#"
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /test:
    get:
      summary: Test endpoint
      responses:
        200:
          description: Success
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: integer
                  name:
                    type: string
                  # Invalid YAML: unbalanced brackets
                  malformed: [unclosed
"#;
            temp_file.write_all(malformed_yaml.as_bytes()).unwrap();

            let result = processor.load_definition(py, temp_file.path().to_str().unwrap());
            assert!(result.is_err());
            let error = result.unwrap_err();
            let error_msg = error.to_string();
            assert!(error_msg.contains("Error parsing YAML file"));
        });
    }

    #[test]
    fn test_error_handling_missing_required_fields() {
        setup_test_env();
        Python::with_gil(|py| {
            let processor = APIDefinitionProcessor::new(None);

            let api_def = json!({
                "info": {"title": "Test API"}, // Missing openapi version
                "paths": {
                    "/test": {
                        "get": {
                            "responses": {"200": {"description": "Success"}}
                        }
                    }
                }
            });

            let result = processor.split_definition_parallel(py, &api_def);
            assert!(result.is_ok()); // Should still process but log warning
        });
    }
}