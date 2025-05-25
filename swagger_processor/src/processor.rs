use pyo3::exceptions::PyException;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use rayon::prelude::*;
use reqwest;
use serde_json::{self, Value, Map};
use serde_yaml;
use std::collections::HashMap;
use std::fs;
use std::time::Instant;
use tokio;
use once_cell::sync::Lazy;

use crate::logger::ThreadSafeLogger;
use crate::types::{APIDef, APIPath, APIVerb};
use crate::utils::{get_root_path, normalize_path};

// Pre-compiled static client for URL loading
static HTTP_CLIENT: Lazy<reqwest::Client> = Lazy::new(|| {
    reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .expect("Failed to create HTTP client")
});

#[pyclass]
pub struct APIDefinitionProcessor {
    logger: Option<ThreadSafeLogger>,
    runtime: tokio::runtime::Runtime,
}

#[pymethods]
impl APIDefinitionProcessor {
    #[new]
    fn new(logger: Option<Py<PyAny>>) -> PyResult<Self> {
        let runtime = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .map_err(|e| PyException::new_err(format!("Failed to create async runtime: {}", e)))?;

        Ok(APIDefinitionProcessor {
            logger: logger.map(ThreadSafeLogger::new),
            runtime,
        })
    }

    fn process_api_definition(
        &self,
        py: Python,
        api_definition_path: &str,
    ) -> PyResult<(String, Py<PyList>)> {
        if let Some(ref logger) = self.logger {
            logger.info(py, "Starting API processing");
        }

        let start_time = Instant::now();
        let raw_definition = self.load_definition(py, api_definition_path)?;
        let (base_yaml, split_definitions) = self.split_definition_optimized(py, &raw_definition)?;
        let merged_definitions = self.merge_definitions_optimized(py, split_definitions)?;

        let result_list = PyList::empty(py);

        for definition in merged_definitions {
            let py_dict = PyDict::new(py);
            match definition {
                APIDef::Path(path) => {
                    py_dict.set_item("type", "path")?;
                    py_dict.set_item("path", path.path)?;
                    py_dict.set_item("yaml", path.yaml)?;
                }
                APIDef::Verb(verb) => {
                    py_dict.set_item("type", "verb")?;
                    py_dict.set_item("verb", verb.verb)?;
                    py_dict.set_item("path", verb.path)?;
                    py_dict.set_item("root_path", verb.root_path)?;
                    py_dict.set_item("yaml", verb.yaml)?;
                }
            }
            result_list.append(py_dict)?;
        }

        if let Some(ref logger) = self.logger {
            logger.info(py, &format!(
                "Time taken to process API definition: {:.3}s",
                start_time.elapsed().as_secs_f64()
            ));
        }

        Ok((base_yaml, result_list.into()))
    }
}

impl APIDefinitionProcessor {
    #[inline]
    fn load_definition(&self, py: Python, api_definition: &str) -> PyResult<Value> {
        if api_definition.starts_with("http") {
            self.load_from_url(py, api_definition)
        } else {
            self.load_from_file(py, api_definition)
        }
    }

    fn load_from_url(&self, py: Python, url: &str) -> PyResult<Value> {
        let response = self.runtime.block_on(async {
            HTTP_CLIENT.get(url).send().await
        }).map_err(|e| PyException::new_err(format!("HTTP error: {}", e)))?;

        if !response.status().is_success() {
            return Err(PyException::new_err(format!("HTTP {}", response.status())));
        }

        let text = self.runtime.block_on(async { response.text().await })
            .map_err(|e| PyException::new_err(format!("Read error: {}", e)))?;

        self.parse_content_fast(&text, url.ends_with(".json"))
    }

    #[inline]
    fn load_from_file(&self, _py: Python, path: &str) -> PyResult<Value> {
        let content = fs::read_to_string(path)
            .map_err(|e| PyException::new_err(format!("File error: {}", e)))?;

        let is_json = path.ends_with(".json") ||
            (!path.ends_with(".yaml") && !path.ends_with(".yml") && content.trim_start().starts_with('{'));

        self.parse_content_fast(&content, is_json)
    }

    #[inline]
    fn parse_content_fast(&self, content: &str, is_json: bool) -> PyResult<Value> {
        if is_json {
            serde_json::from_str(content)
                .map_err(|e| PyException::new_err(format!("JSON error: {}", e)))
        } else {
            serde_yaml::from_str(content)
                .map_err(|e| PyException::new_err(format!("YAML error: {}", e)))
        }
    }

    fn split_definition_optimized(&self, py: Python, api_definition: &Value) -> PyResult<(String, Vec<APIDef>)> {
        let start_time = Instant::now();

        let Some(paths) = api_definition.get("paths").and_then(|p| p.as_object()) else {
            let empty_yaml = serde_yaml::to_string(&Value::Object(Map::new()))
                .map_err(|e| PyException::new_err(format!("YAML error: {}", e)))?;
            return Ok((empty_yaml, Vec::new()));
        };

        // Create base definition once
        let base_definition = self.create_base_definition(api_definition);
        let base_yaml = serde_yaml::to_string(&base_definition)
            .map_err(|e| PyException::new_err(format!("YAML error: {}", e)))?;

        // Pre-calculate capacity
        let estimated_capacity = paths.len() * 6; // ~6 items per path on average
        let path_entries: Vec<_> = paths.iter().collect();

        let results: Result<Vec<_>, PyErr> = path_entries
            .par_iter()
            .map(|(path, path_data)| {
                let normalized_path = normalize_path(path);
                self.process_single_path_optimized(path, &normalized_path, path_data)
            })
            .collect();

        let mut api_definition_list = Vec::with_capacity(estimated_capacity);
        for batch in results? {
            api_definition_list.extend(batch);
        }

        if let Some(ref logger) = self.logger {
            logger.debug(py, &format!(
                "Split {} paths in {:.3}s",
                paths.len(),
                start_time.elapsed().as_secs_f64()
            ));
        }

        Ok((base_yaml, api_definition_list))
    }

    #[inline]
    fn create_base_definition(&self, api_definition: &Value) -> Value {
        let mut base = api_definition.clone();
        if let Some(obj) = base.as_object_mut() {
            obj.remove("paths");
        }
        base
    }

    fn process_single_path_optimized(&self, original_path: &str, normalized_path: &str, path_data: &Value) -> PyResult<Vec<APIDef>> {
        let Some(path_obj) = path_data.as_object() else {
            return Ok(Vec::new());
        };

        let mut definitions = Vec::with_capacity(path_obj.len() + 1);

        // Create APIPath - single allocation
        let path_yaml = self.create_path_yaml_fast(original_path, path_data)?;
        definitions.push(APIDef::Path(APIPath {
            path: normalized_path.to_string(),
            yaml: path_yaml,
        }));

        // Pre-compute root path once
        let root_path = get_root_path(normalized_path);

        // Create APIVerbs
        for (verb, verb_data) in path_obj {
            let verb_yaml = self.create_verb_yaml_fast(original_path, verb, verb_data)?;
            definitions.push(APIDef::Verb(APIVerb {
                verb: verb.to_ascii_uppercase(),
                path: normalized_path.to_string(),
                root_path: root_path.clone(),
                yaml: verb_yaml,
            }));
        }

        Ok(definitions)
    }

    #[inline]
    fn create_path_yaml_fast(&self, path: &str, path_data: &Value) -> PyResult<String> {
        let mut yaml_map = Map::with_capacity(1);
        yaml_map.insert(path.to_string(), path_data.clone());

        serde_yaml::to_string(&Value::Object(yaml_map))
            .map_err(|e| PyException::new_err(format!("YAML error: {}", e)))
    }

    fn create_verb_yaml_fast(&self, path: &str, verb: &str, verb_data: &Value) -> PyResult<String> {
        // Use thread-local buffer for building YAML
        thread_local! {
            static YAML_BUFFER: std::cell::RefCell<String> = std::cell::RefCell::new(String::with_capacity(1024));
        }

        YAML_BUFFER.with(|buffer| {
            let mut buf = buffer.borrow_mut();
            buf.clear();

            // Manual YAML construction for simple structure - much faster than serde
            buf.push_str("paths:\n  \"");
            buf.push_str(path);
            buf.push_str("\":\n    ");
            buf.push_str(verb);
            buf.push_str(":\n");

            // Convert verb_data to YAML and indent
            let verb_yaml = serde_yaml::to_string(verb_data)
                .map_err(|e| PyException::new_err(format!("YAML error: {}", e)))?;

            for line in verb_yaml.lines() {
                if !line.trim().is_empty() {
                    buf.push_str("      ");
                    buf.push_str(line);
                    buf.push('\n');
                }
            }

            Ok(buf.clone())
        })
    }

    fn merge_definitions_optimized(&self, py: Python, api_definition_list: Vec<APIDef>) -> PyResult<Vec<APIDef>> {
        let start_time = Instant::now();

        let mut merged_definitions: HashMap<String, APIDef> = HashMap::with_capacity(api_definition_list.len());

        for item in api_definition_list {
            match item {
                APIDef::Path(mut path) => {
                    let base_path = get_root_path(&path.path);

                    match merged_definitions.get_mut(&base_path) {
                        Some(APIDef::Path(existing_path)) => {
                            // Fast YAML merge using string manipulation
                            self.merge_path_yaml_fast(&mut existing_path.yaml, &path.yaml)?;
                        }
                        None => {
                            path.path = base_path.clone();
                            merged_definitions.insert(base_path, APIDef::Path(path));
                        }
                        _ => unreachable!("Path key should only map to Path"),
                    }
                }
                APIDef::Verb(verb) => {
                    let key = format!("{}-{}", verb.path, verb.verb);
                    merged_definitions.insert(key, APIDef::Verb(verb));
                }
            }
        }

        let final_definitions: Vec<APIDef> = merged_definitions.into_values().collect();

        if let Some(ref logger) = self.logger {
            logger.debug(py, &format!(
                "Merged to {} definitions in {:.3}s",
                final_definitions.len(),
                start_time.elapsed().as_secs_f64()
            ));
        }

        Ok(final_definitions)
    }

    fn merge_path_yaml_fast(&self, existing_yaml: &mut String, new_yaml: &str) -> PyResult<()> {
        // Parse both YAML strings
        let existing_val: Value = serde_yaml::from_str(existing_yaml)
            .map_err(|e| PyException::new_err(format!("YAML parse error: {}", e)))?;
        let new_val: Value = serde_yaml::from_str(new_yaml)
            .map_err(|e| PyException::new_err(format!("YAML parse error: {}", e)))?;

        // Merge objects
        let mut merged = existing_val.as_object().unwrap().clone();
        if let Some(new_obj) = new_val.as_object() {
            for (key, value) in new_obj {
                merged.entry(key.clone()).or_insert_with(|| value.clone());
            }
        }

        // Convert back to YAML
        *existing_yaml = serde_yaml::to_string(&Value::Object(merged))
            .map_err(|e| PyException::new_err(format!("YAML conversion error: {}", e)))?;

        Ok(())
    }
}