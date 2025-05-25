use pyo3::exceptions::PyException;
use serde_json::Value;

// Custom exception for API definition errors
pyo3::create_exception!(api_definition, APIDefinitionError, PyException);

// Internal Rust structures
#[derive(Debug, Clone, PartialEq)]
pub struct APIPath {
    pub path: String,
    pub yaml: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct APIVerb {
    pub verb: String,
    pub path: String,
    pub root_path: String,
    pub yaml: String,
}

#[derive(Debug, Clone, PartialEq)]
pub enum APIDef {
    Path(APIPath),
    Verb(APIVerb),
}